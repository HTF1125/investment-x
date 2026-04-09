from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series
from ix.common.data.transforms import StandardScalar


# ── Credit Stress Index ─────────────────────────────────────────────────────


def credit_stress_index(window: int = 120) -> pd.Series:
    """Composite credit stress index combining spread, curve, and vol signals.

    Aggregates z-scores of: HY spread, IG spread, HY-IG differential,
    VIX, and inverted 2s10s curve. Higher = more stress.
    """
    components = {}

    hy = Series("BAMLH0A0HYM2")
    if not hy.empty:
        components["HY Spread"] = StandardScalar(hy.dropna(), window)

    ig = Series("BAMLC0A4CBBB")
    if not ig.empty:
        components["IG Spread"] = StandardScalar(ig.dropna(), window)

    if not hy.empty and not ig.empty:
        components["HY-IG Diff"] = StandardScalar((hy - ig).dropna(), window)

    vix_s = Series("VIX INDEX:PX_LAST")
    if not vix_s.empty:
        components["VIX"] = StandardScalar(vix_s.dropna(), window)

    y2 = Series("TRYUS2Y:PX_YTM")
    y10 = Series("TRYUS10Y:PX_YTM")
    if not y2.empty and not y10.empty:
        # Inverted curve = more stress
        components["Inv Curve"] = -StandardScalar((y10 - y2).dropna(), window)

    if not components:
        return pd.Series(dtype=float, name="Credit Stress Index")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Credit Stress Index"
    return s


# ── Distress Ratio ──────────────────────────────────────────────────────────


def hy_distress_proxy(threshold: float = 7.0) -> pd.Series:
    """HY distress proxy: 1 when HY OAS exceeds threshold (%), 0 otherwise.

    Default threshold 7% (700bp) approximates when ~10%+ of HY market
    trades at distressed levels. Useful for marking credit crisis periods.
    """
    hy = Series("BAMLH0A0HYM2")
    if hy.empty:
        return pd.Series(dtype=float)
    s = (hy > threshold).astype(float)
    s.name = "HY Distress Signal"
    return s.dropna()


def hy_spread_momentum(window: int = 60) -> pd.Series:
    """HY spread change over window (bps).

    Positive = spreads widening (deteriorating). Negative = tightening (improving).
    Rapid widening (>100bp in 60 days) historically precedes equity drawdowns.
    """
    hy = Series("BAMLH0A0HYM2")
    if hy.empty:
        return pd.Series(dtype=float)
    s = hy.diff(window).dropna()
    s.name = f"HY Spread {window}d Change"
    return s


def hy_spread_velocity(short: int = 20, long: int = 120) -> pd.Series:
    """Rate of change of HY spread movement (velocity).

    Accelerating spread widening = credit market panic.
    Decelerating widening = stress may be peaking.
    """
    hy = Series("BAMLH0A0HYM2")
    if hy.empty:
        return pd.Series(dtype=float)
    short_chg = hy.diff(short)
    long_chg = hy.diff(long) / (long / short)
    s = (short_chg - long_chg).dropna()
    s.name = "HY Spread Velocity"
    return s


# ── Leveraged Loan Proxy ────────────────────────────────────────────────────


def leveraged_loan_spread() -> pd.Series:
    """Leveraged loan spread proxy from HY-IG differential.

    HY-IG spread captures the risk premium for sub-investment-grade credit.
    Widening signals stress in leveraged lending markets first
    (leveraged loans reprice faster than bonds due to floating rate).
    """
    hy = Series("BAMLH0A0HYM2")
    ig = Series("BAMLC0A4CBBB")
    if hy.empty or ig.empty:
        return pd.Series(dtype=float)
    s = (hy - ig).dropna()
    s.name = "Leveraged Loan Spread Proxy"
    return s


def leveraged_loan_spread_zscore(window: int = 252) -> pd.Series:
    """Z-score of leveraged loan spread proxy."""
    return StandardScalar(leveraged_loan_spread(), window)


# ── CDS Proxy ───────────────────────────────────────────────────────────────


def cdx_hy_proxy() -> pd.Series:
    """CDX HY proxy from BAML HY OAS (highly correlated, ~0.95+).

    BAML HY OAS is the best available proxy for CDX HY index levels
    when direct CDS index data is not available.
    """
    s = Series("BAMLH0A0HYM2")
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "CDX HY Proxy"
    return s.dropna()


def cdx_ig_proxy() -> pd.Series:
    """CDX IG proxy from BAML BBB OAS."""
    s = Series("BAMLC0A4CBBB")
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "CDX IG Proxy"
    return s.dropna()


