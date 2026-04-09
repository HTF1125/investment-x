"""Pure weight functions for batch strategy allocation."""

import pandas as pd
import numpy as np

from .constants import SECTORS

# ════════════════════════════════════════════════════════════════════


def _available(px, assets):
    return [a for a in assets if a in px.columns and px[a].notna().any()]


def _equal_weight(assets):
    if not assets:
        return pd.Series(dtype=float)
    return pd.Series(1.0 / len(assets), index=assets)


def _compute_rsi(series, period):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(period, min_periods=period).mean()
    avg_loss = loss.rolling(period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, 1e-10)
    return 100 - (100 / (1 + rs))


# ════════════════════════════════════════════════════════════════════
# WEIGHT FUNCTIONS (31)
# ════════════════════════════════════════════════════════════════════


def wf_static(px, d, p):
    return pd.Series(p["weights"])


def wf_momentum(px, d, p):
    lb = p["lookback"]
    top_n = p.get("top_n", 1)
    assets = _available(px, p["assets"])
    cash = p.get("cash")
    if len(px) <= lb or not assets:
        return _equal_weight(assets or ["SPY"])
    ret = px[assets].iloc[-1] / px[assets].iloc[-lb - 1] - 1
    ret = ret.dropna()
    if cash and cash in px.columns and len(px[cash].dropna()) > lb:
        cash_ret = px[cash].iloc[-1] / px[cash].iloc[-lb - 1] - 1
        candidates = ret[ret > cash_ret]
        if candidates.empty:
            return pd.Series({cash: 1.0})
    else:
        candidates = ret[ret > 0] if p.get("absolute", True) else ret
    if candidates.empty:
        if cash:
            return pd.Series({cash: 1.0})
        return _equal_weight(assets)
    top = candidates.nlargest(min(top_n, len(candidates)))
    return pd.Series(1.0 / len(top), index=top.index)


def wf_momentum_13612w(px, d, p):
    assets = _available(px, p["assets"])
    top_n = p.get("top_n", 1)
    cash = p.get("cash")
    if len(px) < 13 or not assets:
        return _equal_weight(assets or ["SPY"])
    pr = px[assets]
    r1 = pr.iloc[-1] / pr.iloc[-2] - 1
    r3 = pr.iloc[-1] / pr.iloc[-4] - 1 if len(pr) > 3 else r1
    r6 = pr.iloc[-1] / pr.iloc[-7] - 1 if len(pr) > 6 else r3
    r12 = pr.iloc[-1] / pr.iloc[-13] - 1 if len(pr) > 12 else r6
    score = 12 * r1 + 4 * r3 + 2 * r6 + r12
    if cash and cash in px.columns and len(px[cash].dropna()) > 12:
        c = px[cash]
        c_r1 = c.iloc[-1] / c.iloc[-2] - 1
        c_r3 = c.iloc[-1] / c.iloc[-4] - 1 if len(c) > 3 else c_r1
        c_r6 = c.iloc[-1] / c.iloc[-7] - 1 if len(c) > 6 else c_r3
        c_r12 = c.iloc[-1] / c.iloc[-13] - 1 if len(c) > 12 else c_r6
        cash_score = 12 * c_r1 + 4 * c_r3 + 2 * c_r6 + c_r12
        candidates = score[score > cash_score].dropna()
        if candidates.empty:
            return pd.Series({cash: 1.0})
    else:
        candidates = score.dropna()
        candidates = candidates[candidates > 0]
    if candidates.empty:
        return pd.Series({cash: 1.0}) if cash else _equal_weight(assets)
    top = candidates.nlargest(min(top_n, len(candidates)))
    return pd.Series(1.0 / len(top), index=top.index)


def wf_sector_momentum(px, d, p):
    lb = p["lookback"]
    top_n = p.get("top_n", 3)
    sectors = _available(px, p.get("sectors", SECTORS))
    fallback = p.get("fallback", "SPY")
    if len(px) <= lb or len(sectors) < top_n:
        return pd.Series({fallback: 1.0})
    ret = px[sectors].iloc[-1] / px[sectors].iloc[-lb - 1] - 1
    ret = ret.dropna()
    if len(ret) < top_n:
        return pd.Series({fallback: 1.0})
    top = ret.nlargest(top_n)
    top = top[top > 0]
    if top.empty:
        return pd.Series({fallback: 1.0})
    return pd.Series(1.0 / len(top), index=top.index)


