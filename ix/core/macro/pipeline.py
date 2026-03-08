"""Pipeline orchestration and DB serialization for macro outlook.

This module ties together data loading, computation, and persistence.
It provides:
  - compute_full_pipeline(): runs the entire three-horizon computation
  - serialize_*(): convert results to JSON-safe dicts
  - save_to_db(): upsert results to the macro_outlook table
  - compute_and_save(): convenience wrapper
  - compute_all_targets(): batch computation for the scheduler
"""

import numpy as np
import pandas as pd

from ix.core.macro.config import (
    TARGET_INDICES,
    REGIME_NAMES,
    LIQUIDITY_PHASES,
)
from ix.core.macro.indicators import (
    GROWTH_LOADERS,
    INFLATION_LOADERS,
    LIQUIDITY_LOADERS,
    LIQUIDITY_WEIGHTS,
    TACTICAL_LOADERS,
    KOREA_LOADERS,
    INDICATOR_DESCRIPTIONS,
    load_growth_data,
    load_inflation_data,
    load_liquidity_data,
    load_tactical_data,
    load_korea_data,
    load_target_index,
)
from ix.core.macro.engine import (
    build_axis_composite,
    compute_regime_probabilities,
    compute_transition_matrix,
    project_probabilities,
    compute_liquidity_cycle,
    compute_tactical_score,
    compute_allocation,
    regime_forward_return_stats,
    liquidity_phase_forward_stats,
    tactical_bucket_forward_stats,
    dominant_regime,
)
from ix.core.macro.backtest import run_backtest


# ==============================================================================
# SERIALIZATION HELPERS
# ==============================================================================


