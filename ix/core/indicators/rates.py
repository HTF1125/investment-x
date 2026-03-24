from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series, MultiSeries
from ix.core.transforms import StandardScalar


# ── US Rates & Spreads ──────────────────────────────────────────────────────


# ── Yield Curve ──────────────────────────────────────────────────────────────

def us_2s10s() -> pd.Series:
    """US 2s10s yield curve spread (10Y - 2Y)."""
    spread = Series("FRNTRSYLD100") - Series("FRNTRSYLD020")
    if spread.empty:
        return pd.Series(dtype=float)
    spread.name = "US 2s10s"
    return spread.dropna()


def us_3m10y() -> pd.Series:
    """US 3m10y yield curve spread (10Y - 3M)."""
    spread = Series("TRYUS10Y:PX_YTM") - Series("TRYUS3M:PX_YTM")
    if spread.empty:
        return pd.Series(dtype=float)
    spread.name = "US 3m10y"
    return spread.dropna()


def us_2s30s() -> pd.Series:
    """US 2s30s yield curve spread (30Y - 2Y)."""
    spread = Series("FRNTRSYLD300") - Series("FRNTRSYLD020")
    if spread.empty:
        return pd.Series(dtype=float)
    spread.name = "US 2s30s"
    return spread.dropna()


def kr_2s10s() -> pd.Series:
    """Korea 2s10s yield curve spread."""
    spread = Series("BONDAVG01@10Y:PX_YTM") - Series("BONDAVG01@2Y:PX_YTM")
    if spread.empty:
        return pd.Series(dtype=float)
    spread.name = "KR 2s10s"
    return spread.dropna()


# ── Yield Curve Inversion Duration ────────────────────────────────────────────


def yield_curve_inversion_duration() -> pd.Series:
    """Cumulative business days the 2s10s curve has been inverted.

    Counts consecutive days with 10Y - 2Y < 0.  Resets to 0 when the
    curve un-inverts.  Duration matters more than the initial inversion:
    inversions lasting <3 months predict recessions only ~45% of the time,
    while those >3 months jump to ~73%.

    The 2022-2024 inversion lasted ~500 business days — the longest on
    record — yet no recession materialized, likely due to post-COVID
    structural distortions (fiscal stimulus, labor hoarding).

    Use as a recession watch input alongside Sahm Rule and SLOOS.
    Crossing ~60 trading days (~3 months) is the empirical warning level.

    Source: Computed from US 2s10s yield curve (FRNTRSYLD100 - FRNTRSYLD020).
    """
    spread = Series("FRNTRSYLD100") - Series("FRNTRSYLD020")
    if spread.empty:
        return pd.Series(dtype=float, name="Inversion Duration (days)")

    inverted = (spread < 0).astype(int)
    # Cumulative count that resets on un-inversion
    groups = (inverted != inverted.shift()).cumsum()
    duration = inverted.groupby(groups).cumsum()
    duration.name = "Inversion Duration (days)"
    return duration.dropna()


def yield_curve_inversion_depth() -> pd.Series:
    """Cumulative depth of 2s10s inversion (bp-days).

    Sum of daily inversion magnitude during each inversion episode.
    Captures both duration AND severity — a deep, long inversion
    accumulates more bp-days than a shallow, short one.

    Resets to 0 when curve un-inverts.

    Source: Computed from US 2s10s yield curve.
    """
    spread = Series("FRNTRSYLD100") - Series("FRNTRSYLD020")
    if spread.empty:
        return pd.Series(dtype=float, name="Inversion Depth (bp-days)")

    # Only accumulate when inverted (spread < 0)
    inv_magnitude = spread.clip(upper=0).abs() * 100  # convert to bps
    groups = ((spread >= 0) != (spread.shift() >= 0)).cumsum()
    depth = inv_magnitude.groupby(groups).cumsum()
    # Zero out non-inverted periods
    depth[spread >= 0] = 0
    depth.name = "Inversion Depth (bp-days)"
    return depth.dropna()


# ── Real Rates ───────────────────────────────────────────────────────────────

