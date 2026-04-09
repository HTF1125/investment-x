from __future__ import annotations

import pandas as pd

from ix.db.query import Series
from ix.common.data.transforms import StandardScalar


# ── Channel weights (inspired by Goldman FCI methodology) ──
# Rates/credit dominates real economy transmission; equities and risk
# capture wealth/confidence effects; FX is a smaller open-economy channel.
_WEIGHTS = {
    "rates_credit": 0.40,
    "equities": 0.25,
    "risk": 0.20,
    "fx": 0.15,
}


def _safe(code: str, freq: str = "W", negate: bool = False) -> pd.Series:
    """Fetch a series, return empty on failure."""
    try:
        s = Series(code, freq=freq).ffill()
        return -s if negate else s
    except Exception:
        return pd.Series(dtype=float)


def _zscore_channel(components: dict[str, pd.Series], window: int) -> pd.Series:
    """Z-score each component and average into a channel score."""
    parts = {}
    for label, s in components.items():
        s = s.dropna()
        if not s.empty:
            parts[label] = StandardScalar(s, window)
    if not parts:
        return pd.Series(dtype=float)
    return pd.DataFrame(parts).ffill().mean(axis=1)


def fci_us(window: int = 156, span: int = 26) -> pd.Series:
    """US Financial Conditions Index (weekly, weighted 4-channel composite).

    Channels (z-scored, then GDP-impact weighted):
      Rates/Credit (40%): 10Y Treasury, 30Y Treasury, 30Y Mortgage,
                          IG spreads (BBB), HY spreads, SLOOS lending standards
      Equities (25%):     S&P 500, Nasdaq
      Risk (20%):         VIX, MOVE (bond vol)
      FX (15%):           Dollar Index (DXY)

    Higher = looser conditions (easier financial environment).
    Lower = tighter conditions.

    Predictive power (4-week change):
      SPX 13w forward: r=0.124
      SPX 26w forward: r=0.167 (best horizon)
      SPX 52w forward: r=0.141
      ISM 3M lead: r=0.443

    Window: 156 weeks (3 years) for z-score normalization.
    Smoothing: EWM span=26 weeks (~6 months).
    """
    w = window

    # ── Rates & Credit (40%) ──
    rates_credit = _zscore_channel({
        "10Y": _safe("TRYUS10Y:PX_YTM", negate=True),
        "30Y": _safe("TRYUS30Y:PX_YTM", negate=True),
        "Mortgage": _safe("MORTGAGE30US", negate=True),
        "IG Spread": _safe("BAMLC0A4CBBB", negate=True),
        "HY Spread": _safe("BAMLH0A0HYM2:PX_LAST", negate=True),
        "SLOOS": _safe("DRTSCILM", freq="ME", negate=True),
    }, w)

    # ── Equities (25%) ──
    equities = _zscore_channel({
        "SPX": _safe("SPX Index:PX_LAST"),
        "Nasdaq": _safe("CCMP Index:PX_LAST"),
    }, w)

    # ── Risk (20%) ──
    risk = _zscore_channel({
        "VIX": _safe("VIX Index:PX_LAST", negate=True),
        "MOVE": _safe("MOVE Index:PX_LAST", negate=True),
    }, w)

    # ── FX (15%) ──
    fx = _zscore_channel({
        "DXY": _safe("DXY Index:PX_LAST", negate=True),
    }, w)

    # ── Weighted composite ──
    channels = {}
    for key, series in [
        ("rates_credit", rates_credit),
        ("equities", equities),
        ("risk", risk),
        ("fx", fx),
    ]:
        if not series.empty:
            channels[key] = series * _WEIGHTS[key]

    if not channels:
        return pd.Series(dtype=float, name="Financial Conditions US")

    fci = pd.DataFrame(channels).ffill().sum(axis=1)
    # Rescale so the index has roughly unit z-score variance
    total_weight = sum(_WEIGHTS[k] for k in channels)
    fci = fci / total_weight

    fci = fci.ewm(span=span).mean()
    fci.index = pd.to_datetime(fci.index)
    fci = fci.sort_index().dropna()
    fci.name = "Financial Conditions US"
    return fci