def wf_trend_sma(px, d, p):
    sma = p["sma_months"]
    equity = p.get("equity", "SPY")
    bond = p.get("bond", "IEF")
    if equity not in px.columns or len(px) < sma + 1:
        return pd.Series({equity: 0.5, bond: 0.5})
    price = px[equity].iloc[-1]
    sma_val = px[equity].iloc[-sma:].mean()
    if price > sma_val:
        return pd.Series({equity: 1.0, bond: 0.0})
    return pd.Series({equity: 0.0, bond: 1.0})


def wf_dual_sma(px, d, p):
    fast = p["fast"]
    slow = p["slow"]
    equity = p.get("equity", "SPY")
    bond = p.get("bond", "IEF")
    if equity not in px.columns or len(px) < slow + 1:
        return pd.Series({equity: 0.5, bond: 0.5})
    fast_sma = px[equity].iloc[-fast:].mean()
    slow_sma = px[equity].iloc[-slow:].mean()
    if fast_sma > slow_sma:
        return pd.Series({equity: 1.0, bond: 0.0})
    return pd.Series({equity: 0.0, bond: 1.0})


def wf_trend_breadth(px, d, p):
    sma = p.get("sma_months", 10)
    assets = _available(px, p["assets"])
    equity = p.get("equity", "SPY")
    bond = p.get("bond", "IEF")
    if len(px) < sma + 1 or not assets:
        return pd.Series({equity: 0.5, bond: 0.5})
    above = sum(1 for a in assets if px[a].iloc[-1] > px[a].iloc[-sma:].mean())
    breadth = above / len(assets)
    return pd.Series({equity: breadth, bond: 1 - breadth})


def wf_dual_momentum(px, d, p):
    lb = p["lookback"]
    risky = _available(px, p["risky"])
    safe = p.get("safe", "IEF")
    cash = p.get("cash", "BIL")
    if not risky or len(px) <= lb:
        return pd.Series({safe: 1.0})
    rets = {}
    for a in risky + [safe]:
        if a in px.columns and len(px[a].dropna()) > lb:
            rets[a] = px[a].iloc[-1] / px[a].iloc[-lb - 1] - 1
    cash_ret = 0
    if cash in px.columns and len(px[cash].dropna()) > lb:
        cash_ret = px[cash].iloc[-1] / px[cash].iloc[-lb - 1] - 1
    risky_rets = {a: rets[a] for a in risky if a in rets}
    if not risky_rets:
        return pd.Series({safe: 1.0})
    best = max(risky_rets, key=risky_rets.get)
    if risky_rets[best] > cash_ret:
        return pd.Series({best: 1.0})
    elif safe in rets and rets[safe] > cash_ret:
        return pd.Series({safe: 1.0})
    else:
        return pd.Series({cash: 1.0}) if cash in px.columns else pd.Series({safe: 1.0})


def wf_defensive_rotation(px, d, p):
    assets = _available(px, p["assets"])
    cash = p.get("cash", "BIL")
    top_n = p.get("top_n", 2)
    fallback = p.get("fallback", "SPY")
    if len(px) < 13 or not assets:
        return pd.Series({fallback: 1.0})
    scores = {}
    for a in assets:
        pr = px[a].dropna()
        if len(pr) < 13:
            continue
        r1 = pr.iloc[-1] / pr.iloc[-2] - 1
        r3 = pr.iloc[-1] / pr.iloc[-4] - 1 if len(pr) > 3 else r1
        r6 = pr.iloc[-1] / pr.iloc[-7] - 1 if len(pr) > 6 else r3
        r12 = pr.iloc[-1] / pr.iloc[-13] - 1 if len(pr) > 12 else r6
        scores[a] = 12 * r1 + 4 * r3 + 2 * r6 + r12
    cash_score = 0
    if cash in px.columns and len(px[cash].dropna()) > 12:
        c = px[cash].dropna()
        c_r1 = c.iloc[-1] / c.iloc[-2] - 1
        c_r3 = c.iloc[-1] / c.iloc[-4] - 1 if len(c) > 3 else c_r1
        c_r6 = c.iloc[-1] / c.iloc[-7] - 1 if len(c) > 6 else c_r3
        c_r12 = c.iloc[-1] / c.iloc[-13] - 1 if len(c) > 12 else c_r6
        cash_score = 12 * c_r1 + 4 * c_r3 + 2 * c_r6 + c_r12
    passing = {a: s for a, s in scores.items() if s > cash_score}
    if not passing:
        return pd.Series({fallback: 1.0})
    ranked = sorted(passing.items(), key=lambda x: x[1], reverse=True)[:top_n]
    w = 1.0 / len(ranked)
    return pd.Series({a: w for a, _ in ranked})