def us_10y_real() -> pd.Series:
    """US 10Y TIPS real yield."""
    s = Series("FRNTIPYLD010")
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "US 10Y Real Yield"
    return s.dropna()


def us_10y_breakeven() -> pd.Series:
    """US 10Y breakeven inflation (nominal - TIPS)."""
    bei = Series("FRNTRSYLD100") - Series("FRNTIPYLD010")
    if bei.empty:
        return pd.Series(dtype=float)
    bei.name = "US 10Y Breakeven"
    return bei.dropna()


# ── Credit Spreads ───────────────────────────────────────────────────────────

def hy_spread() -> pd.Series:
    """ICE BofA US High Yield OAS."""
    s = Series("BAMLH0A0HYM2")
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "US HY OAS"
    return s.dropna()


def ig_spread() -> pd.Series:
    """ICE BofA US Investment Grade OAS."""
    s = Series("BAMLC0A0CM")
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "US IG OAS"
    return s.dropna()


def bbb_spread() -> pd.Series:
    """ICE BofA BBB US Corporate OAS."""
    s = Series("BAMLC0A4CBBB")
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "US BBB OAS"
    return s.dropna()


def hy_ig_ratio() -> pd.Series:
    """HY/IG spread ratio — rises in stress."""
    hy = Series("BAMLH0A0HYM2")
    ig = Series("BAMLC0A0CM")
    if hy.empty or ig.empty:
        return pd.Series(dtype=float)
    ratio = (hy / ig).dropna()
    ratio.name = "HY/IG Ratio"
    return ratio


def spread_zscore(window: int = 252) -> pd.DataFrame:
    """Rolling z-scores of HY, IG, BBB spreads."""
    hy = Series("BAMLH0A0HYM2")
    ig = Series("BAMLC0A0CM")
    bbb = Series("BAMLC0A4CBBB")
    data = {}
    if not hy.empty:
        data["HY"] = hy
    if not ig.empty:
        data["IG"] = ig
    if not bbb.empty:
        data["BBB"] = bbb
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data).dropna()
    if df.empty:
        return pd.DataFrame()
    roll = df.rolling(window)
    return df.sub(roll.mean()).div(roll.std()).dropna()


# ── Risk Appetite ────────────────────────────────────────────────────────────

def risk_appetite(window: int = 160) -> pd.Series:
    """Risk appetite index: inverted average z-score of vol + spreads.

    Higher = more risk appetite (tighter spreads, lower vol).
    """
    vix = Series("VIX INDEX:PX_LAST")
    move = Series("MOVE INDEX:PX_LAST")
    hy = Series("BAMLH0A0HYM2")
    ig = Series("BAMLC0A0CM")
    components = []
    if not vix.empty:
        components.append(StandardScalar(vix, window))
    if not move.empty:
        components.append(StandardScalar(move, window))
    if not hy.empty:
        components.append(StandardScalar(hy, window))
    if not ig.empty:
        components.append(StandardScalar(ig, window))
    if not components:
        return pd.Series(dtype=float, name="Risk Appetite")
    result = -pd.concat(components, axis=1).ffill().mean(axis=1)
    result.name = "Risk Appetite"
    return result.dropna()


# ── Monetary Policy (merged from monetary_policy.py) ────────────────────────


def rate_cut_expectations() -> pd.Series:
    """Expected rate change over next 12 months (bps).

    (100 - FF1) gives implied current policy rate.
    (100 - FF12) gives implied rate 12 months ahead.
    Difference: positive = market pricing cuts; negative = pricing hikes.
    Multiplied by 100 to express in basis points.
    """
    ff1 = Series("FF1 Comdty:PX_LAST")
    ff12 = Series("FF12 Comdty:PX_LAST")
    if ff1.empty or ff12.empty:
        return pd.Series(dtype=float)
    s = ((ff1 - ff12) * 100).dropna()
    s.name = "Rate Cut Expectations (bps)"
    return s