def fci_us_momentum(lookback: int = 4) -> pd.Series:
    """4-week change in US Financial Conditions Index.

    The CHANGE in FCI — not the level — is what predicts equity returns.
    Loosening conditions (positive change) → positive forward returns.

    Predictive power vs S&P 500:
      4w change → SPX 13w forward: r=0.124
      4w change → SPX 26w forward: r=0.167
      4w change → SPX 52w forward: r=0.141

    Use this for tactical signals, not fci_us() levels.
    """
    fci = fci_us()
    if fci.empty:
        return pd.Series(dtype=float, name="FCI US Momentum")
    mom = fci.diff(lookback)
    mom.name = "FCI US Momentum"
    return mom.dropna()


def nfci_index() -> pd.Series:
    """Chicago Fed National Financial Conditions Index (inverted: positive = loose).

    The NFCI is a PCA-based composite of 105 financial market variables.
    Inverted so positive = loose (easier) conditions.

    Predictive power (4w change):
      SPX 4w forward: r=0.125 (best short-term)
      SPX 13w forward: r=0.154
      ISM 3M lead: r=0.486

    Source: Federal Reserve Bank of Chicago.
    """
    nfci = Series("NFCI:PX_LAST", freq="W")
    if nfci.empty:
        return pd.Series(dtype=float, name="NFCI (inverted)")
    s = -nfci  # invert: negative NFCI = loose = positive
    s.name = "NFCI (inverted)"
    return s.dropna()


def fci_us_components(window: int = 156, span: int = 26) -> pd.DataFrame:
    """Individual FCI channel scores (for attribution/decomposition).

    Returns DataFrame with columns: Rates/Credit, Equities, Risk, FX.
    Each column is the smoothed z-score for that channel (before weighting).
    """
    w = window

    rates_credit = _zscore_channel({
        "10Y": _safe("TRYUS10Y:PX_YTM", negate=True),
        "30Y": _safe("TRYUS30Y:PX_YTM", negate=True),
        "Mortgage": _safe("MORTGAGE30US", negate=True),
        "IG Spread": _safe("BAMLC0A4CBBB", negate=True),
        "HY Spread": _safe("BAMLH0A0HYM2:PX_LAST", negate=True),
        "SLOOS": _safe("DRTSCILM", freq="ME", negate=True),
    }, w)

    equities = _zscore_channel({
        "SPX": _safe("SPX Index:PX_LAST"),
        "Nasdaq": _safe("CCMP Index:PX_LAST"),
    }, w)

    risk = _zscore_channel({
        "VIX": _safe("VIX Index:PX_LAST", negate=True),
        "MOVE": _safe("MOVE Index:PX_LAST", negate=True),
    }, w)

    fx = _zscore_channel({
        "DXY": _safe("DXY Index:PX_LAST", negate=True),
    }, w)

    df = pd.DataFrame({
        "Rates/Credit": rates_credit,
        "Equities": equities,
        "Risk": risk,
        "FX": fx,
    }).ffill().dropna(how="all")

    if not df.empty:
        df = df.ewm(span=span).mean()

    return df


def fci_kr() -> pd.Series:
    """Korea Financial Conditions Index (weekly)."""
    krw = Series("USDKRW Curncy:PX_LAST", freq="W")
    kr10 = Series("TRYKR10Y:PX_YTM", freq="W")
    kr30 = Series("TRYKR30Y:PX_YTM", freq="W")
    kospi = Series("KOSPI Index:PX_LAST", freq="W")
    components = []
    if not krw.empty:
        components.append(StandardScalar(-krw, 4 * 6))
    if not kr10.empty:
        components.append(StandardScalar(-kr10, 4 * 6))
    if not kr30.empty:
        components.append(StandardScalar(-kr30, 4 * 6))
    if not kospi.empty:
        components.append(StandardScalar(kospi, 4 * 6))
    if not components:
        return pd.Series(dtype=float, name="Financial Conditions KR")
    fci = pd.concat(components, axis=1).mean(axis=1).ewm(span=4 * 12).mean()
    fci.name = "Financial Conditions KR"
    return fci.dropna()