def wf_inverse_vol(px, d, p):
    vol_window = p["vol_window"]
    assets = _available(px, p["assets"])
    if len(px) <= vol_window or not assets:
        return _equal_weight(assets)
    ret = px[assets].pct_change().iloc[-vol_window:]
    vol = ret.std() * np.sqrt(12)
    vol = vol.replace(0, np.nan).dropna()
    if vol.empty:
        return _equal_weight(assets)
    inv = 1.0 / vol
    return inv / inv.sum()


def wf_vol_target(px, d, p):
    target_vol = p["target_vol"]
    vol_window = p.get("vol_window", 12)
    equity = p.get("equity", "SPY")
    bond = p.get("bond", "IEF")
    if equity not in px.columns or len(px) <= vol_window:
        return pd.Series({equity: 0.5, bond: 0.5})
    ret = px[equity].pct_change().iloc[-vol_window:]
    realized_vol = ret.std() * np.sqrt(12)
    if realized_vol < 1e-10:
        return pd.Series({equity: 0.5, bond: 0.5})
    eq_weight = min(1.0, max(0.0, target_vol / realized_vol))
    return pd.Series({equity: eq_weight, bond: 1 - eq_weight})


def wf_macro_level(px, d, p):
    macro = p["macro_data"]
    threshold = p["threshold"]
    equity = p.get("equity", "SPY")
    bond = p.get("bond", "IEF")
    lag = p.get("lag", 1)
    m = macro.loc[:d]
    if len(m) < lag + 1:
        return pd.Series({equity: 0.5, bond: 0.5})
    val = m.iloc[-(lag + 1)]
    if pd.isna(val):
        return pd.Series({equity: 0.5, bond: 0.5})
    if val > threshold:
        return pd.Series({equity: 1.0, bond: 0.0})
    return pd.Series({equity: 0.0, bond: 1.0})


def wf_macro_direction(px, d, p):
    macro = p["macro_data"]
    equity = p.get("equity", "SPY")
    bond = p.get("bond", "IEF")
    lag = p.get("lag", 1)
    ma_window = p.get("ma_window", 3)
    m = macro.loc[:d]
    if len(m) < lag + ma_window + 2:
        return pd.Series({equity: 0.5, bond: 0.5})
    ma = m.rolling(ma_window).mean()
    current = ma.iloc[-(lag + 1)]
    prev = ma.iloc[-(lag + 2)]
    if pd.isna(current) or pd.isna(prev):
        return pd.Series({equity: 0.5, bond: 0.5})
    if current > prev:
        return pd.Series({equity: 1.0, bond: 0.0})
    return pd.Series({equity: 0.0, bond: 1.0})


def wf_vix_regime(px, d, p):
    macro = p["macro_data"]
    high_thresh = p.get("high_thresh", 25)
    low_thresh = p.get("low_thresh", 15)
    equity = p.get("equity", "SPY")
    bond = p.get("bond", "IEF")
    m = macro.loc[:d]
    if m.empty:
        return pd.Series({equity: 0.5, bond: 0.5})
    vix = m.iloc[-1]
    if pd.isna(vix):
        return pd.Series({equity: 0.5, bond: 0.5})
    if vix > high_thresh:
        return pd.Series({equity: 1.0, bond: 0.0})
    elif vix < low_thresh:
        return pd.Series({equity: 0.0, bond: 1.0})
    return pd.Series({equity: 0.5, bond: 0.5})


