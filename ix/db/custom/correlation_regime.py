from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series
from ix.core.transforms import StandardScalar


# ── Equity-Bond Correlation Regime ──────────────────────────────────────────


def equity_bond_corr_regime(window: int = 60, threshold: float = 0.0) -> pd.Series:
    """Equity-bond correlation regime classification.

    Positive correlation = 'stagflationary' regime (stocks and bonds fall together).
    Negative correlation = 'normal' regime (bonds hedge equities).
    Returns: 1 = positive corr (dangerous), -1 = negative corr (normal), 0 = neutral.
    """
    spx = Series("SPX INDEX:PX_LAST").pct_change()
    y10 = Series("TRYUS10Y:PX_YTM").diff()
    corr = spx.rolling(window).corr(y10).dropna()
    regime = pd.Series(0, index=corr.index, dtype=float)
    regime[corr > threshold] = 1
    regime[corr < -threshold] = -1
    regime.name = "Eq-Bond Corr Regime"
    return regime


def equity_bond_corr_zscore(window: int = 60) -> pd.Series:
    """Z-score of rolling equity-bond correlation.

    Extreme positive z-scores = correlation regime shift (rare, important).
    """
    spx = Series("SPX INDEX:PX_LAST").pct_change()
    y10 = Series("TRYUS10Y:PX_YTM").diff()
    corr = spx.rolling(window).corr(y10).dropna()
    s = StandardScalar(corr, 252)
    s.name = "Eq-Bond Corr Z-Score"
    return s.dropna()


# ── Cross-Asset Correlation Stress ──────────────────────────────────────────


def cross_asset_correlation(window: int = 60) -> pd.Series:
    """Average pairwise correlation across major asset classes.

    High correlation = "correlation crisis" (diversification fails).
    Low correlation = normal diversification benefits.
    Spikes to >0.5 historically mark systemic stress events.
    """
    assets = {
        "SPX": Series("SPX INDEX:PX_LAST"),
        "Bonds": Series("TLT US EQUITY:PX_LAST"),
        "Gold": Series("GOLDCOMP:PX_LAST"),
        "DXY": Series("DXY INDEX:PX_LAST"),
        "Commodities": Series("BCOM-CME:PX_LAST"),
        "VIX": Series("VIX INDEX:PX_LAST"),
    }
    # Filter out empty series
    rets = {}
    for name, s in assets.items():
        if not s.empty:
            rets[name] = s.pct_change().dropna()

    if len(rets) < 3:
        return pd.Series(dtype=float, name="Cross-Asset Correlation")

    df = pd.DataFrame(rets).dropna()

    # Rolling average pairwise correlation
    n = len(rets)
    pairs = [(i, j) for i in range(n) for j in range(i + 1, n)]
    cols = list(rets.keys())

    avg_corr = pd.Series(dtype=float)
    for idx in range(window, len(df)):
        sub = df.iloc[idx - window:idx]
        corr_matrix = sub.corr().values
        pair_corrs = [abs(corr_matrix[i][j]) for i, j in pairs]
        avg_corr.loc[df.index[idx]] = np.mean(pair_corrs)

    avg_corr.name = "Cross-Asset Avg Correlation"
    return avg_corr.dropna()


def cross_asset_correlation_fast(window: int = 60) -> pd.Series:
    """Fast version: average absolute correlation using expanding pairs.

    Uses SPX-TLT, SPX-Gold, SPX-DXY as key pairs.
    More efficient than full pairwise computation.
    """
    spx = Series("SPX INDEX:PX_LAST").pct_change()
    tlt = Series("TLT US EQUITY:PX_LAST").pct_change()
    gold = Series("GOLDCOMP:PX_LAST").pct_change()
    dxy = Series("DXY INDEX:PX_LAST").pct_change()

    pairs = []
    if not spx.empty and not tlt.empty:
        pairs.append(spx.rolling(window).corr(tlt).abs())
    if not spx.empty and not gold.empty:
        pairs.append(spx.rolling(window).corr(gold).abs())
    if not spx.empty and not dxy.empty:
        pairs.append(spx.rolling(window).corr(dxy).abs())
    if not tlt.empty and not gold.empty:
        pairs.append(tlt.rolling(window).corr(gold).abs())

    if not pairs:
        return pd.Series(dtype=float, name="Avg Abs Correlation")

    s = pd.concat(pairs, axis=1).mean(axis=1).dropna()
    s.name = "Avg Abs Correlation"
    return s