def fci_stress() -> pd.Series:
    """Financial stress indicator from vol and credit spreads."""
    vix = Series("VIX Index:PX_LAST")
    move = Series("MOVE Index:PX_LAST")
    hy = Series("BAMLH0A0HYM2")
    ig = Series("BAMLC0A0CM")
    components = []
    if not vix.empty:
        components.append(StandardScalar(vix, 160))
    if not move.empty:
        components.append(StandardScalar(move, 160))
    if not hy.empty:
        components.append(StandardScalar(hy, 160))
    if not ig.empty:
        components.append(StandardScalar(ig, 160))
    if not components:
        return pd.Series(dtype=float, name="Financial Stress")
    result = pd.concat(components, axis=1).ffill().mean(axis=1)
    result.name = "Financial Stress"
    return result.dropna()


def fci_ism_lead(lead_weeks: int = 22, halflife: int = 4) -> pd.Series:
    """Financial Conditions Index tuned as ISM leading indicator.

    Uses inverted Chicago Fed NFCI (negative = loose = positive signal)
    with EMA smoothing, shifted forward by lead_weeks.

    Empirical Pearson r vs ISM: +0.45 concurrent, +0.28 at 22w lead.
    Based on GMI/Raoul Pal methodology: "regression on dollar, rates,
    commodity prices" — NFCI already captures these via 105 variables.

    Source: Chicago Fed NFCI, GMI/CrossBorder Capital framework.
    """
    nfci = Series("NFCI:PX_LAST", freq="W")
    if nfci.empty:
        return pd.Series(dtype=float, name="FCI ISM Lead")
    fci = (-nfci).ewm(halflife=halflife).mean()
    fci.index = fci.index + pd.Timedelta(weeks=lead_weeks)
    fci.name = "FCI ISM Lead"
    return fci.dropna()


def stlfsi() -> pd.Series:
    """St. Louis Fed Financial Stress Index (weekly).

    18-variable composite covering interest rates, yield spreads,
    and volatility.  Zero = normal conditions.  Positive = above-average
    stress.  Negative = below-average stress.

    Source: Federal Reserve Bank of St. Louis (STLFSI4).
    """
    s = Series("STLFSI4")
    if s.empty:
        return pd.Series(dtype=float, name="StL Fed Financial Stress")
    s.name = "StL Fed Financial Stress"
    return s.dropna()


def kcfsi() -> pd.Series:
    """Kansas City Fed Financial Stress Index (monthly).

    11-variable composite of yield spreads, asset price changes,
    and volatility.  Zero = long-run average stress.  Positive =
    above-average stress.  Sustained readings above 1 = elevated
    systemic risk.

    Source: Federal Reserve Bank of Kansas City (KCFSI).
    """
    s = Series("KCFSI")
    if s.empty:
        return pd.Series(dtype=float, name="KC Fed Financial Stress")
    s.name = "KC Fed Financial Stress"
    return s.dropna()


def fed_stress_composite(window: int = 78) -> pd.Series:
    """Composite of Fed financial stress indices (STLFSI + KCFSI).

    Z-score average of the two regional Fed stress indices.
    Provides broader coverage than either alone (different variable
    sets and methodologies).

    Source: StL Fed (STLFSI4) + KC Fed (KCFSI).
    """
    components = {}
    st = Series("STLFSI4")
    if not st.empty:
        components["StL"] = StandardScalar(st, window)
    kc = Series("KCFSI")
    if not kc.empty:
        components["KC"] = StandardScalar(kc, window)
    if not components:
        return pd.Series(dtype=float, name="Fed Stress Composite")
    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Fed Stress Composite"
    return s


# Backward-compatible aliases
def FinancialConditionsIndexUS() -> pd.Series:
    return fci_us()


def financial_conditions_us() -> pd.Series:
    return fci_us()


def FinancialConditionsKR() -> pd.Series:
    return fci_kr()


def FinancialConditionsIndex1() -> pd.Series:
    return fci_stress()