def wf_rsi(px, d, p):
    period = p["period"]
    equity = p.get("equity", "SPY")
    bond = p.get("bond", "IEF")
    overbought = p.get("overbought", 70)
    oversold = p.get("oversold", 30)
    if equity not in px.columns or len(px) < period + 2:
        return pd.Series({equity: 0.5, bond: 0.5})
    rsi = _compute_rsi(px[equity], period)
    val = rsi.iloc[-1]
    if pd.isna(val):
        return pd.Series({equity: 0.5, bond: 0.5})
    if val < oversold:
        return pd.Series({equity: 1.0, bond: 0.0})
    elif val > overbought:
        return pd.Series({equity: 0.0, bond: 1.0})
    return pd.Series({equity: 0.5, bond: 0.5})


def wf_zscore(px, d, p):
    window = p["window"]
    equity = p.get("equity", "SPY")
    bond = p.get("bond", "IEF")
    threshold = p.get("threshold", 1.5)
    if equity not in px.columns or len(px) < window + 1:
        return pd.Series({equity: 0.5, bond: 0.5})
    s = px[equity].iloc[-window:]
    mu = s.mean()
    sigma = s.std()
    if sigma < 1e-10:
        return pd.Series({equity: 0.5, bond: 0.5})
    z = (s.iloc[-1] - mu) / sigma
    if z < -threshold:
        return pd.Series({equity: 1.0, bond: 0.0})
    elif z > threshold:
        return pd.Series({equity: 0.0, bond: 1.0})
    return pd.Series({equity: 0.5, bond: 0.5})


def wf_seasonal(px, d, p):
    equity_months = p["equity_months"]
    equity = p.get("equity", "SPY")
    bond = p.get("bond", "IEF")
    if d.month in equity_months:
        return pd.Series({equity: 1.0, bond: 0.0})
    return pd.Series({equity: 0.0, bond: 1.0})


def wf_mom_trend(px, d, p):
    mom_lb = p.get("mom_lookback", 12)
    sma_lb = p.get("sma_lookback", 10)
    equity = p.get("equity", "SPY")
    bond = p.get("bond", "IEF")
    mode = p.get("mode", "both")
    if equity not in px.columns or len(px) < max(mom_lb, sma_lb) + 1:
        return pd.Series({equity: 0.5, bond: 0.5})
    pr = px[equity]
    sig_mom = (pr.iloc[-1] / pr.iloc[-mom_lb - 1] - 1) > 0
    sig_trend = pr.iloc[-1] > pr.iloc[-sma_lb:].mean()
    if mode == "both":
        if sig_mom and sig_trend:
            return pd.Series({equity: 1.0, bond: 0.0})
        elif not sig_mom and not sig_trend:
            return pd.Series({equity: 0.0, bond: 1.0})
        return pd.Series({equity: 0.5, bond: 0.5})
    elif mode == "any":
        if sig_mom or sig_trend:
            return pd.Series({equity: 1.0, bond: 0.0})
        return pd.Series({equity: 0.0, bond: 1.0})
    w = (int(sig_mom) + int(sig_trend)) / 2
    return pd.Series({equity: w, bond: 1 - w})


def wf_macro_trend(px, d, p):
    macro = p["macro_data"]
    threshold = p.get("threshold", 50)
    lag = p.get("lag", 1)
    sma_lb = p.get("sma_lookback", 10)
    equity = p.get("equity", "SPY")
    bond = p.get("bond", "IEF")
    if equity not in px.columns or len(px) < sma_lb + 1:
        return pd.Series({equity: 0.5, bond: 0.5})
    m = macro.loc[:d]
    if len(m) < lag + 2:
        sig_macro = True
    else:
        val = m.iloc[-(lag + 1)]
        sig_macro = not pd.isna(val) and val > threshold
    pr = px[equity]
    sig_trend = pr.iloc[-1] > pr.iloc[-sma_lb:].mean()
    if sig_macro and sig_trend:
        return pd.Series({equity: 1.0, bond: 0.0})
    elif not sig_macro and not sig_trend:
        return pd.Series({equity: 0.0, bond: 1.0})
    return pd.Series({equity: 0.5, bond: 0.5})


