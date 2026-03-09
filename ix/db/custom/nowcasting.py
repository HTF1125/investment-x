from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series
from ix.core.transforms import StandardScalar


# ── GDPNow & Real-Time GDP Tracking ────────────────────────────────────────


def gdpnow() -> pd.Series:
    """Atlanta Fed GDPNow real-time GDP estimate.

    Updated ~weekly. Most accurate real-time GDP tracker available.
    Converges to actual GDP print as quarter progresses.
    """
    s = Series("GDPNOW")
    if s.empty:
        # Fallback: construct GDP proxy from ISM + employment
        s = _gdp_proxy()
    s.name = "GDPNow"
    return s.dropna()


def _gdp_proxy() -> pd.Series:
    """GDP growth proxy from ISM Manufacturing + Nonfarm Payrolls."""
    ism = Series("NAPM")  # ISM Manufacturing PMI
    nfp = Series("PAYEMS")  # Nonfarm Payrolls
    if ism.empty and nfp.empty:
        return pd.Series(dtype=float)
    components = {}
    if not ism.empty:
        components["ISM"] = StandardScalar(ism.dropna(), 120)
    if not nfp.empty:
        nfp_mom = nfp.pct_change(12) * 100
        components["NFP"] = StandardScalar(nfp_mom.dropna(), 120)
    return pd.DataFrame(components).mean(axis=1).dropna()


# ── Weekly Economic Index ───────────────────────────────────────────────────


def weekly_economic_index() -> pd.Series:
    """NY Fed Weekly Economic Index (WEI).

    High-frequency GDP proxy using 10 weekly/daily indicators.
    Scaled to 4-quarter GDP growth units. Updated weekly.
    """
    s = Series("WEI")
    s.name = "Weekly Economic Index"
    return s.dropna()


def wei_momentum(window: int = 13) -> pd.Series:
    """WEI momentum: change over ~1 quarter.

    Positive = economic activity accelerating.
    Negative = decelerating.
    """
    wei = weekly_economic_index()
    s = wei.diff(window).dropna()
    s.name = "WEI Momentum"
    return s


# ── ADS Business Conditions ─────────────────────────────────────────────────


def ads_business_conditions() -> pd.Series:
    """Aruoba-Diebold-Scotti Business Conditions Index (daily).

    Mean zero = average growth. Positive = above-trend. Negative = below-trend.
    Based on jobless claims, payrolls, industrial production, real GDP,
    real income, real manufacturing sales.
    """
    s = Series("ADSCI")
    s.name = "ADS Business Conditions"
    return s.dropna()


# ── High-Frequency Activity Proxies ─────────────────────────────────────────


def initial_claims(freq: str = "W") -> pd.Series:
    """Initial jobless claims — highest-frequency labor market indicator.

    Rising claims = labor market weakening (leading indicator).
    4-week MA smooths weekly noise.
    """
    s = Series("ICSA", freq=freq)
    s.name = "Initial Claims"
    return s.dropna()


def initial_claims_4wma() -> pd.Series:
    """4-week moving average of initial claims (smoothed)."""
    s = Series("IC4WSA")
    if s.empty:
        s = initial_claims().rolling(4).mean()
    s.name = "Initial Claims 4WMA"
    return s.dropna()


def continued_claims(freq: str = "W") -> pd.Series:
    """Continued (insured) unemployment claims."""
    s = Series("CCSA", freq=freq)
    s.name = "Continued Claims"
    return s.dropna()


def claims_ratio() -> pd.Series:
    """Continued / Initial claims ratio — duration of unemployment.

    Rising = unemployed staying jobless longer (structural weakness).
    Falling = quick reabsorption (healthy labor market).
    """
    initial = initial_claims()
    cont = continued_claims()
    df = pd.concat([initial, cont], axis=1).dropna()
    if df.empty or df.shape[1] < 2:
        return pd.Series(dtype=float, name="Claims Ratio")
    s = (df.iloc[:, 1] / df.iloc[:, 0]).dropna()
    s.name = "Claims Ratio"
    return s


# ── Industrial Production ───────────────────────────────────────────────────


def industrial_production_yoy(freq: str = "ME") -> pd.Series:
    """US Industrial Production YoY growth (%).

    Key coincident indicator of manufacturing activity.
    """
    ip = Series("INDPRO", freq=freq)
    s = ip.pct_change(12) * 100
    s.name = "Industrial Production YoY"
    return s.dropna()


def capacity_utilization(freq: str = "ME") -> pd.Series:
    """Capacity Utilization Rate (%).

    Above 80% = inflationary pressure. Below 75% = slack.
    """
    s = Series("TCU", freq=freq)
    s.name = "Capacity Utilization"
    return s.dropna()


# ── Composite Nowcast ───────────────────────────────────────────────────────


def nowcast_composite(window: int = 120) -> pd.Series:
    """Composite nowcasting index from available high-frequency data.

    Combines all available nowcasting signals into a single z-score.
    Positive = above-trend growth. Negative = below-trend.
    """
    components = {}

    wei = weekly_economic_index()
    if not wei.empty:
        components["WEI"] = StandardScalar(wei, window)

    ads = ads_business_conditions()
    if not ads.empty:
        components["ADS"] = StandardScalar(ads, window)

    claims = initial_claims()
    if not claims.empty:
        # Invert — lower claims = better
        components["Claims"] = -StandardScalar(claims, window)

    ip = Series("INDPRO")
    if not ip.empty:
        ip_yoy = ip.pct_change(12).dropna()
        components["IP"] = StandardScalar(ip_yoy, window)

    if not components:
        return pd.Series(dtype=float, name="Nowcast Composite")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Nowcast Composite"
    return s
