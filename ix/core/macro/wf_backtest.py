"""Walk-forward backtest engine for macro regime strategy.

Pure computation -- no Streamlit, no plotting. All indicator directions
are determined by empirical IC sign (no theory-based sign control).
"""

from __future__ import annotations

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


def _soft_score(pctile: float, low: float = 0.35, high: float = 0.65) -> float:
    """Soft regime scoring with neutral zone."""
    if pctile <= low:
        return 0.0
    elif pctile >= high:
        return 1.0
    return (pctile - low) / (high - low)


# ---------------------------------------------------------------------------
# Walk-Forward Backtest Engines
# ---------------------------------------------------------------------------

def _wf_category_backtest(
    category_indicators: Dict[str, pd.Series],
    fwd_ret: pd.Series,
    idx_ret: pd.Series,
    all_dates: pd.DatetimeIndex,
    lookback_weeks: int,
    top_n: int,
    corr_max: float,
    rebal_weeks: int,
    weight_method: str,
    # V3 optimized parameters
    weekly_prices: pd.Series | None = None,
    sma_window: int = 40,
    macro_trend_split: Tuple[float, float] = (1.0, 0.0),
    alloc_range: Tuple[float, float] = (0.10, 0.90),
    soft_zone: Tuple[float, float] = (0.35, 0.65),
    # Circuit breakers (disabled by default -- set thresholds to enable)
    vix_series: pd.Series | None = None,
    vix_threshold: float = 0.0,
    drawdown_threshold: float = 0.0,
    drawdown_lookback: int = 52,
) -> Tuple[Dict | None, list]:
    """Walk-forward backtest for a single category.

    All indicator directions determined by empirical IC sign.
    """
    min_start = lookback_weeks + 52
    if len(all_dates) < min_start + 52 or not category_indicators:
        return None, []

    macro_w, trend_w = macro_trend_split
    alloc_lo, alloc_hi = alloc_range
    soft_lo, soft_hi = soft_zone

    selection_history = []
    eq_weights = pd.Series(dtype=float, name="eq_weight")
    rebal_indices = list(range(min_start, len(all_dates), rebal_weeks))

    for rebal_idx in rebal_indices:
        t = all_dates[rebal_idx]
        w_start = max(0, rebal_idx - lookback_weeks)
        window_dates = all_dates[w_start:rebal_idx]
        if len(window_dates) < 104:
            continue

        ic_scores = {}
        for ind_name, ind_series in category_indicators.items():
            w_ind = ind_series.reindex(window_dates).dropna()
            w_fwd = fwd_ret.reindex(window_dates).dropna()
            overlap = pd.concat({"ind": w_ind, "ret": w_fwd}, axis=1).dropna()
            if len(overlap) < 52:
                continue
            try:
                ic_val, _ = sp_stats.spearmanr(overlap["ind"], overlap["ret"])
                if not np.isnan(ic_val):
                    ic_scores[ind_name] = ic_val
            except Exception:
                continue

        if len(ic_scores) < 2:
            continue

        ranked = sorted(ic_scores.items(), key=lambda x: abs(x[1]), reverse=True)
        selected = []
        for ind_name, ic_val in ranked:
            if not selected:
                selected.append((ind_name, ic_val))
                continue
            candidate = category_indicators[ind_name].reindex(window_dates).dropna()
            too_corr = False
            for sel_name, _ in selected:
                sel_s = category_indicators[sel_name].reindex(window_dates).dropna()
                ov = pd.concat({"a": candidate, "b": sel_s}, axis=1).dropna()
                if len(ov) >= 30 and abs(ov["a"].corr(ov["b"])) > corr_max:
                    too_corr = True
                    break
            if not too_corr:
                selected.append((ind_name, ic_val))
            if len(selected) >= top_n:
                break

        if not selected:
            continue

        # Direction from empirical IC sign only
        parts = {}
        for ind_name, ic_val in selected:
            direction = np.sign(ic_val)
            parts[ind_name] = category_indicators[ind_name] * direction

        comp_df = pd.DataFrame(parts).loc[:t].dropna()
        if comp_df.empty:
            continue
        composite = comp_df.mean(axis=1)
        if composite.empty or len(composite) < 52:
            continue

        trail = composite.iloc[-lookback_weeks:]
        if len(trail) < 52:
            continue
        pctile = sp_stats.percentileofscore(trail.iloc[:-1].values, trail.iloc[-1]) / 100.0
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
            "selected": [n for n, _ in selected],
            "ics": {n: ic for n, ic in selected},
            "eq_weight": eq_wt,
            "n_candidates": len(ic_scores),
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
    top_n: int,
    corr_max: float,
    rebal_weeks: int,
    weight_method: str,
) -> Tuple[Dict | None, list]:
    """Walk-forward Regime backtest: Growth x Inflation = 4 quadrants."""
    min_start = lookback_weeks + 52
    if len(all_dates) < min_start + 52:
        return None, []

    def _build_signal(indicators, window_dates, t):
        ic_scores = {}
        for ind_name, ind_series in indicators.items():
            w_ind = ind_series.reindex(window_dates).dropna()
            w_fwd = fwd_ret.reindex(window_dates).dropna()
            ov = pd.concat({"ind": w_ind, "ret": w_fwd}, axis=1).dropna()
            if len(ov) < 52:
                continue
            try:
                ic_val, _ = sp_stats.spearmanr(ov["ind"], ov["ret"])
                if not np.isnan(ic_val):
                    ic_scores[ind_name] = ic_val
            except Exception:
                continue
        if len(ic_scores) < 2:
            return None, []
        ranked = sorted(ic_scores.items(), key=lambda x: abs(x[1]), reverse=True)
        selected = []
        for ind_name, ic_val in ranked:
            if not selected:
                selected.append((ind_name, ic_val))
                continue
            cand = indicators[ind_name].reindex(window_dates).dropna()
            too_corr = False
            for sn, _ in selected:
                ss = indicators[sn].reindex(window_dates).dropna()
                ov2 = pd.concat({"a": cand, "b": ss}, axis=1).dropna()
                if len(ov2) >= 30 and abs(ov2["a"].corr(ov2["b"])) > corr_max:
                    too_corr = True
                    break
            if not too_corr:
                selected.append((ind_name, ic_val))
            if len(selected) >= top_n:
                break
        if not selected:
            return None, []
        parts = {}
        wts_local = {}
        for n, ic in selected:
            direction = np.sign(ic)
            parts[n] = indicators[n] * direction
            wts_local[n] = abs(ic) if weight_method == "IC-Weighted" else 1.0
        comp_df = pd.DataFrame(parts).loc[:t].dropna()
        if comp_df.empty:
            return None, selected
        tw = sum(wts_local.values())
        if tw == 0:
            return None, selected
        sig = sum(comp_df[k] * (wts_local[k] / tw) for k in wts_local if k in comp_df.columns)
        return sig, [(n, ic) for n, ic in selected]

    eq_weights = pd.Series(dtype=float, name="eq_weight")
    selection_history = []
    rebal_indices = list(range(min_start, len(all_dates), rebal_weeks))

    for rebal_idx in rebal_indices:
        t = all_dates[rebal_idx]
        w_start = max(0, rebal_idx - lookback_weeks)
        window_dates = all_dates[w_start:rebal_idx]
        if len(window_dates) < 104:
            continue

        g_sig, g_sel = _build_signal(growth_indicators, window_dates, t)
        i_sig, i_sel = _build_signal(inflation_indicators, window_dates, t)

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

        g_up = g_pctile > 0.50
        # Inflation composite direction is empirical IC sign, so high
        # pctile = bullish composite. Invert so i_up means rising inflation.
        i_up = i_pctile < 0.50

        if g_up and not i_up:
            regime = "Goldilocks"
        elif g_up and i_up:
            regime = "Reflation"
        elif not g_up and i_up:
            regime = "Stagflation"
        else:
            regime = "Deflation"

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
# Full pipeline: load, z-score, run 5 backtests
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