def wf_triple(px, d, p):
    macro = p["macro_data"]
    threshold = p.get("threshold", 50)
    lag = p.get("lag", 1)
    mom_lb = p.get("mom_lookback", 12)
    sma_lb = p.get("sma_lookback", 10)
    equity = p.get("equity", "SPY")
    bond = p.get("bond", "IEF")
    if equity not in px.columns or len(px) < max(mom_lb, sma_lb) + 1:
        return pd.Series({equity: 0.5, bond: 0.5})
    pr = px[equity]
    sig_mom = int((pr.iloc[-1] / pr.iloc[-mom_lb - 1] - 1) > 0)
    sig_trend = int(pr.iloc[-1] > pr.iloc[-sma_lb:].mean())
    m = macro.loc[:d]
    if len(m) < lag + 2:
        sig_macro = 1
    else:
        val = m.iloc[-(lag + 1)]
        sig_macro = int(not pd.isna(val) and val > threshold)
    votes = sig_mom + sig_trend + sig_macro
    if votes >= 3:
        return pd.Series({equity: 1.0, bond: 0.0})
    elif votes == 2:
        return pd.Series({equity: 0.7, bond: 0.3})
    elif votes == 1:
        return pd.Series({equity: 0.3, bond: 0.7})
    return pd.Series({equity: 0.0, bond: 1.0})


def wf_multi_trend_momentum(px, d, p):
    sma_lb = p.get("sma_months", 10)
    mom_lb = p.get("mom_months", 6)
    assets = _available(px, p["assets"])
    cash = p.get("cash", "BIL")
    top_n = p.get("top_n", 3)
    if len(px) < max(sma_lb, mom_lb) + 1 or not assets:
        return pd.Series({cash: 1.0}) if cash in px.columns else _equal_weight(assets)
    scores = {}
    for a in assets:
        pr = px[a].dropna()
        if len(pr) < max(sma_lb, mom_lb) + 1:
            continue
        trend = pr.iloc[-1] > pr.iloc[-sma_lb:].mean()
        mom = pr.iloc[-1] / pr.iloc[-mom_lb - 1] - 1
        if trend and mom > 0:
            scores[a] = mom
    if not scores:
        return pd.Series({cash: 1.0}) if cash in px.columns else _equal_weight(assets)
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
    w = 1.0 / len(ranked)
    return pd.Series({a: w for a, _ in ranked})


def wf_drawdown_control(px, d, p):
    dd_thresh = p.get("dd_thresh", -0.10)
    equity = p.get("equity", "SPY")
    bond = p.get("bond", "IEF")
    lookback = p.get("lookback", 12)
    if equity not in px.columns or len(px) < lookback + 1:
        return pd.Series({equity: 0.5, bond: 0.5})
    pr = px[equity]
    peak = pr.iloc[-lookback:].max()
    dd = (pr.iloc[-1] / peak) - 1
    if dd < dd_thresh * 2:
        return pd.Series({equity: 0.0, bond: 1.0})
    elif dd < dd_thresh:
        return pd.Series({equity: 0.3, bond: 0.7})
    return pd.Series({equity: 1.0, bond: 0.0})


def wf_bond_rotation(px, d, p):
    lb = p["lookback"]
    bonds = _available(px, p["bonds"])
    top_n = p.get("top_n", 1)
    if len(px) <= lb or len(bonds) < 2:
        return _equal_weight(bonds)
    ret = px[bonds].iloc[-1] / px[bonds].iloc[-lb - 1] - 1
    ret = ret.dropna()
    if ret.empty:
        return _equal_weight(bonds)
    top = ret.nlargest(min(top_n, len(ret)))
    return pd.Series(1.0 / len(top), index=top.index)


def wf_relative_value(px, d, p):
    lb = p["lookback"]
    asset_a = p["asset_a"]
    asset_b = p["asset_b"]
    if asset_a not in px.columns or asset_b not in px.columns or len(px) <= lb:
        return pd.Series({asset_a: 0.5, asset_b: 0.5})
    ret_a = px[asset_a].iloc[-1] / px[asset_a].iloc[-lb - 1] - 1
    ret_b = px[asset_b].iloc[-1] / px[asset_b].iloc[-lb - 1] - 1
    if ret_a > ret_b:
        return pd.Series({asset_a: 1.0})
    return pd.Series({asset_b: 1.0})