def rate_expectations_momentum(window: int = 20) -> pd.Series:
    """Velocity of repricing in rate expectations (bps change over window).

    Fast move toward cuts (positive momentum) historically precedes
    equity rallies. Fast move toward hikes precedes risk-off.
    """
    s = rate_cut_expectations().diff(window)
    s.name = "Rate Expectations Momentum"
    return s.dropna()


def rate_expectations_zscore(window: int = 252) -> pd.Series:
    """Z-score of rate cut expectations vs trailing distribution.

    Extreme readings mark inflection points for risk assets.
    """
    return StandardScalar(rate_cut_expectations(), window)


def term_premium_proxy() -> pd.Series:
    """Term premium proxy: 10Y yield minus implied 12M policy rate (%).

    Compensation for duration risk beyond rate expectations.
    Rising with stable rate expectations = bond supply concern.
    Falling = flight to quality or QE expectations.
    """
    y10 = Series("TRYUS10Y:PX_YTM")
    ff12 = Series("FF12 Comdty:PX_LAST")
    if y10.empty or ff12.empty:
        return pd.Series(dtype=float)
    implied_rate = 100 - ff12
    s = (y10 - implied_rate).dropna()
    s.name = "Term Premium Proxy"
    return s


def policy_rate_level() -> pd.Series:
    """Implied current policy rate from FF1 (%).

    100 - FF1 price. Tracks the effective Fed Funds rate.
    """
    ff1 = Series("FF1 Comdty:PX_LAST")
    if ff1.empty:
        return pd.Series(dtype=float)
    s = (100 - ff1).dropna()
    s.name = "Implied Policy Rate"
    return s


# ── Global Rates ────────────────────────────────────────────────────────────


# ── Major Sovereign Yields ─────────────────────────────────────────────────


def german_10y(freq: str = "D") -> pd.Series:
    """German 10Y Bund Yield (%).

    European rate benchmark. Risk-free rate for Eurozone.
    Negative yields (pre-2022) were historic anomaly.
    """
    s = Series("GDBR10 INDEX:PX_LAST", freq=freq)
    if s.empty:
        s = Series("IRLTLT01DEM156N", freq=freq)  # FRED German 10Y
    s.name = "German 10Y"
    return s.dropna()


def japan_10y(freq: str = "D") -> pd.Series:
    """Japan 10Y JGB Yield (%).

    BOJ yield curve control anchor. Movements above/below
    YCC band signal major policy shifts. Carry trade driver.
    """
    s = Series("TRYJP10Y:PX_YTM", freq=freq)
    if s.empty:
        s = Series("IRLTLT01JPM156N", freq=freq)  # FRED Japan 10Y
    s.name = "Japan 10Y"
    return s.dropna()


def uk_10y(freq: str = "D") -> pd.Series:
    """UK 10Y Gilt Yield (%).

    Gilt market stress indicator. 2022 gilt crisis showed
    how fast sovereign bond markets can destabilize.
    """
    s = Series("GUKG10 INDEX:PX_LAST", freq=freq)
    if s.empty:
        s = Series("IRLTLT01GBM156N", freq=freq)  # FRED UK 10Y
    s.name = "UK 10Y Gilt"
    return s.dropna()


# ── Sovereign Spreads ──────────────────────────────────────────────────────


def us_germany_spread(freq: str = "D") -> pd.Series:
    """US 10Y - German 10Y Bund spread (pp).

    Capital flow / USD direction signal. Widening = USD strength
    (US rates more attractive). Narrowing = EUR recovery.
    """
    us10 = Series("TRYUS10Y:PX_YTM", freq=freq)
    if us10.empty:
        us10 = Series("DGS10", freq=freq)
    de10 = german_10y(freq=freq)
    if us10.empty or de10.empty:
        return pd.Series(dtype=float, name="US-DE Spread")
    s = (us10 - de10).dropna()
    s.name = "US-DE 10Y Spread"
    return s


def us_japan_spread(freq: str = "D") -> pd.Series:
    """US 10Y - Japan 10Y JGB spread (pp).

    Carry trade profitability. Widening = stronger yen carry trade
    incentive. Rapid narrowing = carry unwind risk (JPY squeeze).
    """
    us10 = Series("TRYUS10Y:PX_YTM", freq=freq)
    if us10.empty:
        us10 = Series("DGS10", freq=freq)
    jp10 = japan_10y(freq=freq)
    if us10.empty or jp10.empty:
        return pd.Series(dtype=float, name="US-JP Spread")
    s = (us10 - jp10).dropna()
    s.name = "US-JP 10Y Spread"
    return s


