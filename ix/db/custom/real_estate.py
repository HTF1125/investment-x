from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series, MultiSeries
from ix.core.transforms import StandardScalar


# ── Home Prices ────────────────────────────────────────────────────────────


def case_shiller_yoy(freq: str = "ME") -> pd.Series:
    """Case-Shiller US National Home Price Index YoY (%).

    Wealth effect driver. Each 10% home price gain adds ~0.3pp
    to consumer spending growth. Leads consumer confidence.
    Lags mortgage rates by 6-12 months.
    """
    cs = Series("CSUSHPINSA", freq=freq)
    s = cs.pct_change(12) * 100
    s.name = "Case-Shiller YoY"
    return s.dropna()


def case_shiller_momentum(window: int = 3) -> pd.Series:
    """Case-Shiller 3-month annualized rate (%).

    Turns faster than YoY. Captures inflection points in housing
    price cycle 6-9 months before the annual rate.
    """
    cs = Series("CSUSHPINSA")
    s = cs.pct_change(window).mul(12 / window).mul(100).dropna()
    s.name = "Home Price Momentum"
    return s


# ── Housing Activity ───────────────────────────────────────────────────────


def existing_home_sales(freq: str = "ME") -> pd.Series:
    """Existing Home Sales (millions, SAAR).

    Volume of housing transactions. Drives broker commissions,
    mortgage originations, home improvement spending.
    Below 4M = frozen market. Above 5.5M = healthy.
    """
    s = Series("EXHOSLUSM495S", freq=freq)
    if not s.empty:
        s = s / 1e6  # Convert to millions
    s.name = "Existing Home Sales (M)"
    return s.dropna()


def existing_home_sales_yoy(freq: str = "ME") -> pd.Series:
    """Existing Home Sales YoY (%)."""
    ehs = Series("EXHOSLUSM495S", freq=freq)
    s = ehs.pct_change(12) * 100
    s.name = "Existing Home Sales YoY"
    return s.dropna()


def new_home_sales(freq: str = "ME") -> pd.Series:
    """New Single-Family Home Sales (thousands, SAAR).

    Leading indicator vs existing — contracts signed, not closed.
    More forward-looking for construction activity.
    """
    s = Series("HSN1F", freq=freq)
    s.name = "New Home Sales"
    return s.dropna()


# ── Builder Confidence ─────────────────────────────────────────────────────


def nahb_housing_market_index(freq: str = "ME") -> pd.Series:
    """NAHB/Wells Fargo Housing Market Index.

    Builder confidence. Leads housing starts by 1-3 months.
    Above 50 = positive conditions. Below 50 = contraction.
    """
    s = Series("NAHBHMI", freq=freq)
    if s.empty:
        s = Series("HOUSINGNSA", freq=freq)
    s.name = "NAHB HMI"
    return s.dropna()


# ── Commercial Real Estate ─────────────────────────────────────────────────


def commercial_real_estate_price(freq: str = "QE") -> pd.Series:
    """Commercial Real Estate Price Index YoY (%).

    CRE stress indicator. Post-2022 office segment under extreme
    pressure from remote work. Watch for contagion to regional banks.
    """
    cre = Series("COMREPUSQ159N", freq=freq)
    if cre.empty:
        return pd.Series(dtype=float, name="CRE Price YoY")
    s = cre.pct_change(4) * 100
    s.name = "CRE Price YoY"
    return s.dropna()


# ── Mortgage Market ────────────────────────────────────────────────────────


def mortgage_purchase_index(freq: str = "W") -> pd.Series:
    """MBA Mortgage Purchase Application Index.

    High-frequency housing demand signal. Purchase applications
    (not refinancing) reflect genuine buyer demand.
    """
    s = Series("MPURNSA", freq=freq)
    if s.empty:
        s = Series("MORTAPPW", freq=freq)
    s.name = "Mortgage Purchase Index"
    return s.dropna()


def mortgage_purchase_yoy() -> pd.Series:
    """MBA Purchase Applications YoY (%)."""
    mpi = mortgage_purchase_index()
    if mpi.empty:
        return pd.Series(dtype=float, name="Purchase Apps YoY")
    s = mpi.pct_change(52) * 100
    s.name = "Purchase Apps YoY"
    return s.dropna()


# ── Composite ──────────────────────────────────────────────────────────────


def housing_composite(window: int = 120) -> pd.Series:
    """Housing sector composite index.

    Combines prices, activity, and affordability into a single
    z-scored signal. Positive = housing strength.
    """
    components = {}

    cs = Series("CSUSHPINSA")
    if not cs.empty:
        cs_yoy = cs.pct_change(12).dropna()
        components["Prices"] = StandardScalar(cs_yoy, window)

    starts = Series("HOUST")
    if not starts.empty:
        starts_yoy = starts.pct_change(12).dropna()
        components["Starts"] = StandardScalar(starts_yoy, window)

    permits = Series("PERMIT")
    if not permits.empty:
        permits_yoy = permits.pct_change(12).dropna()
        components["Permits"] = StandardScalar(permits_yoy, window)

    # Mortgage rate inverted (lower rate = better for housing)
    mort = Series("MORTGAGE30US")
    if not mort.empty:
        components["Rates"] = -StandardScalar(mort.dropna(), window)

    if not components:
        return pd.Series(dtype=float, name="Housing Composite")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Housing Composite"
    return s