def wf_multi_timeframe(px, d, p):
    short_lb = p.get("short_lb", 3)
    long_lb = p.get("long_lb", 12)
    short_wt = p.get("short_weight", 0.4)
    equity = p.get("equity", "SPY")
    bond = p.get("bond", "IEF")
    if equity not in px.columns or len(px) < long_lb + 1:
        return pd.Series({equity: 0.5, bond: 0.5})
    pr = px[equity]
    short_sig = float(pr.iloc[-1] / pr.iloc[-short_lb - 1] - 1 > 0)
    long_sig = float(pr.iloc[-1] / pr.iloc[-long_lb - 1] - 1 > 0)
    score = short_wt * short_sig + (1 - short_wt) * long_sig
    return pd.Series({equity: score, bond: 1 - score})


def wf_composite_macro(px, d, p):
    indicators = p["indicators"]
    equity = p.get("equity", "SPY")
    bond = p.get("bond", "IEF")
    total_weight = 0
    score = 0
    for macro, thresh, lag, wt in indicators:
        m = macro.loc[:d]
        if len(m) < lag + 2:
            continue
        val = m.iloc[-(lag + 1)]
        if pd.isna(val):
            continue
        total_weight += wt
        if val > thresh:
            score += wt
    if total_weight == 0:
        return pd.Series({equity: 0.5, bond: 0.5})
    frac = score / total_weight
    if frac >= 0.6:
        return pd.Series({equity: 1.0, bond: 0.0})
    elif frac <= 0.3:
        return pd.Series({equity: 0.0, bond: 1.0})
    return pd.Series({equity: 0.5, bond: 0.5})


def wf_vol_scaled_momentum(px, d, p):
    lb = p["lookback"]
    vol_window = p.get("vol_window", 6)
    assets = _available(px, p["assets"])
    top_n = p.get("top_n", 2)
    cash = p.get("cash")
    if len(px) <= max(lb, vol_window) or not assets:
        return _equal_weight(assets or ["SPY"])
    ret = px[assets].iloc[-1] / px[assets].iloc[-lb - 1] - 1
    vol = px[assets].pct_change().iloc[-vol_window:].std() * np.sqrt(12)
    vol = vol.replace(0, np.nan)
    score = (ret / vol).dropna()
    if cash and cash in px.columns and len(px[cash].dropna()) > lb:
        cash_ret = px[cash].iloc[-1] / px[cash].iloc[-lb - 1] - 1
        score = score[ret > cash_ret]
    if score.empty:
        return pd.Series({cash: 1.0}) if cash else _equal_weight(assets)
    top = score.nlargest(min(top_n, len(score)))
    top_vol = vol.reindex(top.index).dropna()
    if top_vol.empty:
        return pd.Series(1.0 / len(top), index=top.index)
    inv = 1.0 / top_vol
    return inv / inv.sum()


def wf_adaptive_momentum(px, d, p):
    short_lb = p.get("short_lb", 3)
    long_lb = p.get("long_lb", 12)
    vol_threshold = p.get("vol_threshold", 0.20)
    vol_window = p.get("vol_window", 6)
    equity = p.get("equity", "SPY")
    bond = p.get("bond", "IEF")
    if equity not in px.columns or len(px) < long_lb + 1:
        return pd.Series({equity: 0.5, bond: 0.5})
    realized_vol = px[equity].pct_change().iloc[-vol_window:].std() * np.sqrt(12)
    lb = short_lb if realized_vol > vol_threshold else long_lb
    ret = px[equity].iloc[-1] / px[equity].iloc[-lb - 1] - 1
    if ret > 0:
        return pd.Series({equity: 1.0, bond: 0.0})
    return pd.Series({equity: 0.0, bond: 1.0})