# ── Credit Cycle Indicators ─────────────────────────────────────────────────


def credit_cycle_phase(window: int = 252) -> pd.Series:
    """Credit cycle phase indicator based on spread level and momentum.

    Combines spread z-score (level) with spread momentum (direction).
    Quadrants: Tightening (bullish), Tight (late-cycle), Widening (bearish),
    Wide (opportunity/recovery).
    Returns composite score: positive = improving, negative = deteriorating.
    """
    hy = Series("BAMLH0A0HYM2")
    if hy.empty:
        return pd.Series(dtype=float)
    level_z = StandardScalar(hy.dropna(), window)
    momentum = hy.diff(60)
    mom_z = StandardScalar(momentum.dropna(), window)
    # Invert both (lower spread / tightening = positive)
    s = -(level_z + mom_z).dropna() / 2
    s.name = "Credit Cycle Phase"
    return s


def sloos_lending_standards() -> pd.Series:
    """SLOOS: Net % of banks tightening C&I loan standards (large/medium firms).

    The Senior Loan Officer Opinion Survey is the Fed's quarterly gauge
    of bank credit availability.  Positive = net tightening.  Negative =
    net easing.

    Empirically leads recessions by ~12 months.  Persistent readings
    above +30% net tightening have preceded every recession since 1990.
    When banks tighten, credit-dependent capex and hiring slow.

    Publication lag: ~6 weeks after quarter-end (quarterly, ~144 pts).
    Source: Federal Reserve, FRED DRTSCILM.
    """
    s = Series("DRTSCILM")
    if s.empty:
        return pd.Series(dtype=float, name="SLOOS C&I Lending Standards")
    s.name = "SLOOS C&I Lending Standards"
    return s.dropna()


def sloos_credit_card_standards() -> pd.Series:
    """SLOOS: Net % of banks tightening credit card loan standards.

    Consumer credit channel — tightening here signals rising consumer
    default concerns and directly constrains household spending.

    Source: Federal Reserve, FRED DRTSCLCC.
    """
    s = Series("DRTSCLCC")
    if s.empty:
        return pd.Series(dtype=float, name="SLOOS Credit Card Standards")
    s.name = "SLOOS Credit Card Standards"
    return s.dropna()


def sloos_composite() -> pd.Series:
    """SLOOS lending standards composite: average of C&I Large, C&I Small,
    Consumer Credit Card, CRE.

    Positive = tightening (banks restricting credit).
    Negative = easing (banks loosening).
    >20 = recession warning. <0 = easy credit.
    Leads credit conditions by 2-3 quarters.

    Source: Federal Reserve Senior Loan Officer Survey
    """
    codes = {
        "C&I Large": "DRTSCILM",
        "C&I Small": "DRTSCIS",
        "Consumer CC": "DRTSCLCC",
        "CRE": "SUBLPDRCSC",
    }
    data = {}
    for label, code in codes.items():
        s = Series(code)
        if not s.empty:
            data[label] = s
    if not data:
        return pd.Series(dtype=float)
    df = pd.DataFrame(data).ffill()
    result = df.mean(axis=1)
    result.name = "SLOOS Composite"
    return result.dropna()


def ig_hy_compression() -> pd.Series:
    """IG-HY spread compression ratio (IG / HY).

    Rising = spreads compressing (risk appetite strong, HY tightening faster).
    Falling = spreads diverging (risk aversion, HY widening faster).
    Extreme compression often marks late-cycle risk-taking.
    """
    ig = Series("BAMLC0A4CBBB")
    hy = Series("BAMLH0A0HYM2")
    if ig.empty or hy.empty:
        return pd.Series(dtype=float)
    s = (ig / hy).dropna()
    s.name = "IG/HY Compression"
    return s


def financial_conditions_credit(window: int = 120) -> pd.Series:
    """Credit component of financial conditions.

    Combines BBB spread, HY spread, and bank credit growth into a single
    credit conditions measure. Negative = tight, Positive = easy.
    """
    bbb = Series("BAMLC0A4CBBB")
    hy = Series("BAMLH0A0HYM2")
    credit = Series("TOTBKCR")

    components = {}
    if not bbb.empty:
        components["BBB"] = -StandardScalar(bbb.dropna(), window)
    if not hy.empty:
        components["HY"] = -StandardScalar(hy.dropna(), window)
    if not credit.empty:
        credit_yoy = credit.pct_change(52).dropna()
        components["Credit Growth"] = StandardScalar(credit_yoy, window)

    if not components:
        return pd.Series(dtype=float, name="Credit Conditions")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Credit Conditions"
    return s