def load_data_for_index(index_name: str) -> Dict:
    """Pre-load price + indicator data for an index.

    Returns a dict that can be passed as ``preloaded_data`` to
    ``run_full_wf_pipeline`` to avoid redundant DB calls when
    running multiple backtests for the same index.
    """
    prices = load_index(index_name)
    if prices.empty:
        return {"error": f"Could not load {index_name}"}

    indicators = load_all_indicators(("Growth", "Inflation", "Liquidity", "Tactical"))

    from ix.core.macro.taxonomy import get_eligible_factors
    eligible = get_eligible_factors(index_name)
    indicators = {k: v for k, v in indicators.items() if k in eligible}

    return {"prices": prices, "indicators": indicators, "index_name": index_name}


def run_full_wf_pipeline(
    index_name: str,
    lookback_years: int = 5,
    top_n: int = 10,
    corr_max: float = 0.70,
    rebal_weeks: int = 13,
    horizon_key: str = "3m",
    weight_method: str = "Equal-Weighted",
    zscore_window: int = 260,
    # V3 optimized parameters
    optimized: bool = False,
    sma_window: int = 40,
    macro_trend_split: Tuple[float, float] = (1.0, 0.0),
    alloc_range: Tuple[float, float] = (0.10, 0.90),
    soft_zone: Tuple[float, float] = (0.35, 0.65),
    blend_weights: Dict[str, float] | None = None,
    # V4 improvements
    use_category_horizons: bool = False,
    apply_publication_lags: bool = False,
    vix_threshold: float = 0.0,
    drawdown_threshold: float = 0.0,
    benchmark_weight: float = 0.50,
    txcost_bps: float = 0,
    # Pre-loaded data (avoids redundant DB calls in batch runs)
    preloaded_data: Dict | None = None,
) -> Dict:
    """Complete walk-forward pipeline.

    All indicator directions determined by empirical IC sign.
    When optimized=True, uses trend overlay, soft scoring, blended
    4-category signal, circuit breakers.

    Pass ``preloaded_data`` (from ``load_data_for_index``) to skip
    the expensive indicator loading step.
    """
    if preloaded_data and "error" not in preloaded_data:
        prices = preloaded_data["prices"]
        indicators = dict(preloaded_data["indicators"])
    else:
        prices = load_index(index_name)
        if prices.empty:
            return {"error": f"Could not load {index_name}"}

        indicators = load_all_indicators(("Growth", "Inflation", "Liquidity", "Tactical"))

        from ix.core.macro.taxonomy import get_eligible_factors
        eligible = get_eligible_factors(index_name)
        indicators = {k: v for k, v in indicators.items() if k in eligible}

    freq = "W-WED"
    weekly = resample_to_freq(prices, freq)
    idx_ret = weekly.pct_change().dropna()

    # Default forward returns (used unless per-category horizons override)
    fwd_periods = HORIZON_MAP[horizon_key]
    fwd_ret = compute_forward_returns(weekly, fwd_periods)

    # Pre-compute per-category forward returns if enabled
    cat_fwd_rets = {}
    if use_category_horizons:
        for cat_name, periods in CATEGORY_HORIZONS.items():
            cat_fwd_rets[cat_name] = compute_forward_returns(weekly, periods)

    # Load VIX for circuit breaker
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

    # Z-score all indicators at weekly freq (with optional publication lag)
    ind_z = {}
    ind_cats = {}
    ind_meta = {}  # name -> (category, invert) -- kept for metadata/serialization
    for name, (raw, cat, desc, inv) in indicators.items():
        resampled = resample_to_freq(raw, freq)
        if resampled.empty or len(resampled) < 52:
            continue
        # Apply publication lag: shift data forward to simulate delayed release
        if apply_publication_lags:
            lag = PUBLICATION_LAGS.get(name, 0)
            if lag > 0:
                resampled = resampled.shift(lag)
        z = rolling_zscore(resampled, zscore_window)
        if z.empty or len(z) < 52:
            continue
        ind_z[name] = z
        ind_cats[name] = cat
        ind_meta[name] = (cat, inv)

    cat_pools = {"Growth": {}, "Inflation": {}, "Liquidity": {}, "Tactical": {}}
    for name, z_series in ind_z.items():
        cat = ind_cats.get(name)
        if cat in cat_pools:
            cat_pools[cat][name] = z_series

    all_dates = idx_ret.index
    lookback_weeks = lookback_years * 52

    # V3 extra args for optimized mode
    v3_kwargs = {}
    if optimized:
        v3_kwargs = dict(
            weekly_prices=weekly,
            sma_window=sma_window,
            macro_trend_split=macro_trend_split,
            alloc_range=alloc_range,
            soft_zone=soft_zone,
        )
        # Circuit breakers
        if vix_threshold > 0 and vix_weekly is not None:
            v3_kwargs["vix_series"] = vix_weekly
            v3_kwargs["vix_threshold"] = vix_threshold
        if drawdown_threshold < 0:
            v3_kwargs["drawdown_threshold"] = drawdown_threshold

    wf_results = {}
    wf_histories = {}
    cat_wt_series = {}  # for blended backtest

    for cat_name in ["Growth", "Inflation", "Liquidity", "Tactical"]:
        pool = cat_pools.get(cat_name, {})
        if len(pool) < 3:
            continue
        # Use per-category forward returns if enabled
        cat_fwd = cat_fwd_rets.get(cat_name, fwd_ret) if use_category_horizons else fwd_ret
        res, hist = _wf_category_backtest(
            pool, cat_fwd, idx_ret, all_dates,
            lookback_weeks, top_n, corr_max, rebal_weeks, weight_method,
            **v3_kwargs,
        )
        if res is not None:
            wf_results[cat_name] = res
            wf_histories[cat_name] = hist
            # Extract weight series for blending
            if hist:
                ws = pd.Series(dtype=float)
                for h in hist:
                    ws[h["date"]] = h["eq_weight"]
                ws = ws.reindex(idx_ret.index).ffill()
                cat_wt_series[cat_name] = ws

    # Blended 4-category signal (optimized mode) -- equal-weight by default
    if optimized and cat_wt_series:
        bw = blend_weights  # None = equal-weight in _blended_backtest
        blended_res = _blended_backtest(cat_wt_series, idx_ret, bw, alloc_range,
                                        benchmark_weight=benchmark_weight,
                                        txcost_bps=txcost_bps)
        if blended_res is not None:
            wf_results["Blended"] = blended_res
            wf_histories["Blended"] = []  # no per-rebal history for blended

    # Regime backtest (Growth x Inflation quadrant)
    if len(cat_pools["Growth"]) >= 3 and len(cat_pools["Inflation"]) >= 3:
        res, hist = _wf_regime_backtest(
            cat_pools["Growth"], cat_pools["Inflation"],
            fwd_ret, idx_ret, all_dates,
            lookback_weeks, top_n, corr_max, rebal_weeks, weight_method,
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
        "optimized": optimized,
        "benchmark_weight": benchmark_weight,
    }