def wf_core_satellite(px, d, p):
    core_weight = p.get("core_weight", 0.6)
    core_assets = p["core"]
    satellite_assets = _available(px, p["satellite"])
    lb = p.get("lookback", 6)
    top_n = p.get("top_n", 1)
    w = {}
    for a, cw in core_assets.items():
        if a in px.columns:
            w[a] = cw * core_weight
    sat_weight = 1 - core_weight
    if len(px) > lb and satellite_assets:
        ret = px[satellite_assets].iloc[-1] / px[satellite_assets].iloc[-lb - 1] - 1
        ret = ret.dropna()
        top = ret.nlargest(min(top_n, len(ret)))
        top = top[top > 0]
        if not top.empty:
            per = sat_weight / len(top)
            for a in top.index:
                w[a] = w.get(a, 0) + per
        else:
            for a in core_assets:
                if a in px.columns:
                    w[a] = w.get(a, 0) + sat_weight * core_assets[a]
    else:
        for a in core_assets:
            if a in px.columns:
                w[a] = w.get(a, 0) + sat_weight * core_assets[a]
    return pd.Series(w)


def wf_roro(px, d, p):
    signals_cfg = p["signals"]
    equity = p.get("equity", "SPY")
    bond = p.get("bond", "IEF")
    threshold = p.get("threshold", 0.5)
    if equity not in px.columns or len(px) < 13:
        return pd.Series({equity: 0.5, bond: 0.5})
    votes = 0
    total = 0
    pr = px[equity]
    for sig_type, sig_p in signals_cfg:
        total += 1
        if sig_type == "trend":
            sma = sig_p.get("sma", 10)
            if len(pr) >= sma:
                votes += int(pr.iloc[-1] > pr.iloc[-sma:].mean())
        elif sig_type == "momentum":
            lb = sig_p.get("lb", 12)
            if len(pr) > lb:
                votes += int(pr.iloc[-1] / pr.iloc[-lb - 1] - 1 > 0)
        elif sig_type == "drawdown":
            lb = sig_p.get("lb", 12)
            thresh = sig_p.get("thresh", -0.10)
            if len(pr) >= lb:
                peak = pr.iloc[-lb:].max()
                votes += int((pr.iloc[-1] / peak - 1) > thresh)
        elif sig_type == "macro":
            macro = sig_p.get("data")
            thresh = sig_p.get("thresh", 50)
            lag = sig_p.get("lag", 1)
            if macro is not None:
                m = macro.loc[:d]
                if len(m) > lag + 1:
                    val = m.iloc[-(lag + 1)]
                    if not pd.isna(val):
                        votes += int(val > thresh)
    if total == 0:
        return pd.Series({equity: 0.5, bond: 0.5})
    frac = votes / total
    if frac >= threshold:
        return pd.Series({equity: 1.0, bond: 0.0})
    elif frac <= (1 - threshold):
        return pd.Series({equity: 0.0, bond: 1.0})
    return pd.Series({equity: 0.5, bond: 0.5})


def wf_cross_asset_rotation(px, d, p):
    lb = p["lookback"]
    assets = _available(px, p["assets"])
    top_n = p.get("top_n", 2)
    cash = p.get("cash")
    use_13612w = p.get("use_13612w", False)
    if len(px) < 13 or not assets:
        return _equal_weight(assets or ["SPY"])
    if use_13612w:
        pr = px[assets]
        r1 = pr.iloc[-1] / pr.iloc[-2] - 1
        r3 = pr.iloc[-1] / pr.iloc[-4] - 1 if len(pr) > 3 else r1
        r6 = pr.iloc[-1] / pr.iloc[-7] - 1 if len(pr) > 6 else r3
        r12 = pr.iloc[-1] / pr.iloc[-13] - 1 if len(pr) > 12 else r6
        score = 12 * r1 + 4 * r3 + 2 * r6 + r12
    else:
        if len(px) <= lb:
            return _equal_weight(assets)
        score = px[assets].iloc[-1] / px[assets].iloc[-lb - 1] - 1
    score = score.dropna()
    if cash and cash in px.columns and len(px[cash].dropna()) > (12 if use_13612w else lb):
        if use_13612w:
            c = px[cash]
            c_score = 12 * (c.iloc[-1]/c.iloc[-2]-1) + 4 * (c.iloc[-1]/c.iloc[-4]-1) + 2 * (c.iloc[-1]/c.iloc[-7]-1) + (c.iloc[-1]/c.iloc[-13]-1)
        else:
            c_score = px[cash].iloc[-1] / px[cash].iloc[-lb - 1] - 1
        score = score[score > c_score]
        if score.empty:
            return pd.Series({cash: 1.0})
    if score.empty:
        return pd.Series({cash: 1.0}) if cash else _equal_weight(assets)
    top = score.nlargest(min(top_n, len(score)))
    return pd.Series(1.0 / len(top), index=top.index)


