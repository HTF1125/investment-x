"""IC-weighted multi-regime ensemble strategy.

Combines ALL registered 1D regimes into a single walk-forward allocation
strategy.  For each asset in the universe, the algorithm selects the
regimes that have statistically significant predictive power (Spearman IC,
expanding window) and blends their Z-scores weighted by IC.  Assets with
positive combined signal receive proportional allocation; when no asset
has a positive signal the portfolio goes to cash (BIL).

The output matches the ``StrategyData`` frontend interface (so
``StrategyTab`` renders it directly) plus ensemble-specific metadata:
``current_weights``, ``regime_drivers``, and ``ensemble_meta``.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .compute import (
    DEFAULT_ASSET_TICKERS,
    _load_asset_prices,
    _safe_float,
)
from .registry import list_regimes

log = logging.getLogger(__name__)


def compute_ensemble_strategy(
    tickers: dict[str, str] | None = None,
    warmup_months: int = 60,
    lag_months: int = 1,
    horizon_months: int = 3,
    ic_threshold: float = 0.10,
    cost_bps: int = 10,
    cash_ticker: str = "BIL",
) -> dict | None:
    """Walk-forward IC-weighted multi-regime ensemble.

    Args:
        tickers: Asset universe (display name -> DB code).  Defaults to
            the broad 11-ETF macro universe.

    Returns a dict compatible with the frontend ``StrategyData`` interface
    (plus ``current_weights``, ``regime_drivers``, ``ensemble_meta``), or
    ``None`` if insufficient data.
    """
    if tickers is None:
        tickers = DEFAULT_ASSET_TICKERS

    # ── 1. Build all regime Z-scores ──────────────────────────────
    regs = list_regimes()
    regime_z: dict[str, pd.Series] = {}  # key -> Z-score series

    for reg in regs:
        if not reg.regime_class or not reg.dimensions:
            continue
        try:
            regime = reg.regime_class()
            df = regime.build(**reg.default_params)
            z_col = f"{reg.dimensions[0]}_Z"
            if z_col in df.columns:
                regime_z[reg.key] = df[z_col]
        except Exception as exc:
            log.warning("Ensemble: failed to build '%s': %s", reg.key, exc)

    if not regime_z:
        return None

    regime_keys = list(regime_z.keys())
    log.info("Ensemble: built %d regime Z-scores", len(regime_keys))

    # ── 2. Load asset prices ──────────────────────────────────────
    try:
        prices = _load_asset_prices(tickers)
    except Exception as exc:
        log.warning("Ensemble: price load failed: %s", exc)
        return None

    if prices.empty:
        return None

    rets = prices.pct_change().dropna(how="all")
    common_idx = rets.index
    has_cash = cash_ticker in rets.columns
    alloc_assets = [t for t in prices.columns if t != cash_ticker]

    # ── 3. Align Z-scores to common index ─────────────────────────
    z_matrix = pd.DataFrame(index=common_idx)
    for key, z in regime_z.items():
        z_matrix[key] = z.reindex(common_idx, method="ffill")

    # Forward returns per asset (for IC computation)
    fwd_matrix = pd.DataFrame(index=common_idx)
    for asset in alloc_assets:
        if asset in prices.columns:
            fwd_matrix[asset] = prices[asset].pct_change(horizon_months).shift(-horizon_months)

    if len(common_idx) < warmup_months + lag_months + 12:
        return None

    # ── 4. Pre-compute expanding IC series ────────────────────────
    # For each (regime, asset) pair, compute IC at every expanding window
    # point.  This vectorises the expensive spearmanr calls.
    log.info("Ensemble: computing expanding IC for %d regime-asset pairs...",
             len(regime_keys) * len(alloc_assets))

    ic_store: dict[tuple[str, str], pd.Series] = {}    # (regime, asset) -> IC series
    pval_store: dict[tuple[str, str], pd.Series] = {}  # (regime, asset) -> p-val series

    for rkey in regime_keys:
        sig = z_matrix[rkey].shift(lag_months)  # lagged signal
        for asset in alloc_assets:
            if asset not in fwd_matrix.columns:
                continue
            merged = pd.concat([
                sig.rename("signal"),
                fwd_matrix[asset].rename("fwd"),
            ], axis=1).dropna()

            if len(merged) < warmup_months + 30:
                continue

            ics: list[float] = []
            pvals: list[float] = []
            dates_out: list = []

            for end in range(warmup_months, len(merged)):
                window = merged.iloc[:end + 1]
                rho, pval = spearmanr(window["signal"], window["fwd"])
                ics.append(float(rho) if np.isfinite(rho) else 0.0)
                pvals.append(float(pval) if np.isfinite(pval) else 1.0)
                dates_out.append(merged.index[end])

            ic_store[(rkey, asset)] = pd.Series(ics, index=dates_out)
            pval_store[(rkey, asset)] = pd.Series(pvals, index=dates_out)

    log.info("Ensemble: IC computation done (%d pairs)", len(ic_store))

    # ── 5. Walk-forward allocation loop ───────────────────────────
    wf_rets: list[float] = []
    ew_rets: list[float] = []
    spy_rets: list[float] = []
    wf_dates: list[str] = []
    holdings_list: list[dict[str, float]] = []
    prev_weights: dict[str, float] = {}
    has_spy = "SPY" in rets.columns

    # Track per-asset regime drivers at each month (only keep latest)
    latest_drivers: dict[str, list[dict[str, Any]]] = {}

    for pos in range(warmup_months + lag_months, len(common_idx)):
        t = common_idx[pos]
        lagged_t = common_idx[pos - lag_months]

        # For each asset, combine Z-scores from significant regimes
        asset_combined_z: dict[str, float] = {}
        month_drivers: dict[str, list[dict[str, Any]]] = {}

        for asset in alloc_assets:
            sig_regimes: list[tuple[str, float, float]] = []  # (key, ic, z_current)

            for rkey in regime_keys:
                pair = (rkey, asset)
                if pair not in ic_store:
                    continue

                ic_series = ic_store[pair]
                pval_series = pval_store[pair]

                # Get IC and p-value at the lagged date (or nearest before)
                ic_at_t = ic_series.asof(lagged_t)
                pval_at_t = pval_series.asof(lagged_t)

                if pd.isna(ic_at_t) or pd.isna(pval_at_t):
                    continue
                if pval_at_t >= ic_threshold:
                    continue

                z_val = z_matrix[rkey].iloc[pos - lag_months]
                if pd.isna(z_val):
                    continue

                sig_regimes.append((rkey, float(ic_at_t), float(z_val)))

            if sig_regimes:
                # IC-weighted combination: signed IC in numerator, |IC| in denominator
                numer = sum(ic * z for _, ic, z in sig_regimes)
                denom = sum(abs(ic) for _, ic, _ in sig_regimes)
                combined = numer / denom if denom > 1e-9 else 0.0
                asset_combined_z[asset] = combined
                month_drivers[asset] = [
                    {"regime": rkey, "ic": round(ic, 4), "z_current": round(z, 3)}
                    for rkey, ic, z in sorted(sig_regimes, key=lambda x: abs(x[1]), reverse=True)
                ]
            else:
                asset_combined_z[asset] = 0.0

        # Allocate proportional to positive combined Z (no cap — IC
        # weighting already gives weak signals small weights naturally)
        positive = {a: z for a, z in asset_combined_z.items() if z > 0}

        if positive:
            total_z = sum(positive.values())
            weights = {a: z / total_z for a, z in positive.items()}
        else:
            weights = {cash_ticker: 1.0} if has_cash else {}

        holdings_list.append(weights)
        latest_drivers = month_drivers

        # Turnover cost
        all_tickers = set(list(weights.keys()) + list(prev_weights.keys()))
        turnover = sum(abs(weights.get(tk, 0.0) - prev_weights.get(tk, 0.0)) for tk in all_tickers)
        txn_cost = turnover * cost_bps / 10_000
        prev_weights = weights

        # Portfolio return (net of cost)
        row = rets.iloc[pos]
        month_ret = sum(
            w * (float(row[tk]) if tk in row.index and pd.notna(row[tk]) else 0.0)
            for tk, w in weights.items()
        ) - txn_cost
        wf_rets.append(month_ret)

        # Benchmarks
        valid = [float(row[c]) for c in alloc_assets if c in row.index and pd.notna(row[c])]
        ew_rets.append(np.mean(valid) if valid else 0.0)
        spy_rets.append(float(row["SPY"]) if has_spy and pd.notna(row.get("SPY")) else 0.0)

        wf_dates.append(t.strftime("%Y-%m-%d"))

    if len(wf_rets) < 12:
        return None

    # ── 6. Build output ───────────────────────────────────────────
    def build_equity(monthly: list[float]) -> list[float]:
        eq = [1.0]
        for r in monthly:
            eq.append(eq[-1] * (1 + r))
        return eq

    def build_drawdown(equity: list[float]) -> list[float]:
        peak = equity[0]
        dd = []
        for v in equity:
            if v > peak:
                peak = v
            dd.append(v / peak - 1 if peak > 0 else 0.0)
        return dd

    def build_stats(monthly: list[float], equity: list[float]) -> dict:
        n = len(monthly)
        if n < 2:
            return {"cagr": 0.0, "ann_vol": 0.0, "sharpe": 0.0, "max_dd": 0.0, "months": n}
        arr = np.array(monthly)
        cagr = (equity[-1] / equity[0]) ** (12 / n) - 1 if equity[0] > 0 else 0.0
        ann_vol = float(arr.std()) * float(np.sqrt(12))
        sharpe = cagr / ann_vol if ann_vol > 1e-9 else 0.0
        dd = build_drawdown(equity)
        max_dd = min(dd)
        return {
            "cagr": _safe_float(cagr) or 0.0,
            "ann_vol": _safe_float(ann_vol) or 0.0,
            "sharpe": _safe_float(sharpe) or 0.0,
            "max_dd": _safe_float(max_dd) or 0.0,
            "months": n,
        }

    wf_eq = build_equity(wf_rets)
    ew_eq = build_equity(ew_rets)
    spy_eq = build_equity(spy_rets)
    eq_dates = [wf_dates[0]] + wf_dates

    # Yearly returns
    yearly: list[dict] = []
    year_groups: dict[int, list[tuple[float, float, float]]] = {}
    for i, d in enumerate(wf_dates):
        yr = int(d[:4])
        if yr not in year_groups:
            year_groups[yr] = []
        year_groups[yr].append((wf_rets[i], ew_rets[i], spy_rets[i]))

    for yr in sorted(year_groups.keys()):
        rows = year_groups[yr]
        wf_yr = float(np.prod([1 + r for r, _, _ in rows]) - 1)
        ew_yr = float(np.prod([1 + r for _, r, _ in rows]) - 1)
        sp_yr = float(np.prod([1 + r for _, _, r in rows]) - 1)
        yearly.append({
            "year": yr,
            "wf_best": _safe_float(wf_yr) or 0.0,
            "diversified": _safe_float(ew_yr) or 0.0,
            "spy": _safe_float(sp_yr) or 0.0,
            "wf_alpha": _safe_float(wf_yr - sp_yr) or 0.0,
            "div_alpha": _safe_float(ew_yr - sp_yr) or 0.0,
        })

    # Current weights (last month)
    current_weights = holdings_list[-1] if holdings_list else {}

    # Add ic_pvalue to latest_drivers from pval_store
    for asset, drivers in latest_drivers.items():
        for d in drivers:
            pair = (d["regime"], asset)
            if pair in pval_store:
                pv = pval_store[pair]
                last_pval = pv.iloc[-1] if len(pv) > 0 else 1.0
                d["ic_pvalue"] = round(float(last_pval), 4)
            else:
                d["ic_pvalue"] = 1.0

    return {
        # StrategyData-compatible fields
        "start_date": wf_dates[0] if wf_dates else None,
        "end_date": wf_dates[-1] if wf_dates else None,
        "months": len(wf_rets),
        "wf_lookback": warmup_months,
        "num_assets": len(alloc_assets),
        "lag_months": lag_months,
        "models": {
            "wf_best_asset": {
                "label": "IC-Weighted Ensemble",
                "description": "Walk-forward IC-weighted combination of all regimes",
                "dates": eq_dates,
                "equity": [_safe_float(v) or 0.0 for v in wf_eq],
                "drawdown": [_safe_float(v) or 0.0 for v in build_drawdown(wf_eq)],
                "stats": build_stats(wf_rets, wf_eq),
            },
            "diversified": {
                "label": "EW Universe",
                "description": "Equal-weight all assets (benchmark)",
                "dates": eq_dates,
                "equity": [_safe_float(v) or 0.0 for v in ew_eq],
                "drawdown": [_safe_float(v) or 0.0 for v in build_drawdown(ew_eq)],
                "stats": build_stats(ew_rets, ew_eq),
            },
            "spy_bnh": {
                "label": "SPY Buy & Hold",
                "description": "100% SPY buy-and-hold (benchmark)",
                "dates": eq_dates,
                "equity": [_safe_float(v) or 0.0 for v in spy_eq],
                "drawdown": [_safe_float(v) or 0.0 for v in build_drawdown(spy_eq)],
                "stats": build_stats(spy_rets, spy_eq),
            },
        },
        "regime_history": {
            "dates": wf_dates,
            "regimes": ["Ensemble"] * len(wf_dates),
        },
        "yearly_returns": yearly,
        "allocation_templates": {},
        "assets": alloc_assets + ([cash_ticker] if has_cash else []),
        "holdings_history": {
            "dates": wf_dates,
            "holdings": [
                {k: _safe_float(v) or 0.0 for k, v in h.items()}
                for h in holdings_list
            ],
        },
        "cost_bps": cost_bps,
        # Ensemble-specific fields
        "ensemble_meta": {
            "total_regimes": len(regime_keys),
            "regime_keys": regime_keys,
            "horizon_months": horizon_months,
            "significance_threshold": ic_threshold,
            "warmup_months": warmup_months,
        },
        "current_weights": {k: _safe_float(v) or 0.0 for k, v in current_weights.items()},
        "regime_drivers": latest_drivers,
    }