# ── Diversification Index ───────────────────────────────────────────────────


def diversification_index(window: int = 60) -> pd.Series:
    """Diversification benefit index (inverse of avg abs correlation).

    High = good diversification (correlations low).
    Low = poor diversification (everything moving together).
    100 = perfect diversification. 0 = perfect correlation.
    """
    corr = cross_asset_correlation_fast(window)
    s = ((1 - corr) * 100).dropna()
    s.name = "Diversification Index"
    return s


# ── Correlation Breakdown Detection ─────────────────────────────────────────


def correlation_surprise(window_short: int = 20, window_long: int = 252) -> pd.Series:
    """Correlation surprise: short-term vs long-term avg correlation.

    Positive = correlations spiking above normal (stress).
    Negative = correlations below normal (calm, good diversification).
    Large positive values mark systemic risk events.
    """
    short = cross_asset_correlation_fast(window_short)
    long_ = cross_asset_correlation_fast(window_long)
    s = (short - long_).dropna()
    s.name = "Correlation Surprise"
    return s


# ── Safe Haven Demand ───────────────────────────────────────────────────────


def safe_haven_demand(window: int = 20) -> pd.Series:
    """Safe haven demand index: gold + treasuries + yen vs equities + credit.

    Positive = safe haven assets outperforming (risk aversion).
    Negative = risk assets outperforming (risk appetite).
    """
    # Safe havens (rising = demand)
    gold = Series("GOLDCOMP:PX_LAST")
    tlt = Series("TLT US EQUITY:PX_LAST")

    # Risk assets (rising = risk-on)
    spx = Series("SPX INDEX:PX_LAST")

    haven_components = []
    if not gold.empty:
        haven_components.append(StandardScalar(gold.pct_change(window).dropna(), 252))
    if not tlt.empty:
        haven_components.append(StandardScalar(tlt.pct_change(window).dropna(), 252))

    risk_components = []
    if not spx.empty:
        risk_components.append(StandardScalar(spx.pct_change(window).dropna(), 252))

    if not haven_components or not risk_components:
        return pd.Series(dtype=float, name="Safe Haven Demand")

    haven = pd.concat(haven_components, axis=1).mean(axis=1)
    risk = pd.concat(risk_components, axis=1).mean(axis=1)
    s = (haven - risk).dropna()
    s.name = "Safe Haven Demand"
    return s


# ── Tail Risk Indicator ─────────────────────────────────────────────────────


def tail_risk_index(window: int = 20) -> pd.Series:
    """Composite tail risk indicator.

    Combines: VIX term structure (backwardation), SKEW index,
    equity-bond correlation shift, and credit stress.
    Higher = more tail risk priced. Useful for hedging timing.
    """
    components = {}

    # VIX backwardation (stress)
    vix = Series("VIX INDEX:PX_LAST")
    vix3m = Series("VIX3M INDEX:PX_LAST")
    if not vix.empty and not vix3m.empty:
        ts = -(vix3m - vix)  # Negative term spread = backwardation = stress
        components["VIX TS"] = StandardScalar(ts.dropna(), 252)

    # SKEW (tail risk pricing)
    skew = Series("SKEW INDEX:PX_LAST")
    if not skew.empty:
        components["SKEW"] = StandardScalar(skew.dropna(), 252)

    # Credit stress
    hy = Series("BAMLH0A0HYM2")
    if not hy.empty:
        components["Credit"] = StandardScalar(hy.dropna(), 252)

    # Equity-bond regime (positive corr = stress)
    spx = Series("SPX INDEX:PX_LAST").pct_change()
    y10 = Series("TRYUS10Y:PX_YTM").diff()
    if not spx.empty and not y10.empty:
        corr = spx.rolling(window).corr(y10).dropna()
        components["Eq-Bond Corr"] = StandardScalar(corr, 252)

    if not components:
        return pd.Series(dtype=float, name="Tail Risk Index")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Tail Risk Index"
    return s
