"""Compute macro regime strategy walk-forward backtests and save to DB.

Usage:
    python -m ix.core.macro.wf_compute          # all indices
    python -m ix.core.macro.wf_compute ACWI     # single index
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ix.db.conn import Session
from ix.db.models.macro_regime_strategy import MacroRegimeStrategy as MacroRegimeStrategyDB
from ix.core.macro.wf_backtest import INDEX_MAP
from ix.common import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Serialization helpers (used by MacroRegimeStrategy.save() via extra kwargs
# and by the legacy save_to_db path)
# ---------------------------------------------------------------------------


def _sf(v) -> float | None:
    """Safe float for JSON."""
    if v is None:
        return None
    try:
        f = float(v)
        return None if (pd.isna(f) or np.isinf(f)) else round(f, 6)
    except (TypeError, ValueError):
        return None


def _dates(idx) -> list[str]:
    return [d.strftime("%Y-%m-%d") for d in idx]


def _vals(s) -> list[float | None]:
    return [_sf(v) for v in s.values]


def _subsample(dates: list, values: list, max_pts: int = 800) -> tuple[list, list]:
    """Thin time series to at most max_pts points, keeping first/last."""
    n = len(dates)
    if n <= max_pts:
        return dates, values
    step = max(1, n // max_pts)
    idx = list(range(0, n, step))
    if idx[-1] != n - 1:
        idx.append(n - 1)
    return [dates[i] for i in idx], [values[i] for i in idx]


def serialize_backtest(pipeline: dict) -> dict:
    wf_results = pipeline.get("wf_results", {})
    wf_histories = pipeline.get("wf_histories", {})

    # Benchmark from first available strategy
    bench = {}
    if wf_results:
        first = next(iter(wf_results.values()))
        bench = {
            "ann_return": _sf(first["bench_ann_ret"]),
            "sharpe": _sf(first["bench_sharpe"]),
            "max_dd": _sf(first["bench_mdd"]),
            "vol": _sf(first["bench_vol"]),
        }

    strategies = {}
    for name, r in wf_results.items():
        bt = r["bt_df"]
        dates_raw = _dates(bt.index)
        excess = r["excess"]

        # Yearly alpha
        yearly = excess.groupby(excess.index.year).sum()
        yearly_alpha = {str(int(yr)): _sf(v) for yr, v in yearly.items()}

        # Rolling 52w excess
        rolling_ex = excess.rolling(52).sum().dropna()
        re_dates, re_vals = _subsample(_dates(rolling_ex.index), _vals(rolling_ex))

        # Drawdown
        dd = bt["strategy_cum"] / bt["strategy_cum"].expanding().max() - 1

        # Subsample curves
        cum_d, cum_s = _subsample(dates_raw, _vals(bt["strategy_cum"]))
        _, cum_b = _subsample(dates_raw, _vals(bt["benchmark_cum"]))
        _, cum_i = _subsample(dates_raw, _vals(bt["idx_cum"]))
        ew_d, ew_v = _subsample(dates_raw, _vals(bt["eq_weight"]))
        dd_d, dd_v = _subsample(dates_raw, _vals(dd))

        strategies[name] = {
            "ann_return": _sf(r["strat_ann_ret"]),
            "sharpe": _sf(r["strat_sharpe"]),
            "max_dd": _sf(r["strat_mdd"]),
            "vol": _sf(r["strat_vol"]),
            "ir": _sf(r["ir"]),
            "te": _sf(r["te"]),
            "hit_rate": _sf(r["bt_hit"]),
            "avg_eq_wt": _sf(bt["eq_weight"].mean()),
            "alpha": _sf(r["strat_ann_ret"] - r["bench_ann_ret"]),
            "period_start": bt.index[0].strftime("%Y-%m"),
            "period_end": bt.index[-1].strftime("%Y-%m"),
            "cumulative": {"dates": cum_d, "strategy": cum_s, "benchmark": cum_b, "index": cum_i},
            "eq_weight": {"dates": ew_d, "values": ew_v},
            "drawdown": {"dates": dd_d, "values": dd_v},
            "rolling_excess": {"dates": re_dates, "values": re_vals},
            "yearly_alpha": yearly_alpha,
        }

    # Regime history
    regime_history = []
    if "Regime" in wf_histories:
        for h in wf_histories["Regime"]:
            regime_history.append({
                "date": h["date"].strftime("%Y-%m-%d") if hasattr(h["date"], "strftime") else str(h["date"]),
                "regime": h.get("regime", ""),
                "growth_pctile": _sf(h.get("growth_pctile")),
                "inflation_pctile": _sf(h.get("inflation_pctile")),
                "eq_weight": _sf(h.get("eq_weight")),
            })

    return {
        "parameters": {
            "optimized": pipeline.get("optimized", True),
            "n_indicators": pipeline.get("n_indicators", 0),
            "n_total": pipeline.get("n_total", 0),
        },
        "cat_counts": pipeline.get("cat_counts", {}),
        "benchmark": bench,
        "strategies": strategies,
        "regime_history": regime_history,
    }


def serialize_factors(pipeline: dict) -> dict:
    wf_histories = pipeline.get("wf_histories", {})
    result = {}

    for cat_name in ["Growth", "Inflation", "Liquidity", "Tactical"]:
        history = wf_histories.get(cat_name, [])
        if not history:
            continue

        # Build selection matrix
        all_sel = set()
        for h in history:
            all_sel.update(h.get("selected", []))
        all_sel_sorted = sorted(all_sel)

        # Frequency
        freq_counts = {}
        for ind in all_sel_sorted:
            freq_counts[ind] = sum(1 for h in history if ind in h.get("selected", []))
        freq_sorted = sorted(freq_counts.items(), key=lambda x: x[1], reverse=True)
        frequency = [
            {"indicator": name, "count": cnt, "pct": round(cnt / len(history), 3)}
            for name, cnt in freq_sorted
        ]

        # Latest selection
        latest = history[-1]
        latest_sel = {
            "date": latest["date"].strftime("%Y-%m-%d") if hasattr(latest["date"], "strftime") else str(latest["date"]),
            "indicators": [
                {"name": n, "ic": _sf(ic)}
                for n, ic in sorted(
                    latest.get("ics", {}).items(),
                    key=lambda x: abs(x[1]),
                    reverse=True,
                )
            ],
        }

        # IC heatmap (top 15)
        top15_names = [f["indicator"] for f in frequency[:15]]
        hm_dates = []
        hm_values = {name: [] for name in top15_names}
        for h in history:
            d = h["date"].strftime("%Y-%m") if hasattr(h["date"], "strftime") else str(h["date"])[:7]
            hm_dates.append(d)
            ics = h.get("ics", {})
            for name in top15_names:
                hm_values[name].append(_sf(ics.get(name, 0.0)))

        result[cat_name] = {
            "n_rebalances": len(history),
            "n_unique_indicators": len(all_sel_sorted),
            "frequency": frequency,
            "latest_selection": latest_sel,
            "ic_heatmap": {
                "dates": hm_dates,
                "indicators": top15_names,
                "values": [hm_values[n] for n in top15_names],
            },
        }

    return result


def serialize_current_signal(pipeline: dict) -> dict:
    wf_histories = pipeline.get("wf_histories", {})

    category_signals = {}
    factor_selections = {}

    for cat_name in ["Growth", "Inflation", "Liquidity", "Tactical", "Regime", "Blended"]:
        history = wf_histories.get(cat_name, [])
        if not history:
            continue
        latest = history[-1]
        eq_wt = latest.get("eq_weight", 0.5)

        if eq_wt >= 0.70:
            label = "Risk-On"
        elif eq_wt <= 0.30:
            label = "Risk-Off"
        else:
            label = "Neutral"

        sig = {
            "eq_weight": _sf(eq_wt),
            "label": label,
            "date": latest["date"].strftime("%Y-%m-%d") if hasattr(latest["date"], "strftime") else str(latest["date"]),
        }
        if cat_name == "Regime":
            sig["regime"] = latest.get("regime", "")
            sig["growth_pctile"] = _sf(latest.get("growth_pctile"))
            sig["inflation_pctile"] = _sf(latest.get("inflation_pctile"))

        category_signals[cat_name] = sig

        # Factor selections for non-Regime categories
        if cat_name in ("Growth", "Inflation", "Liquidity", "Tactical"):
            ics = latest.get("ics", {})
            factor_selections[cat_name] = [
                {"name": n, "ic": _sf(ic)}
                for n, ic in sorted(ics.items(), key=lambda x: abs(x[1]), reverse=True)
            ]

    return {
        "category_signals": category_signals,
        "factor_selections": factor_selections,
    }


# ---------------------------------------------------------------------------
# Legacy DB upsert (macro_regime_strategy table)
# ---------------------------------------------------------------------------


def _save_to_legacy_db(
    index_name: str,
    backtest: dict,
    factors: dict,
    current_signal: dict,
) -> None:
    """Upsert to the old macro_regime_strategy table (backward compat)."""
    with Session() as session:
        existing = (
            session.query(MacroRegimeStrategyDB)
            .filter_by(index_name=index_name)
            .first()
        )
        if existing:
            existing.computed_at = datetime.now(timezone.utc)
            existing.backtest = backtest
            existing.factors = factors
            existing.current_signal = current_signal
        else:
            session.add(
                MacroRegimeStrategyDB(
                    index_name=index_name,
                    computed_at=datetime.now(timezone.utc),
                    backtest=backtest,
                    factors=factors,
                    current_signal=current_signal,
                )
            )


# Keep old name as alias for any external callers
save_to_db = _save_to_legacy_db


# ---------------------------------------------------------------------------
# Optimized parameters
# ---------------------------------------------------------------------------

OPTIMIZED_PARAMS = dict(
    lookback_years=5,
    rebal_weeks=4,              # Grid search optimal: 4w rebalancing
    horizon_key="6m",
    sma_window=30,
    macro_trend_split=(0.6, 0.4),
    alloc_range=(0.10, 0.90),
    soft_zone=(0.25, 0.75),
    blend_weights=None,
    use_category_horizons=True,
    apply_publication_lags=True,
    benchmark_weight=0.50,
    txcost_bps=10,
    composite_mode="ic_weighted",  # Pre-flipped z-scores + IC-weighted composites
    universe_path="reports/macro/v2_universe.json",
)


# ---------------------------------------------------------------------------
# Main compute functions
# ---------------------------------------------------------------------------


def compute_and_save(index_name: str) -> None:
    """Run walk-forward pipeline for one index and save to DB.

    Saves to ``macro_regime_strategy`` table (backtest, factors, current_signal).
    """
    from ix.core.macro.wf_backtest import run_full_wf_pipeline

    t0 = time.time()
    logger.info(f"Computing regime strategy for {index_name}...")

    pipeline = run_full_wf_pipeline(index_name=index_name, **OPTIMIZED_PARAMS)

    if "error" in pipeline:
        logger.error(f"Pipeline error for {index_name}: {pipeline['error']}")
        return

    bt = serialize_backtest(pipeline)
    fac = serialize_factors(pipeline)
    sig = serialize_current_signal(pipeline)
    _save_to_legacy_db(index_name, bt, fac, sig)

    elapsed = time.time() - t0
    logger.info(f"Saved {index_name} in {elapsed:.1f}s")


def compute_all() -> None:
    """Run pipeline for all indices."""
    for name in INDEX_MAP:
        try:
            compute_and_save(name)
        except Exception as e:
            logger.warning(f"Failed for {name}: {e}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    args = [a for a in sys.argv[1:]]

    if args:
        target = args[0]
        if target not in INDEX_MAP:
            logger.error(f"Unknown index: {target}. Available: {list(INDEX_MAP.keys())}")
            sys.exit(1)
        compute_and_save(target)
    else:
        compute_all()