def wf_trend_vol_filter(px, d, p):
    sma_lb = p.get("sma_months", 10)
    vol_window = p.get("vol_window", 6)
    vol_cap = p.get("vol_cap", 0.20)
    equity = p.get("equity", "SPY")
    bond = p.get("bond", "IEF")
    if equity not in px.columns or len(px) < max(sma_lb, vol_window) + 1:
        return pd.Series({equity: 0.5, bond: 0.5})
    pr = px[equity]
    trend_up = pr.iloc[-1] > pr.iloc[-sma_lb:].mean()
    realized_vol = pr.pct_change().iloc[-vol_window:].std() * np.sqrt(12)
    if not trend_up:
        return pd.Series({equity: 0.0, bond: 1.0})
    if realized_vol > vol_cap:
        scale = min(1.0, vol_cap / realized_vol)
        return pd.Series({equity: scale, bond: 1 - scale})
    return pd.Series({equity: 1.0, bond: 0.0})


def wf_equity_rotation(px, d, p):
    lb = p["lookback"]
    equities = _available(px, p["equities"])
    bond = p.get("bond", "IEF")
    sma_filter = p.get("sma_filter", 0)
    top_n = p.get("top_n", 1)
    if len(px) <= max(lb, sma_filter) or not equities:
        return pd.Series({bond: 1.0})
    ret = px[equities].iloc[-1] / px[equities].iloc[-lb - 1] - 1
    ret = ret.dropna()
    if sma_filter > 0:
        above_sma = [a for a in ret.index if px[a].iloc[-1] > px[a].iloc[-sma_filter:].mean()]
        ret = ret.reindex(above_sma)
    if ret.empty or (ret <= 0).all():
        return pd.Series({bond: 1.0})
    top = ret[ret > 0].nlargest(min(top_n, len(ret[ret > 0])))
    if top.empty:
        return pd.Series({bond: 1.0})
    return pd.Series(1.0 / len(top), index=top.index)


def wf_canary(px, d, p):
    canary = _available(px, p["canary"])
    offensive = _available(px, p["offensive"])
    defensive = _available(px, p["defensive"])
    off_top_n = p.get("off_top_n", 3)
    def_top_n = p.get("def_top_n", 2)
    if len(px) < 13 or not canary:
        return _equal_weight(offensive or defensive)

    def _13612w(pr):
        r1 = pr.iloc[-1] / pr.iloc[-2] - 1
        r3 = pr.iloc[-1] / pr.iloc[-4] - 1 if len(pr) > 3 else r1
        r6 = pr.iloc[-1] / pr.iloc[-7] - 1 if len(pr) > 6 else r3
        r12 = pr.iloc[-1] / pr.iloc[-13] - 1 if len(pr) > 12 else r6
        return 12 * r1 + 4 * r3 + 2 * r6 + r12

    crash_detected = False
    for a in canary:
        pr = px[a].dropna()
        if len(pr) < 13:
            continue
        if _13612w(pr) < 0:
            crash_detected = True
            break

    target = defensive if crash_detected else offensive
    top_n = def_top_n if crash_detected else off_top_n
    scores = {}
    for a in target:
        pr = px[a].dropna()
        if len(pr) < 13:
            continue
        scores[a] = _13612w(pr)
    if not scores:
        return _equal_weight(target)
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_n]
    w = 1.0 / len(ranked)
    return pd.Series({a: w for a, _ in ranked})


# ════════════════════════════════════════════════════════════════════
# CONFIG BUILDER
# ════════════════════════════════════════════════════════════════════

