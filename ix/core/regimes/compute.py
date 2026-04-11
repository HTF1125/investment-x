"""Generic regime compute + serialization.

``RegimeComputer`` is the base pipeline that runs any :class:`Regime`
subclass and serializes the result into the shape expected by the
``regime_snapshot`` DB table.

All public regimes are 1D and use this generic pipeline. Multi-axis
composites are generated on demand by ``ix.core.regimes.compose``,
not by computer subclasses.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from ix.db.conn import Session
from ix.db.models import RegimeSnapshot, regime_fingerprint

from .base import Regime
from .registry import RegimeRegistration

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Default asset universes by regime family
# ─────────────────────────────────────────────────────────────────────

#: Broad macro universe — default for regimes that don't declare their own.
DEFAULT_ASSET_TICKERS: dict[str, str] = {
    "SPY": "SPY US EQUITY:PX_LAST",   # US large cap
    "IWM": "IWM US EQUITY:PX_LAST",   # US small cap
    "EFA": "EFA US EQUITY:PX_LAST",   # Developed ex-US
    "EEM": "EEM US EQUITY:PX_LAST",   # Emerging markets
    "TLT": "TLT US EQUITY:PX_LAST",   # Long Treasuries
    "IEF": "IEF US EQUITY:PX_LAST",   # Intermediate Treasuries
    "TIP": "TIP US EQUITY:PX_LAST",   # TIPS
    "HYG": "HYG US EQUITY:PX_LAST",   # High yield credit
    "GLD": "GLD US EQUITY:PX_LAST",   # Gold
    "DBC": "DBC US EQUITY:PX_LAST",   # Broad commodities
    "BIL": "BIL US EQUITY:PX_LAST",   # T-bills (risk-free proxy)
}

#: Equity-only universe — regional equity rotation + cash fallback.
EQUITY_ASSET_TICKERS: dict[str, str] = {
    "SPY": "SPY US EQUITY:PX_LAST",   # US large cap
    "IWM": "IWM US EQUITY:PX_LAST",   # US small cap
    "EFA": "EFA US EQUITY:PX_LAST",   # Developed ex-US
    "EEM": "EEM US EQUITY:PX_LAST",   # Emerging markets
    "BIL": "BIL US EQUITY:PX_LAST",   # T-bills (cash fallback)
}

#: Named universe presets for the ensemble endpoint.
UNIVERSE_PRESETS: dict[str, dict[str, str]] = {
    "broad": DEFAULT_ASSET_TICKERS,
    "equity": EQUITY_ASSET_TICKERS,
}


def _load_asset_prices(tickers: dict[str, str]) -> pd.DataFrame:
    """Load monthly price series for the given ticker universe.

    Args:
        tickers: ``{display_name: db_code}`` mapping.

    Returns:
        DataFrame indexed by month-end dates, columns = display names.
        Empty DataFrame if no tickers load successfully.
    """
    from ix.db.query import Series as DbSeries

    out: dict[str, pd.Series] = {}
    for display, code in tickers.items():
        try:
            s = DbSeries(code)
            if not s.empty:
                out[display] = s.resample("ME").last()
        except Exception as exc:
            log.warning("Asset price load failed for %s (%s): %s", display, code, exc)

    return pd.DataFrame(out) if out else pd.DataFrame()


def compute_signal_ic(
    signal: pd.Series,
    prices: pd.DataFrame,
    asset_cols: list[str],
    horizon_months: int,
    data_lag_months: int = 1,
    warmup_months: int = 120,
) -> dict[str, dict]:
    """Compute Spearman IC between a regime signal and each asset's forward return.

    IC = rank correlation between the regime's composite Z-score (lagged by
    ``data_lag_months`` to respect publication delay) and the asset's realised
    forward ``horizon_months``-month return.

    Args:
        signal: Regime composite Z-score series (monthly, same index as prices).
        prices: Asset price DataFrame (columns = display tickers).
        asset_cols: Which columns in *prices* to evaluate.
        horizon_months: Forward-return window in months.
        data_lag_months: Publication lag applied to the signal (default 1).
        warmup_months: Skip first N months (rolling z-score warmup).

    Returns:
        ``{ticker: {ic, ic_pvalue, n, horizon}}`` dict.  Empty dict if signal
        is unusable.
    """
    if signal.dropna().empty or len(signal) < warmup_months + 30:
        return {}

    # Lag signal to respect publication delay
    sig = signal.shift(data_lag_months)

    result: dict[str, dict] = {}
    for ticker in asset_cols:
        if ticker not in prices.columns:
            continue
        px = prices[ticker].dropna()
        if px.empty:
            continue

        # Forward H-month return
        fwd_ret = px.pct_change(horizon_months).shift(-horizon_months)

        # Align, skip warmup, drop NAs
        merged = pd.concat([sig.rename("signal"), fwd_ret.rename("fwd")], axis=1)
        merged = merged.iloc[warmup_months:]
        merged = merged.dropna()

        if len(merged) < 30:
            result[ticker] = {
                "ic": None, "ic_pvalue": None,
                "n": len(merged), "horizon": horizon_months,
            }
            continue

        rho, pval = spearmanr(merged["signal"], merged["fwd"])
        result[ticker] = {
            "ic": _safe_float(rho),
            "ic_pvalue": _safe_float(pval),
            "n": len(merged),
            "horizon": horizon_months,
        }

    return result


def compute_asset_analytics(
    df: pd.DataFrame,
    states: list[str],
    tickers: dict[str, str] | None = None,
    signal_col: str | None = None,
    horizon_months: int = 3,
) -> dict | None:
    """Compute per-regime asset performance analytics.

    Generic per-regime asset performance: returns, vol, sharpe, win-rate,
    drawdown for each regime state. Used by all 1D regime computers.

    Args:
        df: Regime build() output with a Dominant state column.
        states: List of regime state names.
        tickers: Asset universe (display name → DB code). Defaults to the
            broad macro universe if None.
        signal_col: Column name for the regime's composite Z-score (e.g.
            ``"Growth_Z"``).  When provided, Spearman IC is computed for
            each asset at the regime's designed horizon.
        horizon_months: Forward-return window for IC computation.

    Returns:
        Asset analytics JSONB dict matching the frontend's AssetAnalytics
        interface, or None if prices can't be loaded or the state column
        is missing. Always includes an empty ``liquidity_splits`` key for
        frontend compatibility.
    """
    if tickers is None:
        tickers = DEFAULT_ASSET_TICKERS

    try:
        prices = _load_asset_prices(tickers)
    except Exception as exc:
        log.warning("Asset analytics: price load failed: %s", exc)
        return None

    if prices.empty:
        log.warning("Asset analytics: no prices loaded")
        return None

    rets = prices.pct_change().dropna(how="all")

    state_col = "Dominant"
    if state_col not in df.columns:
        return None

    aligned_all = rets.join(df[state_col].rename("regime"), how="inner").dropna(subset=["regime"])
    aligned = aligned_all[aligned_all["regime"].isin(states)]

    if aligned.empty:
        return None

    asset_cols = [t for t in prices.columns if t in aligned.columns]
    if not asset_cols:
        return None

    # Use BIL as risk-free proxy if present; else zero
    bil_rf = aligned["BIL"] if "BIL" in aligned.columns else pd.Series(0.0, index=aligned.index)

    # ── Per-regime stats ────────────────────────────────────────────
    per_regime_stats: dict[str, dict] = {}
    for regime in states:
        mask = aligned["regime"] == regime
        r_data = aligned.loc[mask]
        assets_list: list[dict] = []

        for t in asset_cols:
            r = r_data[t].dropna()
            rf = bil_rf.reindex(r.index).fillna(0.0)
            n = len(r)

            if n < 3:
                assets_list.append({
                    "ticker": t, "ann_ret": None, "ann_vol": None,
                    "sharpe": None, "win_rate": None, "max_dd": None,
                    "worst_mo": None, "best_mo": None, "months": n,
                })
                continue

            ann_ret = float(r.mean()) * 12
            ann_vol = float(r.std()) * float(np.sqrt(12))
            exc_ret = float((r - rf).mean()) * 12
            sharpe = exc_ret / ann_vol if ann_vol > 1e-9 else 0.0
            win_rt = float((r > 0).mean())
            cum = (1 + r).cumprod()
            max_dd = float((cum / cum.cummax() - 1).min())

            assets_list.append({
                "ticker": t,
                "ann_ret": _safe_float(ann_ret),
                "ann_vol": _safe_float(ann_vol),
                "sharpe": _safe_float(sharpe),
                "win_rate": _safe_float(win_rt),
                "max_dd": _safe_float(max_dd),
                "worst_mo": _safe_float(r.min()),
                "best_mo": _safe_float(r.max()),
                "months": n,
            })

        per_regime_stats[regime] = {
            "months": int(mask.sum()),
            "assets": assets_list,
        }

    # ── Regime counts ───────────────────────────────────────────────
    total = len(aligned_all)
    regime_counts: dict[str, dict] = {}
    for regime in states:
        n = int((aligned["regime"] == regime).sum())
        regime_counts[regime] = {
            "months": n,
            "pct": (n / total * 100) if total > 0 else 0.0,
        }

    # ── Expected returns (probability-weighted from current state) ──
    expected_returns: dict[str, float] = {}
    prob_cols = [f"P_{s}" for s in states]
    last_valid = df.dropna(subset=prob_cols, how="all")
    if not last_valid.empty:
        last = last_valid.iloc[-1]
        s_probs = {
            s: _safe_float(last.get(f"S_P_{s}", last.get(f"P_{s}")), 0.0) or 0.0
            for s in states
        }
        for t in asset_cols:
            exp_ret = 0.0
            total_p = 0.0
            for regime in states:
                r = aligned.loc[aligned["regime"] == regime, t].dropna()
                if len(r) >= 3:
                    p = s_probs[regime]
                    exp_ret += p * (float(r.mean()) * 12)
                    total_p += p
            if total_p > 0:
                expected_returns[t] = _safe_float(exp_ret / total_p) or 0.0

    # ── Small sample regimes (< 12 months of data) ──────────────────
    small_sample = [
        r for r in states
        if len(aligned[aligned["regime"] == r]) < 12
    ]

    # ── Regime separation quality (Cohen's d + Welch t-test per asset) ──
    # Measures how well the regime classification divides forward returns
    # for each asset. Cohen's d is the standardized mean difference between
    # the best and worst states, scale-free and comparable across assets:
    #   d < 0.1  = noise
    #   d 0.1-0.2 = weak
    #   d 0.2-0.5 = meaningful (actionable in finance context)
    #   d 0.5-1.0 = strong
    #   d > 1.0  = exceptional
    # Welch's t-test provides the p-value for "is best ≠ worst significant".
    regime_separation = _compute_regime_separation(aligned, asset_cols, states)

    # ── State-distribution balance ──────────────────────────────────
    # How evenly the regime spreads observations across declared states.
    # Exposes normalized Shannon entropy + usable-state ratio so the
    # frontend can display a "balanced / skewed / concentrated" badge
    # alongside the per-asset Cohen's d table. See balance.py.
    from .balance import compute_state_balance, state_balance_dict
    try:
        balance = compute_state_balance(aligned["regime"], states)
        balance_payload = state_balance_dict(balance)
    except Exception:
        balance_payload = None

    # ── Signal IC (Spearman) per asset ───────────────────────────────
    # Rank correlation between the regime's composite Z-score and each
    # asset's forward H-month return. Only computed when signal_col is
    # provided (1D regimes); composites pass None and skip this.
    signal_ic: dict[str, dict] | None = None
    if signal_col and signal_col in df.columns:
        signal_ic = compute_signal_ic(
            signal=df[signal_col],
            prices=prices,
            asset_cols=asset_cols,
            horizon_months=horizon_months,
        )

    return {
        "per_regime_stats": per_regime_stats,
        "regime_counts": regime_counts,
        "expected_returns": expected_returns,
        "small_sample_regimes": small_sample,
        "regime_separation": regime_separation,
        "signal_ic": signal_ic,
        "state_balance": balance_payload,
        "liquidity_splits": {},  # Reserved for future cross-regime splits
        "tickers": asset_cols,
    }


def compute_regime_strategy(
    df: pd.DataFrame,
    states: list[str],
    tickers: dict[str, str] | None = None,
    warmup_months: int = 60,
    lag_months: int = 1,
    num_assets: int = 5,
    cash_ticker: str = "BIL",
) -> dict | None:
    """Walk-forward regime-based asset allocation backtest.

    At each month *t* (after *warmup_months*):

    1. Observe the confirmed regime state at *t - lag_months*.
    2. Using an expanding window (months 0 .. t), compute mean annualised
       return per asset **in the observed state**.
    3. Pick the top *num_assets* assets with positive expected return;
       allocate proportional to their expected return.
    4. If no asset has positive expected return, hold cash (0 %).

    Compares against:
    - **Equal-weight universe**: 1/N across all assets every month.
    - **SPY buy-and-hold**: 100 % SPY.

    Returns a dict matching the frontend ``StrategyData`` interface, or
    ``None`` if there is insufficient data.
    """
    if tickers is None:
        tickers = DEFAULT_ASSET_TICKERS

    try:
        prices = _load_asset_prices(tickers)
    except Exception as exc:
        log.warning("Strategy: price load failed: %s", exc)
        return None

    if prices.empty:
        return None

    rets = prices.pct_change().dropna(how="all")

    state_col = "Dominant"
    if state_col not in df.columns:
        return None

    aligned = rets.join(df[state_col].rename("regime"), how="inner").dropna(subset=["regime"])
    aligned = aligned[aligned["regime"].isin(states)]

    asset_cols = [t for t in prices.columns if t != cash_ticker and t in aligned.columns]
    all_cols = [t for t in prices.columns if t in aligned.columns]
    if not asset_cols or len(aligned) < warmup_months + 12:
        return None

    has_spy = "SPY" in aligned.columns
    has_cash = cash_ticker in aligned.columns
    cost_bps = 10  # round-trip commission in basis points

    # ── Walk-forward loop ──────────────────────────────────────────
    wf_rets: list[float] = []
    ew_rets: list[float] = []
    spy_rets: list[float] = []
    wf_dates: list[str] = []
    regime_dates: list[str] = []
    regime_labels: list[str] = []
    allocation_history: dict[str, dict[str, float]] = {}  # state -> latest weights
    holdings_history: list[dict[str, float]] = []  # per-month weights
    prev_weights: dict[str, float] = {}

    idx = aligned.index
    for pos in range(warmup_months + lag_months, len(idx)):
        t = idx[pos]
        lagged_pos = pos - lag_months
        if lagged_pos < warmup_months:
            continue

        current_state = str(aligned.iloc[lagged_pos]["regime"])
        regime_dates.append(t.strftime("%Y-%m-%d"))
        regime_labels.append(current_state)

        # Expanding window: all data up to (not including) current month
        history = aligned.iloc[:pos]
        in_state = history[history["regime"] == current_state]

        # Excess return vs unconditional mean (expanding window).
        # "Which assets benefit from knowing we're in this state?"
        excess_rets: dict[str, float] = {}
        for ticker in asset_cols:
            r_state = in_state[ticker].dropna()
            r_all = history[ticker].dropna()
            if len(r_state) >= 3 and len(r_all) >= 12:
                state_mean = float(r_state.mean()) * 12
                uncond_mean = float(r_all.mean()) * 12
                excess_rets[ticker] = state_mean - uncond_mean

        # Top N with positive excess return, allocate proportional.
        # If NO asset has positive excess → 100% cash (BIL).
        positive = {k: v for k, v in excess_rets.items() if v > 0}
        sorted_pos = sorted(positive.items(), key=lambda x: x[1], reverse=True)
        top_n = sorted_pos[:num_assets]

        if top_n:
            total_excess = sum(v for _, v in top_n)
            weights = {ticker: exc / total_excess for ticker, exc in top_n}
        else:
            weights = {cash_ticker: 1.0} if has_cash else {}

        allocation_history[current_state] = weights
        holdings_history.append(weights)

        # Turnover cost: sum of absolute weight changes × cost_bps / 10_000
        turnover = sum(
            abs(weights.get(t, 0.0) - prev_weights.get(t, 0.0))
            for t in set(list(weights.keys()) + list(prev_weights.keys()))
        )
        txn_cost = turnover * cost_bps / 10_000
        prev_weights = weights

        # Portfolio return this month (net of transaction cost).
        # Use 0.0 for any ticker with missing data (e.g., BIL before 2007).
        row = aligned.iloc[pos]
        month_ret = sum(
            w * (float(row[ticker]) if ticker in row.index and pd.notna(row[ticker]) else 0.0)
            for ticker, w in weights.items()
        ) - txn_cost
        wf_rets.append(month_ret)

        # Equal-weight benchmark
        valid_rets = [float(aligned.iloc[pos][c]) for c in all_cols if pd.notna(aligned.iloc[pos][c])]
        ew_rets.append(np.mean(valid_rets) if valid_rets else 0.0)

        # SPY buy-and-hold
        spy_rets.append(float(aligned.iloc[pos]["SPY"]) if has_spy else 0.0)

        wf_dates.append(t.strftime("%Y-%m-%d"))

    if len(wf_rets) < 12:
        return None

    # ── Build equity curves ────────────────────────────────────────
    def build_equity(monthly_rets: list[float]) -> list[float]:
        eq = [1.0]
        for r in monthly_rets:
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

    def build_stats(monthly_rets: list[float], equity: list[float]) -> dict:
        n = len(monthly_rets)
        if n < 2:
            return {"cagr": 0.0, "ann_vol": 0.0, "sharpe": 0.0, "max_dd": 0.0, "months": n}
        arr = np.array(monthly_rets)
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

    # Dates for equity (one extra point for the initial $1)
    eq_dates = [wf_dates[0]] + wf_dates

    # ── Yearly returns ─────────────────────────────────────────────
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

    # ── Allocation templates (latest weights per state) ────────────
    templates: dict[str, dict[str, float]] = {}
    for state in states:
        if state in allocation_history:
            templates[state] = {
                k: _safe_float(v) or 0.0
                for k, v in allocation_history[state].items()
            }
        else:
            templates[state] = {}

    return {
        "start_date": wf_dates[0] if wf_dates else None,
        "end_date": wf_dates[-1] if wf_dates else None,
        "months": len(wf_rets),
        "wf_lookback": warmup_months,
        "num_assets": num_assets,
        "lag_months": lag_months,
        "models": {
            "wf_best_asset": {
                "label": "WF Top-5 (regime)",
                "description": "Walk-forward top-5 assets by regime state, proportional allocation",
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
            "dates": regime_dates,
            "regimes": regime_labels,
        },
        "yearly_returns": yearly,
        "allocation_templates": templates,
        "assets": asset_cols + ([cash_ticker] if has_cash and cash_ticker not in asset_cols else []),
        "holdings_history": {
            "dates": wf_dates,
            "holdings": [
                {k: _safe_float(v) or 0.0 for k, v in h.items()}
                for h in holdings_history
            ],
        },
        "cost_bps": cost_bps,
    }


def _compute_regime_separation(
    aligned: pd.DataFrame,
    asset_cols: list[str],
    states: list[str],
) -> dict[str, dict]:
    """Compute Cohen's d (best vs worst) + Welch t-test per asset.

    For each asset:
      1. Group monthly returns by regime state
      2. Find the best-return state and worst-return state
      3. Compute Cohen's d = (mean_best - mean_worst) / pooled_std
      4. Compute Welch's t-test p-value for best ≠ worst
      5. Compute η² across ALL states for backward-compat reference

    Cohen's d is scale-free and fair across 2-state and 4-state regimes
    (unlike η² which is bounded lower for fewer-state classifiers).

    Cohen's d thresholds for financial returns (not Cohen's original
    psychology-calibrated thresholds):
      d < 0.1  → noise
      d 0.1-0.2 → weak but real
      d 0.2-0.5 → meaningful (actionable)
      d 0.5-1.0 → strong
      d > 1.0  → exceptional

    Returns:
        {ticker: {
            cohens_d: float,      # |mean_best - mean_worst| / pooled_std
            p_value: float,       # Welch t-test p, best vs worst
            best_state: str,      # name of highest-mean state
            worst_state: str,     # name of lowest-mean state
            eta_sq: float,        # ANOVA η² across all states (reference)
            n: int,               # total observations
        }}
    """
    from scipy.stats import ttest_ind, f as f_dist

    result: dict[str, dict] = {}
    for t in asset_cols:
        # Collect per-state return arrays
        state_data: dict[str, np.ndarray] = {}
        for state in states:
            g = aligned.loc[aligned["regime"] == state, t].dropna().values
            if len(g) >= 3:
                state_data[state] = g

        if len(state_data) < 2:
            result[t] = {
                "cohens_d": None, "p_value": None,
                "best_state": None, "worst_state": None,
                "eta_sq": None, "n": 0,
            }
            continue

        # Find best and worst states by mean
        means = {s: float(g.mean()) for s, g in state_data.items()}
        best_name = max(means, key=means.get)
        worst_name = min(means, key=means.get)

        best_values = state_data[best_name]
        worst_values = state_data[worst_name]
        n1, n2 = len(best_values), len(worst_values)

        # Cohen's d with pooled standard deviation
        s1_sq = float(best_values.var(ddof=1)) if n1 >= 2 else 0.0
        s2_sq = float(worst_values.var(ddof=1)) if n2 >= 2 else 0.0
        pooled_var = ((n1 - 1) * s1_sq + (n2 - 1) * s2_sq) / max(n1 + n2 - 2, 1)
        pooled_std = float(np.sqrt(pooled_var)) if pooled_var > 0 else 0.0

        if pooled_std < 1e-12:
            cohens_d = None
        else:
            cohens_d = (means[best_name] - means[worst_name]) / pooled_std

        # Welch's t-test for best vs worst (unequal variance, sample-size aware)
        try:
            _, p_welch = ttest_ind(best_values, worst_values, equal_var=False)
        except Exception:
            p_welch = None

        # Also compute η² across ALL states as a backward-compat reference
        all_obs = np.concatenate(list(state_data.values()))
        n_total = len(all_obs)
        k = len(state_data)
        grand_mean = float(all_obs.mean())
        ss_between = sum(
            len(g) * (float(g.mean()) - grand_mean) ** 2
            for g in state_data.values()
        )
        ss_within = sum(
            float(((g - g.mean()) ** 2).sum())
            for g in state_data.values()
        )
        ss_total = ss_between + ss_within
        eta_sq = ss_between / ss_total if ss_total > 1e-12 else 0.0

        result[t] = {
            "cohens_d": _safe_float(cohens_d),
            "p_value": _safe_float(p_welch),
            "best_state": best_name,
            "worst_state": worst_name,
            "eta_sq": _safe_float(eta_sq),
            "n": int(n_total),
        }

    return result


# ─────────────────────────────────────────────────────────────────────
# Serialization helpers
# ─────────────────────────────────────────────────────────────────────

def _safe_float(val: Any, fallback: float | None = None) -> float | None:
    """Convert to float, returning fallback for NaN/None/inf."""
    if val is None:
        return fallback
    try:
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return fallback
        return f
    except (TypeError, ValueError):
        return fallback


def _series_to_list(s: pd.Series) -> list:
    """Convert a pandas Series to a JSON-safe list (NaN → None)."""
    if s is None or s.empty:
        return []
    return [None if pd.isna(v) else _safe_float(v) for v in s.values]


def _dates_to_list(idx: pd.DatetimeIndex) -> list[str]:
    """ISO date strings for a DatetimeIndex."""
    if idx is None or len(idx) == 0:
        return []
    return [d.strftime("%Y-%m-%d") for d in idx]


def _prob_dict(row: pd.Series, states: list[str], prefix: str = "P_") -> dict[str, float]:
    """Extract state probabilities from a DataFrame row."""
    return {
        s: _safe_float(row.get(f"{prefix}{s}"), 0.0)
        for s in states
    }


# ─────────────────────────────────────────────────────────────────────
# Generic computer
# ─────────────────────────────────────────────────────────────────────


class RegimeComputer:
    """Generic compute pipeline for any standalone Regime subclass.

    Used by all 1D regimes. Multi-axis composites are generated on
    demand by ``ix.core.regimes.compose`` and do not subclass this.
    """

    def __init__(self, registration: RegimeRegistration):
        self.reg = registration

    def compute(self, params: dict) -> dict:
        """Run the regime pipeline and return the full JSONB payload.

        Returns a dict with keys matching RegimeSnapshot columns:
        ``current_state``, ``timeseries``, ``strategy``, ``asset_analytics``, ``meta``.
        """
        if self.reg.regime_class is None:
            raise ValueError(
                f"Regime '{self.reg.key}' has no regime_class — "
                f"it needs a custom computer_class."
            )

        regime: Regime = self.reg.regime_class()
        df = regime.build(
            z_window=params.get("z_window", 36),
            sensitivity=params.get("sensitivity", 1.0),
            smooth_halflife=params.get("smooth_halflife", 4),
        )

        if df.empty:
            raise RuntimeError(f"Regime '{self.reg.key}' built an empty DataFrame")

        # Auto-compute asset analytics using the registration's declared
        # asset universe (or the default broad universe if none declared).
        # Determine signal column for IC computation — first dimension's Z
        signal_col = (
            f"{self.reg.dimensions[0]}_Z"
            if self.reg.dimensions else None
        )

        try:
            asset_analytics = compute_asset_analytics(
                df,
                states=self.reg.states,
                tickers=self.reg.asset_tickers,
                signal_col=signal_col,
                horizon_months=self.reg.horizon_months,
            )
        except Exception as exc:
            log.warning("Asset analytics computation failed for '%s': %s",
                        self.reg.key, exc)
            asset_analytics = None

        try:
            strategy = compute_regime_strategy(
                df,
                states=self.reg.states,
                tickers=self.reg.asset_tickers,
            )
        except Exception as exc:
            log.warning("Strategy computation failed for '%s': %s",
                        self.reg.key, exc)
            strategy = None

        return {
            "current_state": self.serialize_current_state(df),
            "timeseries": self.serialize_timeseries(df),
            "strategy": strategy,
            "asset_analytics": asset_analytics,
            "meta": self.serialize_meta(),
        }

    # ── Serialization methods (overridable) ─────────────────────────

    def serialize_current_state(self, df: pd.DataFrame) -> dict:
        """Serialize the latest month into a snapshot dict.

        Always shows the most recent available data for each regime.
        If the latest month has partial data (some indicators published,
        others not yet), we still show the last row where the composite
        Z was valid. This prevents composed regimes from showing
        zeros/blanks when one axis publishes ahead of another.
        """
        states = self.reg.states
        dimensions = self.reg.dimensions

        # Find last row with valid composite data — forward-fill first
        # so the last known state carries through even if the very latest
        # month has NaN composite (e.g., monthly macro data hasn't published
        # yet but daily market data has a new row).
        key_col = f"{dimensions[0]}_Z"
        if key_col not in df.columns:
            return {"date": None, "error": "No composite data"}

        filtered = df.dropna(subset=[key_col])
        if filtered.empty:
            return {"date": None, "error": "No valid rows"}

        # Use the actual last date from the full DataFrame (not the filtered one)
        # so the "as of" date reflects the latest data available, even if we
        # forward-fill the composite from an earlier month.
        last = filtered.iloc[-1]
        last_date = df.index[-1] if not df.empty else filtered.index[-1]

        # Dominant state
        dominant = str(last.get("Dominant", states[0]))
        dom_prob = _safe_float(
            last.get(f"S_P_{dominant}", last.get(f"P_{dominant}")),
            0.0,
        )

        # Dimensions
        dim_data = {}
        for dim in dimensions:
            z = _safe_float(last.get(f"{dim}_Z"), 0.0)
            p = _safe_float(last.get(f"{dim}_P"), 0.5)
            prefix = dim[0].lower() + "_"
            components = []
            for col in last.index:
                if col.startswith(prefix) and col != "g_Claims4WMA":
                    val = _safe_float(last.get(col))
                    if val is not None:
                        components.append({
                            "name": col.replace(prefix, ""),
                            "z": val,
                        })
            direction = self._direction_label(dim, z)
            dim_data[dim] = {
                "z": z,
                "p": p,
                "direction": direction,
                "score": int(_safe_float(last.get(f"{dim}_Score"), 0) or 0),
                "total": int(_safe_float(last.get(f"{dim}_Total"), len(components)) or len(components)),
                "components": components,
            }

        return {
            "date": last_date.strftime("%Y-%m"),
            "dominant": dominant,
            "dominant_probability": dom_prob,
            "conviction": _safe_float(last.get("Conviction"), 50.0),
            "months_in_regime": int(_safe_float(last.get("Months_In_Regime"), 1) or 1),
            "probabilities": {
                s: _safe_float(last.get(f"S_P_{s}", last.get(f"P_{s}")), 0.0)
                for s in states
            },
            "dimensions": dim_data,
        }

    def serialize_timeseries(self, df: pd.DataFrame) -> dict:
        """Serialize the full history for History + Indicators pages."""
        states = self.reg.states
        dimensions = self.reg.dimensions

        # Clip history to 2000-01-01 — pre-2000 data is sparse and out of scope
        df = df.loc["2000-01-01":].copy()
        dates = _dates_to_list(df.index)

        composites = {}
        for dim in dimensions:
            z_col = f"{dim}_Z"
            if z_col in df.columns:
                composites[z_col] = _series_to_list(df[z_col])

        probs = {}
        smoothed_probs = {}
        for s in states:
            if f"P_{s}" in df.columns:
                probs[s] = _series_to_list(df[f"P_{s}"])
            if f"S_P_{s}" in df.columns:
                smoothed_probs[s] = _series_to_list(df[f"S_P_{s}"])

        # All individual indicators (g_*, i_*, l_*, m_*)
        indicators = {}
        for col in df.columns:
            if col[:2] in ("g_", "i_", "l_", "m_"):
                indicators[col] = _series_to_list(df[col])

        dominant = (
            df["Dominant"].fillna("").astype(str).tolist()
            if "Dominant" in df.columns else []
        )
        conviction = (
            _series_to_list(df["Conviction"]) if "Conviction" in df.columns else []
        )

        return {
            "dates": dates,
            "composites": composites,
            "raw_probabilities": probs,
            "smoothed_probabilities": smoothed_probs,
            # Legacy alias — kept so old cached snapshots and the
            # compose endpoint (which reads "probabilities") still work.
            "probabilities": probs,
            "dominant": dominant,
            "conviction": conviction,
            "indicators": indicators,
        }

    def serialize_meta(self) -> dict:
        """Return methodology + colors + documentation."""
        return {
            "model_name": self.reg.display_name,
            "description": self.reg.description,
            "states": self.reg.states,
            "dimensions": self.reg.dimensions,
            "color_map": self.reg.color_map,
            "dimension_colors": self.reg.dimension_colors,
            "methodology": {
                "z_score": "25% level + 75% ROC blend",
                "sigmoid_mapping": "logistic function maps z → probability (0-1)",
                "ema_smoothing": "Exponential moving average on state probabilities (halflife-tuned per regime)",
            },
        }

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _direction_label(dim: str, z: float) -> str:
        pos_neg = {
            "Growth":    ("Expanding", "Contracting"),
            "Inflation": ("Rising",    "Falling"),
            "Liquidity": ("Easing",    "Tightening"),
        }
        pos, neg = pos_neg.get(dim, ("Positive", "Negative"))
        return pos if z >= 0 else neg

    # ── Persistence ──────────────────────────────────────────────────

    def save(self, params: dict, payload: dict) -> str:
        """Upsert the computed payload into the regime_snapshot table.

        Returns the fingerprint of the saved row.
        """
        fp = regime_fingerprint(self.reg.key, params)
        now = datetime.now(timezone.utc)

        with Session() as session:
            existing = session.get(RegimeSnapshot, fp)
            if existing is None:
                row = RegimeSnapshot(
                    fingerprint=fp,
                    regime_type=self.reg.key,
                    computed_at=now,
                    parameters=params,
                    current_state=payload["current_state"],
                    timeseries=payload["timeseries"],
                    strategy=payload.get("strategy"),
                    asset_analytics=payload.get("asset_analytics"),
                    meta=payload.get("meta"),
                )
                session.add(row)
            else:
                existing.computed_at = now
                existing.parameters = params
                existing.current_state = payload["current_state"]
                existing.timeseries = payload["timeseries"]
                existing.strategy = payload.get("strategy")
                existing.asset_analytics = payload.get("asset_analytics")
                existing.meta = payload.get("meta")
            session.commit()

        log.info("Saved regime snapshot: %s", fp)
        return fp

    def compute_and_save(self, params: dict | None = None) -> str:
        """Run compute() + save() in one call. Returns the fingerprint."""
        params = params or self.reg.default_params
        payload = self.compute(params)
        return self.save(params, payload)


# ─────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────


def compute_regime(key: str, params: dict | None = None) -> str:
    """Compute and save any registered regime by key.

    Returns the fingerprint of the saved snapshot.
    """
    from .registry import get_regime

    reg = get_regime(key)
    computer_cls = reg.computer_class or RegimeComputer
    computer = computer_cls(reg)
    return computer.compute_and_save(params)
