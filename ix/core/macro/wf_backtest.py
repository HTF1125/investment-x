"""Walk-forward backtest engine for macro regime strategy.

Pure computation -- no Streamlit, no plotting.

Indicator z-scores are **pre-flipped** at computation time so that
high z always means "bullish for equities".  The flip rule per
indicator is ``inv XOR (category in CATEGORY_BEARISH)`` — combining
the per-indicator ``invert`` flag from the taxonomy with the
category-level direction.  This eliminates the need for category-level
percentile inversion at allocation time.

Composites are equal-weight by default.  IC-weighted mode is available
via ``composite_mode="ic_weighted"``.

Indicators are drawn from a curated ~22-indicator universe
(DEFAULT_UNIVERSE) to avoid multiple testing issues.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from scipy import stats as sp_stats

from ix.core.macro.strategy_utils import (
    INDEX_MAP,
    HORIZON_MAP,
    CATEGORY_HORIZONS,
    PUBLICATION_LAGS,
    load_index,
    load_all_indicators,
    resample_to_freq,
    compute_forward_returns,
    rolling_zscore,
)

# ---------------------------------------------------------------------------
# Regime allocation constants
# ---------------------------------------------------------------------------

REGIME_ALLOC = {
    "Goldilocks": 0.90,
    "Reflation": 0.70,
    "Deflation": 0.30,
    "Stagflation": 0.10,
}

# Categories where a *high* composite is bearish for equity returns.
# Their percentile is inverted (1 − p) before allocation scoring.
CATEGORY_BEARISH = {"Inflation"}

# ---------------------------------------------------------------------------
# Default indicator universe (~22 theory-grounded indicators)
# ---------------------------------------------------------------------------

DEFAULT_UNIVERSE = {
    "Growth": [
        "ISM New Orders", "CESI Breadth", "OECD CLI World",
        "Global Trade Composite", "SPX Revision Ratio",
        "Copper/Gold", "Initial Claims",
    ],
    "Inflation": [
        "10Y Breakeven", "CRB Index", "Inflation Surprise",
        "ISM Prices Paid", "CPI 3M Annualized",
    ],
    "Liquidity": [
        "Fed Net Liquidity", "FCI US", "US 3M10Y",
        "HY Spread", "US 2s10s",
    ],
    "Tactical": [
        "VIX", "Put/Call Z-Score", "HY/IG Ratio",
        "US Sector Breadth", "CFTC SPX Net",
    ],
}


def _soft_score(pctile: float, low: float = 0.35, high: float = 0.65) -> float:
    """Soft regime scoring with neutral zone."""
    if pctile <= low:
        return 0.0
    elif pctile >= high:
        return 1.0
    return (pctile - low) / (high - low)


def _compute_ics(
    ind_df: pd.DataFrame,
    fwd_series: pd.Series,
    ind_names: list[str],
    min_obs: int = 52,
) -> list[tuple[str, float]]:
    """Compute Spearman IC for each indicator against forward returns.

    Returns list of (name, ic) for all indicators with enough data.
    """
    results = []
    for ind_name in ind_names:
        ind_vals = ind_df[ind_name].dropna()
        fwd_valid = fwd_series.dropna()
        common = ind_vals.index.intersection(fwd_valid.index)
        if len(common) < min_obs:
            continue
        ic, _ = sp_stats.spearmanr(ind_vals.loc[common], fwd_valid.loc[common])
        if not np.isnan(ic):
            results.append((ind_name, ic))
    return results


def _build_composite(
    ind_df: pd.DataFrame,
    ics: list[tuple[str, float]],
    mode: str = "ic_weighted",
) -> pd.Series | None:
    """Build a composite signal from indicator z-scores.

    Modes
    -----
    equal_weight : simple mean of all columns
    ic_weighted  : weight each column by |IC|, normalize (default)
    """
    if ind_df.empty:
        return None
    ic_dict = dict(ics)
    available = [c for c in ind_df.columns if c in ic_dict]
    if not available:
        available = list(ind_df.columns)

    if mode == "ic_weighted" and available:
        weights = {n: abs(ic_dict.get(n, 0.01)) for n in available}
        total_w = sum(weights.values())
        if total_w == 0:
            return ind_df[available].mean(axis=1, skipna=True).dropna()
        composite = sum(ind_df[n] * (w / total_w) for n, w in weights.items())
    else:
        # equal_weight fallback
        composite = ind_df[available].mean(axis=1, skipna=True)

    return composite.dropna() if composite is not None else None


# ---------------------------------------------------------------------------
# Walk-Forward Backtest Engines
# ---------------------------------------------------------------------------

def _wf_category_backtest(
    category_indicators: Dict[str, pd.Series],
    fwd_ret: pd.Series,
    idx_ret: pd.Series,
    all_dates: pd.DatetimeIndex,
    lookback_weeks: int,
    rebal_weeks: int,
    # Trend overlay
    weekly_prices: pd.Series | None = None,
    sma_window: int = 30,
    macro_trend_split: Tuple[float, float] = (0.6, 0.4),
    # Allocation
    alloc_range: Tuple[float, float] = (0.10, 0.90),
    soft_zone: Tuple[float, float] = (0.25, 0.75),
    # Circuit breakers (disabled by default -- set thresholds to enable)
    vix_series: pd.Series | None = None,
    vix_threshold: float = 0.0,
    drawdown_threshold: float = 0.0,
    drawdown_lookback: int = 52,
    # Composite construction
    composite_mode: str = "equal_weight",
) -> Tuple[Dict | None, list]:
    """Walk-forward backtest for a single category.

    Indicators are expected to be pre-flipped so that high z = bullish.
    Composites are equal-weight by default (``composite_mode``).
    """
    min_start = lookback_weeks + 52
    if len(all_dates) < min_start + 52 or not category_indicators:
        return None, []

    macro_w, trend_w = macro_trend_split
    alloc_lo, alloc_hi = alloc_range
    soft_lo, soft_hi = soft_zone

    # Pre-build full indicator DataFrame for fast window slicing
    ind_names = list(category_indicators.keys())
    ind_df_full = pd.DataFrame(
        {n: category_indicators[n] for n in ind_names}
    ).reindex(all_dates)
    fwd_full = fwd_ret.reindex(all_dates)

    selection_history = []
    eq_weights = pd.Series(dtype=float, name="eq_weight")
    rebal_indices = list(range(min_start, len(all_dates), rebal_weeks))

    for rebal_idx in rebal_indices:
        t = all_dates[rebal_idx]
        w_start = max(0, rebal_idx - lookback_weeks)
        window_dates = all_dates[w_start:rebal_idx]
        if len(window_dates) < 104:
            continue

        window_df = ind_df_full.loc[window_dates]
        fwd_window = fwd_full.loc[window_dates]

        # Compute ICs for selection history metadata
        ics = _compute_ics(window_df, fwd_window, ind_names)
        if not ics:
            continue

        # Build composite (IC-weighted by default, pre-flipped z-scores)
        comp_df = pd.DataFrame(
            {n: category_indicators[n] for n in ind_names}
        ).loc[:t]
        if comp_df.dropna(how="all").empty:
            continue
        composite = _build_composite(comp_df, ics, mode=composite_mode)
        if composite is None or len(composite) < 52:
            continue

        trail = composite.iloc[-lookback_weeks:]
        if len(trail) < 52:
            continue
        pctile = sp_stats.percentileofscore(trail.iloc[:-1].values, trail.iloc[-1]) / 100.0
        # No bearish inversion needed — z-scores are pre-flipped
        macro_score = _soft_score(max(0.0, min(1.0, pctile)), soft_lo, soft_hi)

        # Trend overlay
        trend_score = 0.5
        if weekly_prices is not None and trend_w > 0:
            px_at_t = weekly_prices.reindex(weekly_prices.index[weekly_prices.index <= t])
            if len(px_at_t) >= sma_window:
                trend_score = 1.0 if px_at_t.iloc[-1] > px_at_t.iloc[-sma_window:].mean() else 0.0

        combined = macro_w * macro_score + trend_w * trend_score
        eq_wt = alloc_lo + combined * (alloc_hi - alloc_lo)
        eq_wt = max(alloc_lo, min(alloc_hi, eq_wt))

        # --- Circuit breakers (override allocation to risk-off) ---
        circuit_breaker = None

        # VIX circuit breaker: force risk-off when VIX > threshold
        if vix_series is not None and vix_threshold > 0:
            vix_at_t = vix_series.reindex(vix_series.index[vix_series.index <= t])
            if len(vix_at_t) > 0 and vix_at_t.iloc[-1] > vix_threshold:
                eq_wt = alloc_lo
                circuit_breaker = "vix"

        # Drawdown override: force risk-off when price drops >threshold from 52w high
        if weekly_prices is not None and drawdown_threshold < 0:
            px_at_t = weekly_prices.reindex(weekly_prices.index[weekly_prices.index <= t])
            if len(px_at_t) >= drawdown_lookback:
                high_52w = px_at_t.iloc[-drawdown_lookback:].max()
                current_dd = px_at_t.iloc[-1] / high_52w - 1.0
                if current_dd < drawdown_threshold:
                    eq_wt = alloc_lo
                    circuit_breaker = "drawdown"

        next_rebal = min(rebal_idx + rebal_weeks, len(all_dates))
        for d in all_dates[rebal_idx:next_rebal]:
            eq_weights[d] = eq_wt

        selection_history.append({
            "date": t,
            "selected": [n for n, _ in ics],
            "ics": {n: ic for n, ic in ics},
            "eq_weight": eq_wt,
            "n_candidates": len(ind_names),
            "circuit_breaker": circuit_breaker,
        })

    if not selection_history or eq_weights.empty:
        return None, selection_history

    return _compute_bt_stats(idx_ret, eq_weights), selection_history


def _wf_regime_backtest(
    growth_indicators: Dict[str, pd.Series],
    inflation_indicators: Dict[str, pd.Series],
    fwd_ret: pd.Series,
    idx_ret: pd.Series,
    all_dates: pd.DatetimeIndex,
    lookback_weeks: int,
    rebal_weeks: int,
    inflation_fwd_ret: pd.Series | None = None,
) -> Tuple[Dict | None, list]:
    """Walk-forward Regime backtest: Growth x Inflation = 4 quadrants.

    When *inflation_fwd_ret* is provided, inflation indicators are
    evaluated against that horizon instead of the default *fwd_ret*.
    """
    min_start = lookback_weeks + 52
    if len(all_dates) < min_start + 52:
        return None, []

    # Pre-build full DataFrames for fast window slicing
    g_names = list(growth_indicators.keys())
    i_names = list(inflation_indicators.keys())
    g_df_full = pd.DataFrame({n: growth_indicators[n] for n in g_names}).reindex(all_dates)
    i_df_full = pd.DataFrame({n: inflation_indicators[n] for n in i_names}).reindex(all_dates)
    fwd_full = fwd_ret.reindex(all_dates)
    i_fwd_full = (inflation_fwd_ret if inflation_fwd_ret is not None else fwd_ret).reindex(all_dates)

    def _build_signal(ind_df, ind_names, window_dates, t, fwd_window):
        window_df = ind_df.loc[window_dates]
        fwd_w = fwd_window.loc[window_dates]

        ics = _compute_ics(window_df, fwd_w, ind_names)
        if not ics:
            return None, []

        # IC-weighted composite (z-scores are pre-flipped)
        comp_df = pd.DataFrame({n: ind_df[n] for n in ind_names}).loc[:t]
        if comp_df.dropna(how="all").empty:
            return None, ics
        sig = _build_composite(comp_df, ics, mode="ic_weighted")
        if sig is None:
            return None, ics
        return sig, ics

    eq_weights = pd.Series(dtype=float, name="eq_weight")
    selection_history = []
    rebal_indices = list(range(min_start, len(all_dates), rebal_weeks))

    for rebal_idx in rebal_indices:
        t = all_dates[rebal_idx]
        w_start = max(0, rebal_idx - lookback_weeks)
        window_dates = all_dates[w_start:rebal_idx]
        if len(window_dates) < 104:
            continue

        g_sig, g_sel = _build_signal(g_df_full, g_names, window_dates, t, fwd_full)
        i_sig, i_sel = _build_signal(i_df_full, i_names, window_dates, t, i_fwd_full)

        if g_sig is None or i_sig is None:
            continue
        if len(g_sig) < 52 or len(i_sig) < 52:
            continue

        g_trail = g_sig.iloc[-lookback_weeks:]
        i_trail = i_sig.iloc[-lookback_weeks:]
        if len(g_trail) < 52 or len(i_trail) < 52:
            continue

        g_pctile = sp_stats.percentileofscore(g_trail.iloc[:-1].values, g_trail.iloc[-1]) / 100.0
        i_pctile = sp_stats.percentileofscore(i_trail.iloc[:-1].values, i_trail.iloc[-1]) / 100.0

        # Z-scores are pre-flipped: high = bullish for equities.
        # Growth: high = strong growth (bullish).
        # Inflation: high = LOW inflation (bullish, since flipped).
        # So i_up means "inflation is equity-friendly" = low inflation.
        g_up = g_pctile > 0.50
        i_bullish = i_pctile > 0.50  # high = low inflation (pre-flipped)

        if g_up and i_bullish:
            regime = "Goldilocks"       # strong growth + low inflation
        elif g_up and not i_bullish:
            regime = "Reflation"        # strong growth + high inflation
        elif not g_up and not i_bullish:
            regime = "Stagflation"      # weak growth + high inflation
        else:
            regime = "Deflation"        # weak growth + low inflation

        eq_wt = REGIME_ALLOC[regime]

        next_rebal = min(rebal_idx + rebal_weeks, len(all_dates))
        for d in all_dates[rebal_idx:next_rebal]:
            eq_weights[d] = eq_wt

        selection_history.append({
            "date": t,
            "regime": regime,
            "growth_pctile": g_pctile,
            "inflation_pctile": i_pctile,
            "eq_weight": eq_wt,
            "growth_selected": [n for n, _ in g_sel] if g_sel else [],
            "inflation_selected": [n for n, _ in i_sel] if i_sel else [],
            "selected": ([n for n, _ in g_sel] if g_sel else [])
                      + ([n for n, _ in i_sel] if i_sel else []),
            "ics": dict(g_sel or []) | dict(i_sel or []),
            "n_candidates": 0,
        })

    if not selection_history or eq_weights.empty:
        return None, selection_history

    return _compute_bt_stats(idx_ret, eq_weights), selection_history


def _compute_bt_stats(
    idx_ret: pd.Series,
    eq_weights: pd.Series,
    leverage_rate: float = 0.10,
    benchmark_weight: float = 0.50,
    txcost_bps: float = 0,
) -> Dict | None:
    """Compute backtest performance from index returns and equity weight series.

    Benchmark is a static allocation (default 50% equity / 50% cash).
    When equity weight > 1.0 (leverage), the strategy pays an annual interest
    rate on the borrowed portion.  Transaction costs are deducted on each
    weight change proportional to turnover x txcost_bps.
    """
    bt_df = pd.concat({"idx_ret": idx_ret, "eq_weight": eq_weights}, axis=1).dropna()
    if len(bt_df) < 52:
        return None

    # Leverage cost: weekly cost on the portion above 100%
    weekly_rate = leverage_rate / 52
    leverage_cost = bt_df["eq_weight"].clip(lower=1.0).sub(1.0) * weekly_rate

    # Transaction cost: proportional to abs weight change at rebalances
    txcost = pd.Series(0.0, index=bt_df.index)
    if txcost_bps > 0:
        weight_change = bt_df["eq_weight"].diff().abs().fillna(0)
        txcost = weight_change * (txcost_bps / 10_000)

    bt_df["strategy_ret"] = bt_df["eq_weight"] * bt_df["idx_ret"] - leverage_cost - txcost
    bt_df["benchmark_ret"] = benchmark_weight * bt_df["idx_ret"]
    bt_df["strategy_cum"] = (1 + bt_df["strategy_ret"]).cumprod()
    bt_df["benchmark_cum"] = (1 + bt_df["benchmark_ret"]).cumprod()
    bt_df["idx_cum"] = (1 + bt_df["idx_ret"]).cumprod()

    ann = 52
    ny = len(bt_df) / ann
    sa = bt_df["strategy_cum"].iloc[-1] ** (1 / ny) - 1
    ba = bt_df["benchmark_cum"].iloc[-1] ** (1 / ny) - 1
    sv = bt_df["strategy_ret"].std() * np.sqrt(ann)
    bv = bt_df["benchmark_ret"].std() * np.sqrt(ann)
    excess = bt_df["strategy_ret"] - bt_df["benchmark_ret"]
    te = excess.std() * np.sqrt(ann)

    def _mdd(c):
        return (c / c.expanding().max() - 1).min()

    return {
        "bt_df": bt_df,
        "strat_ann_ret": sa, "bench_ann_ret": ba,
        "strat_vol": sv, "bench_vol": bv,
        "strat_sharpe": sa / sv if sv > 0 else 0,
        "bench_sharpe": ba / bv if bv > 0 else 0,
        "strat_mdd": _mdd(bt_df["strategy_cum"]),
        "bench_mdd": _mdd(bt_df["benchmark_cum"]),
        "te": te,
        "ir": (sa - ba) / te if te > 0 else 0,
        "bt_hit": (excess > 0).mean(),
        "excess": excess,
        "benchmark_weight": benchmark_weight,
    }


# ---------------------------------------------------------------------------
# Full pipeline: load, z-score, run backtests
# ---------------------------------------------------------------------------

def _blended_backtest(
    cat_weight_series: Dict[str, pd.Series],
    idx_ret: pd.Series,
    blend_weights: Dict[str, float] | None = None,
    alloc_range: Tuple[float, float] = (0.0, 1.0),
    benchmark_weight: float = 0.50,
    txcost_bps: float = 0,
) -> Dict | None:
    """Blend multiple category weight series into one and compute stats."""
    if not cat_weight_series:
        return None
    wdf = pd.DataFrame(cat_weight_series).dropna(how="all")
    if wdf.empty:
        return None

    if blend_weights:
        tw = sum(blend_weights.get(c, 0) for c in wdf.columns)
        if tw > 0:
            blended = sum(wdf[c] * (blend_weights.get(c, 0) / tw) for c in wdf.columns)
        else:
            blended = wdf.mean(axis=1)
    else:
        blended = wdf.mean(axis=1)

    alo, ahi = alloc_range
    blended = blended.clip(alo, ahi)
    return _compute_bt_stats(idx_ret, blended, benchmark_weight=benchmark_weight,
                             txcost_bps=txcost_bps)


def load_universe(path: str | None = None) -> Dict[str, list[str]]:
    """Load indicator universe from JSON, fallback to DEFAULT_UNIVERSE."""
    if path:
        p = Path(path)
        if p.is_file():
            data = json.loads(p.read_text())
            if "universe" in data:
                return data["universe"]
    return dict(DEFAULT_UNIVERSE)


def load_data_for_index(
    index_name: str,
    universe: Dict[str, list[str]] | None = None,
) -> Dict:
    """Pre-load price + indicator data for an index.

    When *universe* is provided, loads only those indicators (universal
    set, no geo-eligibility filtering).  Otherwise falls back to loading
    all indicators with geo-filtering.
    """
    prices = load_index(index_name)
    if prices.empty:
        return {"error": f"Could not load {index_name}"}

    indicators = load_all_indicators(("Growth", "Inflation", "Liquidity", "Tactical"))

    if universe:
        universe_names = set()
        for names in universe.values():
            universe_names.update(names)
        indicators = {k: v for k, v in indicators.items() if k in universe_names}
    else:
        from ix.core.macro.taxonomy import get_eligible_factors
        eligible = get_eligible_factors(index_name)
        indicators = {k: v for k, v in indicators.items() if k in eligible}

    return {"prices": prices, "indicators": indicators, "index_name": index_name}


def run_full_wf_pipeline(
    index_name: str,
    lookback_years: int = 5,
    rebal_weeks: int = 13,
    horizon_key: str = "6m",
    zscore_window: int = 260,
    sma_window: int = 30,
    macro_trend_split: Tuple[float, float] = (0.6, 0.4),
    alloc_range: Tuple[float, float] = (0.10, 0.90),
    soft_zone: Tuple[float, float] = (0.25, 0.75),
    blend_weights: Dict[str, float] | None = None,
    use_category_horizons: bool = True,
    apply_publication_lags: bool = True,
    vix_threshold: float = 0.0,
    drawdown_threshold: float = 0.0,
    benchmark_weight: float = 0.50,
    txcost_bps: float = 10,
    universe: Dict[str, list[str]] | None = None,
    universe_path: str | None = None,
    preloaded_data: Dict | None = None,
    composite_mode: str = "equal_weight",
    **kwargs,
) -> Dict:
    """Complete walk-forward pipeline.

    Indicator z-scores are pre-flipped so high = bullish for equities.
    Composites are equal-weight by default.  Uses trend overlay, soft
    scoring, blended 4-category signal, and optional circuit breakers.

    When *universe* or *universe_path* is provided, loads only those
    indicators (no geo-eligibility filtering).

    Pass *preloaded_data* (from ``load_data_for_index``) to skip
    the expensive indicator loading step.
    """
    # Resolve universe
    effective_universe = universe
    if effective_universe is None and universe_path:
        effective_universe = load_universe(universe_path)

    if preloaded_data and "error" not in preloaded_data:
        prices = preloaded_data["prices"]
        indicators = dict(preloaded_data["indicators"])
    else:
        prices = load_index(index_name)
        if prices.empty:
            return {"error": f"Could not load {index_name}"}

        indicators = load_all_indicators(("Growth", "Inflation", "Liquidity", "Tactical"))

        if effective_universe:
            universe_names = set()
            for names in effective_universe.values():
                universe_names.update(names)
            indicators = {k: v for k, v in indicators.items() if k in universe_names}
        else:
            from ix.core.macro.taxonomy import get_eligible_factors
            eligible = get_eligible_factors(index_name)
            indicators = {k: v for k, v in indicators.items() if k in eligible}

    freq = "W-WED"
    weekly = resample_to_freq(prices, freq)
    idx_ret = weekly.pct_change().dropna()

    fwd_periods = HORIZON_MAP[horizon_key]
    fwd_ret = compute_forward_returns(weekly, fwd_periods)

    # Pre-compute per-category forward returns if enabled
    cat_fwd_rets = {}
    if use_category_horizons:
        for cat_name, periods in CATEGORY_HORIZONS.items():
            cat_fwd_rets[cat_name] = compute_forward_returns(weekly, periods)

    # Load VIX for circuit breaker (only if enabled)
    vix_weekly = None
    if vix_threshold > 0:
        try:
            from ix.db.query import Series as DBSeries
            vix_raw = DBSeries("VIX Index:PX_LAST")
            if vix_raw.empty:
                import yfinance as yf
                vix_raw = yf.download("^VIX", period="max", auto_adjust=True)["Close"].squeeze()
            vix_weekly = resample_to_freq(vix_raw, freq)
        except Exception:
            vix_weekly = None

    # Z-score all indicators at weekly freq (with optional publication lag).
    # Pre-flip so high z = bullish for equities:
    #   flip = inv XOR (category in CATEGORY_BEARISH)
    ind_z = {}
    ind_cats = {}
    ind_meta = {}  # name -> (category, invert)
    for name, (raw, cat, desc, inv) in indicators.items():
        resampled = resample_to_freq(raw, freq)
        if resampled.empty or len(resampled) < 52:
            continue
        if apply_publication_lags:
            lag = PUBLICATION_LAGS.get(name, 0)
            if lag > 0:
                resampled = resampled.shift(lag)
        z = rolling_zscore(resampled, zscore_window)
        if z.empty or len(z) < 52:
            continue
        # Pre-flip: high z = bullish for equities after this
        bearish_cat = cat in CATEGORY_BEARISH
        if inv != bearish_cat:
            z = -z
        ind_z[name] = z
        ind_cats[name] = cat
        ind_meta[name] = (cat, inv)

    # Build category pools — respect universe category assignments if provided
    cat_pools = {"Growth": {}, "Inflation": {}, "Liquidity": {}, "Tactical": {}}
    if effective_universe:
        for cat_name, ind_list in effective_universe.items():
            if cat_name not in cat_pools:
                continue
            for name in ind_list:
                if name in ind_z:
                    cat_pools[cat_name][name] = ind_z[name]
    else:
        for name, z_series in ind_z.items():
            cat = ind_cats.get(name)
            if cat in cat_pools:
                cat_pools[cat][name] = z_series

    all_dates = idx_ret.index
    lookback_weeks = lookback_years * 52

    wf_results = {}
    wf_histories = {}
    cat_wt_series = {}

    for cat_name in ["Growth", "Inflation", "Liquidity", "Tactical"]:
        pool = cat_pools.get(cat_name, {})
        if len(pool) < 3:
            continue
        cat_fwd = cat_fwd_rets.get(cat_name, fwd_ret) if use_category_horizons else fwd_ret
        res, hist = _wf_category_backtest(
            pool, cat_fwd, idx_ret, all_dates,
            lookback_weeks, rebal_weeks,
            weekly_prices=weekly,
            sma_window=sma_window,
            macro_trend_split=macro_trend_split,
            alloc_range=alloc_range,
            soft_zone=soft_zone,
            vix_series=vix_weekly,
            vix_threshold=vix_threshold,
            drawdown_threshold=drawdown_threshold,
            composite_mode=composite_mode,
        )
        if res is not None:
            wf_results[cat_name] = res
            wf_histories[cat_name] = hist
            if hist:
                ws = pd.Series(dtype=float)
                for h in hist:
                    ws[h["date"]] = h["eq_weight"]
                ws = ws.reindex(idx_ret.index).ffill()
                cat_wt_series[cat_name] = ws

    # Blended 4-category signal (equal-weight by default)
    if cat_wt_series:
        blended_res = _blended_backtest(cat_wt_series, idx_ret, blend_weights, alloc_range,
                                        benchmark_weight=benchmark_weight,
                                        txcost_bps=txcost_bps)
        if blended_res is not None:
            wf_results["Blended"] = blended_res
            wf_histories["Blended"] = []

    # Regime backtest (Growth x Inflation quadrant)
    inflation_fwd = cat_fwd_rets.get("Inflation") if use_category_horizons else None
    if len(cat_pools["Growth"]) >= 3 and len(cat_pools["Inflation"]) >= 3:
        res, hist = _wf_regime_backtest(
            cat_pools["Growth"], cat_pools["Inflation"],
            fwd_ret, idx_ret, all_dates,
            lookback_weeks, rebal_weeks,
            inflation_fwd_ret=inflation_fwd,
        )
        if res is not None:
            wf_results["Regime"] = res
            wf_histories["Regime"] = hist

    return {
        "wf_results": wf_results,
        "wf_histories": wf_histories,
        "weekly_prices": weekly,
        "idx_ret": idx_ret,
        "fwd_ret": fwd_ret,
        "ind_z": ind_z,
        "ind_cats": ind_cats,
        "ind_meta": ind_meta,
        "cat_pools": cat_pools,
        "n_indicators": len(ind_z),
        "n_total": len(indicators),
        "cat_counts": {c: len(p) for c, p in cat_pools.items()},
        "index_name": index_name,
        "benchmark_weight": benchmark_weight,
    }