def _safe_float(v):
    """Convert a value to float, mapping NaN/None to None for JSON."""
    if v is None:
        return None
    try:
        f = float(v)
        return None if (pd.isna(f) or np.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def _series_to_list(s: pd.Series) -> list:
    """Convert a pandas Series to a list of JSON-safe floats."""
    return [_safe_float(v) for v in s.values]


def _dates_to_list(idx: pd.DatetimeIndex) -> list:
    """Convert a DatetimeIndex to ISO date strings."""
    return [d.strftime("%Y-%m-%d") for d in idx]


# ==============================================================================
# FULL COMPUTATION PIPELINE
# ==============================================================================


def compute_full_pipeline(
    target_name: str,
    fwd_weeks: int = 13,
    z_window: int = 78,
    tail_years: int = 20,
    temperature: float = 1.0,
    regime_w: float = 0.40,
    liquidity_w: float = 0.30,
    tactical_w: float = 0.30,
    tc_bps: float = 10.0,
) -> dict:
    """Compute the full three-horizon macro pipeline for a target index.

    This is the main entry point that loads all data, normalizes indicators,
    builds composites, computes regime probabilities, liquidity phase,
    tactical scores, and blended allocation.

    Args:
        target_name: Key into TARGET_INDICES (e.g., "S&P 500").
        fwd_weeks: Forward return horizon for regime stats.
        z_window: Base rolling z-score window in weeks.
        tail_years: How many years of history to retain for display.
        temperature: Softmax temperature for regime probabilities.
        regime_w: Weight for regime signal in allocation.
        liquidity_w: Weight for liquidity cycle in allocation.
        tactical_w: Weight for tactical score in allocation.
        tc_bps: Transaction cost in basis points for backtest.

    Returns:
        Dict with all computed results for downstream serialization.
    """
    if target_name not in TARGET_INDICES:
        raise KeyError(f"Unknown target '{target_name}'.")
    target = TARGET_INDICES[target_name]
    target_px = load_target_index(target.ticker, "W")
    if target_px.empty:
        raise ValueError(f"No target price history found for '{target_name}'.")

    # Load data (parallel within each group)
    growth_raw = load_growth_data("W")
    inflation_raw = load_inflation_data("W")
    liquidity_raw = load_liquidity_data("W")
    tactical_raw = load_tactical_data("W")

    # Add Korea indicators if applicable
    if target.region == "korea":
        korea_data = load_korea_data("W")
        growth_raw.update(korea_data)

    # Build composites
    growth_norm, growth_composite = build_axis_composite(
        growth_raw, GROWTH_LOADERS + KOREA_LOADERS, z_window
    )
    inflation_norm, inflation_composite = build_axis_composite(
        inflation_raw, INFLATION_LOADERS, z_window
    )
    liquidity_norm, liquidity_composite = build_axis_composite(
        liquidity_raw, LIQUIDITY_LOADERS, z_window,
        weights=LIQUIDITY_WEIGHTS, ema_halflife=3,
    )
    tactical_norm, tactical_composite = build_axis_composite(
        tactical_raw, TACTICAL_LOADERS, z_window
    )

    # Horizon 2: Bayesian regime probabilities
    regime_probs = compute_regime_probabilities(
        growth_composite, inflation_composite, temperature
    )

    # Trim to tail_years
    if not regime_probs.empty:
        cutoff = regime_probs.index[-1] - pd.DateOffset(years=tail_years)
        regime_probs = regime_probs[regime_probs.index >= cutoff]
        growth_composite = growth_composite[growth_composite.index >= cutoff]
        inflation_composite = inflation_composite[
            inflation_composite.index >= cutoff
        ]
        liquidity_composite = liquidity_composite[
            liquidity_composite.index >= cutoff
        ]
        tactical_composite = tactical_composite[
            tactical_composite.index >= cutoff
        ]

    # Horizon 1: Liquidity cycle
    liq_phase = compute_liquidity_cycle(liquidity_composite)

    # Horizon 3: Tactical score
    tac_score = compute_tactical_score(tactical_composite)

    # Transition matrix
    trans_matrix = compute_transition_matrix(regime_probs)

    # Forward return stats
    regime_stats = regime_forward_return_stats(regime_probs, target_px, fwd_weeks)

    # Combined allocation (uses continuous liquidity composite, not categorical phase)
    alloc = compute_allocation(
        regime_probs, liquidity_composite, tac_score, regime_w, liquidity_w, tactical_w
    )

    # Component allocations (single-signal backtests)
    alloc_regime = compute_allocation(
        regime_probs, liquidity_composite, tac_score,
        regime_weight=1.0, liquidity_weight=0.0, tactical_weight=0.0,
    )
    alloc_liquidity = compute_allocation(
        regime_probs, liquidity_composite, tac_score,
        regime_weight=0.0, liquidity_weight=1.0, tactical_weight=0.0,
    )
    alloc_tactical = compute_allocation(
        regime_probs, liquidity_composite, tac_score,
        regime_weight=0.0, liquidity_weight=0.0, tactical_weight=1.0,
    )

    # Backtest: combined
    equity_df, weights_series, stats_df = run_backtest(
        alloc, target_px, target_name, tc_bps
    )
    # Component backtests
    eq_regime, w_regime, st_regime = run_backtest(
        alloc_regime, target_px, target_name, tc_bps
    )
    eq_liq, w_liq, st_liq = run_backtest(
        alloc_liquidity, target_px, target_name, tc_bps
    )
    eq_tac, w_tac, st_tac = run_backtest(
        alloc_tactical, target_px, target_name, tc_bps
    )

    # Phase and tactical forward stats
    liq_fwd_stats = liquidity_phase_forward_stats(liq_phase, target_px, fwd_weeks)
    tac_fwd_stats = tactical_bucket_forward_stats(tac_score, target_px, fwd_weeks)

    return {
        "target_px": target_px,
        "growth_norm": growth_norm,
        "inflation_norm": inflation_norm,
        "liquidity_norm": liquidity_norm,
        "tactical_norm": tactical_norm,
        "growth_composite": growth_composite,
        "inflation_composite": inflation_composite,
        "liquidity_composite": liquidity_composite,
        "tactical_composite": tactical_composite,
        "regime_probs": regime_probs,
        "liq_phase": liq_phase,
        "tac_score": tac_score,
        "trans_matrix": trans_matrix,
        "regime_stats": regime_stats,
        "liq_fwd_stats": liq_fwd_stats,
        "tac_fwd_stats": tac_fwd_stats,
        "alloc": alloc,
        "equity_df": equity_df,
        "weights_series": weights_series,
        "stats_df": stats_df,
        # Component backtests
        "eq_regime": eq_regime,
        "st_regime": st_regime,
        "w_regime": w_regime,
        "eq_liq": eq_liq,
        "st_liq": st_liq,
        "w_liq": w_liq,
        "eq_tac": eq_tac,
        "st_tac": st_tac,
        "w_tac": w_tac,
    }


# ==============================================================================
# SERIALIZATION
# ==============================================================================


def serialize_snapshot(results: dict, target_name: str) -> dict:
    """Serialize current state and indicators to the snapshot JSON format.

    Returns a dict matching the expected JSONB schema for macro_outlook.snapshot.
    """
    regime_probs = results["regime_probs"]
    growth_composite = results["growth_composite"]
    inflation_composite = results["inflation_composite"]
    liquidity_composite = results["liquidity_composite"]
    tac_score = results["tac_score"]
    liq_phase = results["liq_phase"]
    trans_matrix = results["trans_matrix"]
    regime_stats = results["regime_stats"]
    alloc = results["alloc"]

    if regime_probs.empty:
        return {"error": "Insufficient data for regime computation"}

    # Current values
    current_probs = {
        r: _safe_float(regime_probs[r].iloc[-1])
        for r in REGIME_NAMES
        if r in regime_probs.columns
    }
    current_regime = max(current_probs, key=current_probs.get)
    current_growth = _safe_float(
        growth_composite.iloc[-1] if not growth_composite.empty else 0.0
    )
    current_inflation = _safe_float(
        inflation_composite.iloc[-1] if not inflation_composite.empty else 0.0
    )
    current_liq = _safe_float(
        liquidity_composite.iloc[-1] if not liquidity_composite.empty else 0.0
    )
    current_tac = _safe_float(
        tac_score.iloc[-1] if not tac_score.empty else 0.0
    )
    current_alloc = _safe_float(
        alloc.iloc[-1] if not alloc.empty else 0.50
    )
    current_phase = (
        str(liq_phase.iloc[-1]) if not liq_phase.empty else "Unknown"
    )

    # Forward projections
    current_prob_vec = np.array(
        [current_probs.get(r, 0.25) for r in REGIME_NAMES]
    )
    projections = {}
    for label, steps in [("1m", 4), ("3m", 13), ("6m", 26)]:
        proj = project_probabilities(current_prob_vec, trans_matrix, steps)
        projections[label] = {
            r: _safe_float(p) for r, p in zip(REGIME_NAMES, proj)
        }

    # Indicator readings
    indicators = {}
    for axis, norm_dict in [
        ("growth", results["growth_norm"]),
        ("inflation", results["inflation_norm"]),
        ("liquidity", results["liquidity_norm"]),
        ("tactical", results["tactical_norm"]),
    ]:
        axis_indicators = []
        for name, z in norm_dict.items():
            if z.empty:
                continue
            val = _safe_float(z.iloc[-1])
            if val is None:
                continue
            signal = (
                "Bullish" if val > 0.5 else ("Bearish" if val < -0.5 else "Neutral")
            )
            axis_indicators.append(
                {
                    "name": name,
                    "z": val,
                    "signal": signal,
                    "desc": INDICATOR_DESCRIPTIONS.get(name, ""),
                }
            )
        indicators[axis] = axis_indicators

    # Transition matrix
    trans_data = {
        "labels": trans_matrix.index.tolist(),
        "values": [
            [_safe_float(v) for v in row] for row in trans_matrix.values
        ],
    }

    # Regime stats
    regime_stats_list = []
    if not regime_stats.empty:
        for _, row in regime_stats.iterrows():
            regime_stats_list.append(
                {
                    "regime": row["Regime"],
                    "mean_fwd_ret": _safe_float(row["Mean Fwd Ret (%)"]),
                    "median_fwd_ret": _safe_float(row["Median Fwd Ret (%)"]),
                    "std": _safe_float(row["Std (%)"]),
                    "sharpe": _safe_float(row["Sharpe"]),
                    "pct_positive": _safe_float(row["% Positive"]),
                    "n": int(row["N"]),
                }
            )

    # Liquidity phase forward stats
    liq_fwd_stats = results.get("liq_fwd_stats", pd.DataFrame())
    liq_stats_list = []
    if not liq_fwd_stats.empty:
        for _, row in liq_fwd_stats.iterrows():
            liq_stats_list.append(
                {
                    "phase": row["phase"],
                    "mean_fwd_ret": _safe_float(row["mean_fwd_ret"]),
                    "median_fwd_ret": _safe_float(row["median_fwd_ret"]),
                    "std": _safe_float(row["std"]),
                    "sharpe": _safe_float(row["sharpe"]),
                    "pct_positive": _safe_float(row["pct_positive"]),
                    "n": int(row["n"]),
                }
            )

    # Tactical bucket forward stats
    tac_fwd_stats = results.get("tac_fwd_stats", pd.DataFrame())
    tac_stats_list = []
    if not tac_fwd_stats.empty:
        for _, row in tac_fwd_stats.iterrows():
            tac_stats_list.append(
                {
                    "bucket": row["bucket"],
                    "mean_fwd_ret": _safe_float(row["mean_fwd_ret"]),
                    "median_fwd_ret": _safe_float(row["median_fwd_ret"]),
                    "std": _safe_float(row["std"]),
                    "sharpe": _safe_float(row["sharpe"]),
                    "pct_positive": _safe_float(row["pct_positive"]),
                    "n": int(row["n"]),
                }
            )

    return {
        "current": {
            "regime": current_regime,
            "confidence": current_probs.get(current_regime, 0.25),
            "growth": current_growth,
            "inflation": current_inflation,
            "liquidity": current_liq,
            "tactical": current_tac,
            "allocation": current_alloc,
            "liq_phase": current_phase,
            "regime_probs": current_probs,
        },
        "projections": projections,
        "indicator_counts": {
            "growth": len(results["growth_norm"]),
            "inflation": len(results["inflation_norm"]),
            "liquidity": len(results["liquidity_norm"]),
            "tactical": len(results["tactical_norm"]),
        },
        "indicators": indicators,
        "transition_matrix": trans_data,
        "regime_stats": regime_stats_list,
        "liq_phase_stats": liq_stats_list,
        "tactical_stats": tac_stats_list,
    }


def serialize_timeseries(results: dict) -> dict:
    """Serialize time series data to the timeseries JSON format.

    Returns a dict with dates array and value arrays matching the expected
    JSONB schema for macro_outlook.timeseries.
    """
    regime_probs = results["regime_probs"]
    growth_composite = results["growth_composite"]
    inflation_composite = results["inflation_composite"]
    liquidity_composite = results["liquidity_composite"]
    tactical_composite = results["tactical_composite"]
    alloc = results["alloc"]
    liq_phase = results["liq_phase"]
    target_px = results["target_px"]

    if regime_probs.empty:
        return {"dates": [], "target_px": []}

    # Use regime_probs index as the canonical timeline
    dates = regime_probs.index

    return {
        "dates": _dates_to_list(dates),
        "target_px": _series_to_list(target_px.reindex(dates).ffill()),
        "growth": _series_to_list(growth_composite.reindex(dates).ffill()),
        "inflation": _series_to_list(inflation_composite.reindex(dates).ffill()),
        "liquidity": _series_to_list(liquidity_composite.reindex(dates).ffill()),
        "tactical": _series_to_list(
            tactical_composite.reindex(dates).ffill()
        ),
        "allocation": _series_to_list(alloc.reindex(dates).ffill()),
        "liq_phase": [
            str(v) for v in liq_phase.reindex(dates).ffill().values
        ],
        "regime_probs": {
            r: _series_to_list(regime_probs[r])
            for r in REGIME_NAMES
            if r in regime_probs.columns
        },
    }


def _serialize_component_bt(results: dict, key_prefix: str, equity_df_main) -> dict:
    """Serialize a component backtest (regime-only, liquidity-only, tactical-only)."""
    eq = results.get(f"eq_{key_prefix}", pd.DataFrame())
    st = results.get(f"st_{key_prefix}", pd.DataFrame())
    w = results.get(f"w_{key_prefix}", pd.Series(dtype=float))
    if eq.empty:
        return {"equity": [], "weight": [], "stats": {}}
    stats_row = {}
    if not st.empty:
        row = st.iloc[1] if len(st) > 1 else st.iloc[0]
        stats_row = {
            "ann_return": _safe_float(row.get("Ann Return (%)", 0)),
            "ann_vol": _safe_float(row.get("Ann Vol (%)", 0)),
            "sharpe": _safe_float(row.get("Sharpe", 0)),
            "max_dd": _safe_float(row.get("Max DD (%)", 0)),
            "info_ratio": _safe_float(row.get("Info Ratio", 0)),
            "ann_turnover": _safe_float(row.get("Ann Turnover (%)", 0)),
        }
    return {
        "equity": [_safe_float(v) for v in eq["strategy"]],
        "weight": [
            _safe_float(v * 100)
            for v in w.reindex(eq["date"]).ffill().values
        ] if not w.empty else [],
        "stats": stats_row,
    }


def serialize_backtest(results: dict, target_name: str, tc_bps: float) -> dict:
    """Serialize backtest results to the backtest JSON format.

    Returns a dict with equity curves and statistics matching the expected
    JSONB schema for macro_outlook.backtest.
    """
    equity_df = results["equity_df"]
    weights_series = results["weights_series"]
    stats_df = results["stats_df"]

    if equity_df.empty:
        return {"dates": [], "stats": []}

    # Serialize stats
    stats_list = []
    for _, row in stats_df.iterrows():
        stats_list.append(
            {
                "label": row["Strategy"],
                "ann_return": _safe_float(row["Ann Return (%)"]),
                "ann_vol": _safe_float(row["Ann Vol (%)"]),
                "sharpe": _safe_float(row["Sharpe"]),
                "max_dd": _safe_float(row["Max DD (%)"]),
                "info_ratio": _safe_float(row.get("Info Ratio", 0)),
                "tracking_err": _safe_float(row.get("Tracking Err (%)", 0)),
                "ann_turnover": _safe_float(row.get("Ann Turnover (%)", 0)),
            }
        )

    return {
        "dates": _dates_to_list(equity_df["date"]),
        "strategy_equity": [_safe_float(v) for v in equity_df["strategy"]],
        "benchmark_equity": [_safe_float(v) for v in equity_df["benchmark"]],
        "full_equity": [_safe_float(v) for v in equity_df["full"]],
        "strategy_weight": [
            _safe_float(v * 100)
            for v in weights_series.reindex(equity_df["date"]).ffill().values
        ],
        "stats": stats_list,
        # Component backtests
        "regime_only": _serialize_component_bt(results, "regime", equity_df),
        "liquidity_only": _serialize_component_bt(results, "liq", equity_df),
        "tactical_only": _serialize_component_bt(results, "tac", equity_df),
    }


# ==============================================================================
# DATABASE PERSISTENCE
# ==============================================================================


def save_to_db(
    target_name: str, snapshot: dict, timeseries: dict, backtest_data: dict
) -> None:
    """Upsert macro outlook results to the database.

    Creates or updates the macro_outlook row for the given target.
    """
    from datetime import datetime, timezone

    from ix.db.conn import Session
    from ix.db.models.macro_outlook import MacroOutlook

    with Session() as session:
        existing = (
            session.query(MacroOutlook)
            .filter_by(target_name=target_name)
            .first()
        )
        if existing:
            existing.computed_at = datetime.now(timezone.utc)
            existing.snapshot = snapshot
            existing.timeseries = timeseries
            existing.backtest = backtest_data
        else:
            session.add(
                MacroOutlook(
                    target_name=target_name,
                    computed_at=datetime.now(timezone.utc),
                    snapshot=snapshot,
                    timeseries=timeseries,
                    backtest=backtest_data,
                )
            )


# ==============================================================================
# CONVENIENCE WRAPPERS
# ==============================================================================


def compute_and_save(target_name: str, **params) -> None:
    """Compute the full pipeline and save results to DB.

    Args:
        target_name: Key into TARGET_INDICES.
        **params: Passed to compute_full_pipeline().
    """
    results = compute_full_pipeline(target_name, **params)
    snapshot = serialize_snapshot(results, target_name)
    ts_data = serialize_timeseries(results)
    bt_data = serialize_backtest(
        results, target_name, params.get("tc_bps", 10.0)
    )
    save_to_db(target_name, snapshot, ts_data, bt_data)


def compute_all_targets() -> None:
    """Compute macro outlook for all default targets.

    Called by the scheduler every 4 hours.
    """
    from ix.misc import get_logger

    logger = get_logger(__name__)
    DEFAULT_TARGETS = ["S&P 500", "KOSPI", "Nasdaq 100", "KOSDAQ"]
    for name in DEFAULT_TARGETS:
        try:
            logger.info(f"Computing macro outlook for {name}...")
            compute_and_save(name)
            logger.info(f"Macro outlook for {name} saved.")
        except Exception as e:
            logger.warning(f"Failed to compute macro for {name}: {e}")