# ── Global Rate Convergence ────────────────────────────────────────────────


def g4_yield_dispersion(window: int = 60) -> pd.Series:
    """G4 (US, Germany, UK, Japan) 10Y yield standard deviation.

    Measures global rate divergence. Rising = monetary policy
    divergence (USD strength). Falling = convergence (coordinated easing).
    """
    us10 = Series("TRYUS10Y:PX_YTM")
    if us10.empty:
        us10 = Series("DGS10")
    de10 = german_10y()
    uk10 = uk_10y()
    jp10 = japan_10y()

    df = pd.concat([us10, de10, uk10, jp10], axis=1).ffill().dropna()
    if df.empty or df.shape[1] < 3:
        return pd.Series(dtype=float, name="G4 Yield Dispersion")
    s = df.rolling(window).std().mean(axis=1).dropna()
    s.name = "G4 Yield Dispersion"
    return s


def global_real_rate_composite() -> pd.Series:
    """Simple global real rate proxy: US 10Y real + Germany real + Japan real.

    Uses inflation-adjusted yields where available.
    Rising global real rates = tightening financial conditions.
    Falling = accommodative (risk-on).
    """
    us_real = Series("DFII10")  # US TIPS
    if us_real.empty:
        us10 = Series("DGS10")
        bei = Series("T10YIE")
        if not us10.empty and not bei.empty:
            us_real = (us10 - bei).dropna()
    if us_real.empty:
        return pd.Series(dtype=float, name="Global Real Rate")

    # For Germany and Japan, subtract inflation proxies
    de10 = german_10y()
    de_cpi = Series("FPCPITOTLZGDEU")  # Germany CPI YoY
    jp10 = japan_10y()
    jp_cpi = Series("FPCPITOTLZGJPN")  # Japan CPI YoY

    components = {"US": us_real}
    if not de10.empty and not de_cpi.empty:
        df_de = pd.concat([de10, de_cpi], axis=1).ffill().dropna()
        if not df_de.empty:
            components["DE"] = df_de.iloc[:, 0] - df_de.iloc[:, 1]
    if not jp10.empty and not jp_cpi.empty:
        df_jp = pd.concat([jp10, jp_cpi], axis=1).ffill().dropna()
        if not df_jp.empty:
            components["JP"] = df_jp.iloc[:, 0] - df_jp.iloc[:, 1]

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Global Real Rate"
    return s


# ── EM Sovereign ───────────────────────────────────────────────────────────


def term_premium_10y() -> pd.Series:
    """Adrian-Crump-Moench 10Y Treasury Term Premium.

    Decomposes 10Y yield into expected short rates + term premium.
    Rising term premium = fiscal concerns / supply pressure.
    Falling = flight to safety / duration demand.

    Source: NY Fed ACM Model (THREEFYTP10)
    """
    s = Series("THREEFYTP10:PX_LAST")
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "10Y Term Premium"
    return s.dropna()


def embi_spread(freq: str = "D") -> pd.Series:
    """EMBI+ Spread proxy (EM sovereign risk premium, bps).

    EM sovereign stress aggregate. Widening = EM crisis risk.
    Uses BofA EM sovereign OAS or FRED proxy.
    """
    s = Series("BAMEMHBHYCRSP", freq=freq)
    if s.empty:
        s = Series("BAMEMOBCRSP", freq=freq)
    s.name = "EMBI Spread"
    return s.dropna()


def embi_spread_zscore(window: int = 252) -> pd.Series:
    """Z-scored EMBI spread for stress regime detection."""
    spread = embi_spread()
    if spread.empty:
        return pd.Series(dtype=float, name="EMBI Z-Score")
    s = StandardScalar(spread, window)
    s.name = "EMBI Z-Score"
    return s.dropna()
