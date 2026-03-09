from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series
from ix.core.transforms import StandardScalar


# ── Semiconductor Cycle ─────────────────────────────────────────────────────


def sox_index(freq: str = "W") -> pd.Series:
    """Philadelphia Semiconductor Index (SOX).

    Leading indicator for tech sector and global growth.
    Semi cycle leads capex cycle by 6-12 months.
    """
    s = Series("SOX INDEX:PX_LAST", freq=freq)
    s.name = "SOX Index"
    return s.dropna()


def sox_spx_ratio(freq: str = "W") -> pd.Series:
    """SOX / SPX relative performance.

    Rising = semi cycle strengthening (early/mid-cycle).
    Falling = semi cycle weakening (late-cycle warning).
    """
    sox = Series("SOX INDEX:PX_LAST", freq=freq)
    spx = Series("SPX INDEX:PX_LAST", freq=freq)
    s = (sox / spx).dropna()
    s.name = "SOX/SPX Ratio"
    return s


def sox_momentum(window: int = 60) -> pd.Series:
    """SOX index momentum (% change over window).

    > +20% in 60d = strong semi upcycle.
    < -20% in 60d = potential semi downturn.
    """
    sox = Series("SOX INDEX:PX_LAST")
    s = sox.pct_change(window).dropna() * 100
    s.name = "SOX Momentum"
    return s


def semi_book_to_bill() -> pd.Series:
    """Semiconductor book-to-bill proxy from SOX momentum vs earnings.

    Uses SOX relative to its 200-day MA as cycle indicator.
    > 1 = expansion phase. < 1 = contraction phase.
    """
    sox = Series("SOX INDEX:PX_LAST")
    ma200 = sox.rolling(200).mean()
    s = (sox / ma200).dropna()
    s.name = "Semi Book/Bill Proxy"
    return s


# ── Housing Market ──────────────────────────────────────────────────────────


def housing_starts(freq: str = "ME") -> pd.Series:
    """US Housing Starts (thousands, SAAR).

    Leading indicator for construction, materials, employment.
    Above 1.5M = healthy. Below 1.0M = recession territory.
    """
    s = Series("HOUST", freq=freq)
    s.name = "Housing Starts"
    return s.dropna()


def housing_starts_yoy(freq: str = "ME") -> pd.Series:
    """Housing starts year-over-year change (%)."""
    hs = Series("HOUST", freq=freq)
    s = hs.pct_change(12) * 100
    s.name = "Housing Starts YoY"
    return s.dropna()


def building_permits(freq: str = "ME") -> pd.Series:
    """US Building Permits (thousands, SAAR).

    Leads housing starts by 1-2 months. More forward-looking.
    """
    s = Series("PERMIT", freq=freq)
    s.name = "Building Permits"
    return s.dropna()


def housing_affordability_proxy() -> pd.Series:
    """Housing affordability proxy: 30Y mortgage rate x median home price index.

    Rising = worsening affordability (headwind for housing).
    Uses Case-Shiller as home price proxy and MORTGAGE30US for rates.
    """
    mortgage = Series("MORTGAGE30US")
    cs = Series("CSUSHPINSA")  # Case-Shiller US National Home Price
    if mortgage.empty or cs.empty:
        return pd.Series(dtype=float, name="Housing Affordability")
    df = pd.concat([mortgage, cs], axis=1).ffill().dropna()
    s = (df.iloc[:, 0] * df.iloc[:, 1] / df.iloc[:, 1].iloc[0]).dropna()
    s.name = "Housing Affordability Index"
    return s


def mortgage_rate(freq: str = "W") -> pd.Series:
    """30-Year Fixed Mortgage Rate (%).

    Key driver of housing demand. Each 1% increase reduces
    affordability by ~10% of purchasing power.
    """
    s = Series("MORTGAGE30US", freq=freq)
    s.name = "30Y Mortgage Rate"
    return s.dropna()


# ── Energy Markets ──────────────────────────────────────────────────────────


def wti_crude(freq: str = "D") -> pd.Series:
    """WTI Crude Oil price (USD/barrel)."""
    s = Series("CL1 COMB Comdty:PX_LAST", freq=freq)
    if s.empty:
        s = Series("DCOILWTICO", freq=freq)  # FRED WTI
    s.name = "WTI Crude"
    return s.dropna()


def brent_crude(freq: str = "D") -> pd.Series:
    """Brent Crude Oil price (USD/barrel)."""
    s = Series("CO1 COMB Comdty:PX_LAST", freq=freq)
    if s.empty:
        s = Series("DCOILBRENTEU", freq=freq)  # FRED Brent
    s.name = "Brent Crude"
    return s.dropna()


def crack_spread() -> pd.Series:
    """3-2-1 crack spread proxy (gasoline margin).

    Proxy: WTI oil price momentum. Direct crack spread requires
    gasoline futures data. Rising crack spread = refinery margins healthy.
    Uses WTI vs gasoline differential when available.
    """
    wti = Series("CL1 COMB Comdty:PX_LAST")
    if wti.empty:
        wti = Series("DCOILWTICO")
    gasoline = Series("XB1 COMB Comdty:PX_LAST")  # RBOB Gasoline
    if gasoline.empty:
        # Return WTI momentum as proxy
        s = wti.pct_change(20).dropna() * 100
        s.name = "Energy Margin Proxy"
        return s
    # 3-2-1 crack: 2*gasoline + 1*heating_oil - 3*crude / 3
    # Simplified: gasoline - crude spread
    s = (gasoline * 42 - wti).dropna()  # Convert gallons to barrels
    s.name = "Crack Spread"
    return s


def oil_inventory_proxy(window: int = 52) -> pd.Series:
    """Oil inventory proxy from price curve structure.

    Uses WTI price relative to its moving average as contango/backwardation proxy.
    When price > MA: backwardation (tight supply). Price < MA: contango (surplus).
    """
    wti = Series("CL1 COMB Comdty:PX_LAST")
    if wti.empty:
        wti = Series("DCOILWTICO")
    if wti.empty:
        return pd.Series(dtype=float, name="Oil Inventory Proxy")
    ma = wti.rolling(window).mean()
    s = ((wti / ma) - 1).dropna() * 100
    s.name = "Oil Inventory Proxy"
    return s


def natural_gas(freq: str = "D") -> pd.Series:
    """Henry Hub Natural Gas price (USD/MMBtu)."""
    s = Series("NG1 COMB Comdty:PX_LAST", freq=freq)
    if s.empty:
        s = Series("DHHNGSP", freq=freq)  # FRED Natural Gas
    s.name = "Natural Gas"
    return s.dropna()


# ── Precious Metals ─────────────────────────────────────────────────────────


def gold(freq: str = "D") -> pd.Series:
    """Gold spot price (USD/oz)."""
    s = Series("GOLDCOMP:PX_LAST", freq=freq)
    s.name = "Gold"
    return s.dropna()


def gold_silver_ratio(freq: str = "W") -> pd.Series:
    """Gold / Silver ratio — fear gauge and economic cycle indicator.

    Rising (>80) = risk aversion / recession fears.
    Falling (<60) = risk appetite / industrial recovery.
    """
    gold_s = Series("GOLDCOMP:PX_LAST", freq=freq)
    silver = Series("SILVER CURNCY:PX_LAST", freq=freq)
    if silver.empty:
        silver = Series("XAG CURNCY:PX_LAST", freq=freq)
    if gold_s.empty or silver.empty:
        return pd.Series(dtype=float, name="Gold/Silver Ratio")
    s = (gold_s / silver).dropna()
    s.name = "Gold/Silver Ratio"
    return s


def gold_real_rate_relationship(window: int = 120) -> pd.Series:
    """Rolling correlation of gold vs real rates.

    Normally negative (gold rises when real rates fall).
    When correlation breaks, it signals regime shift in inflation expectations.
    """
    gold_s = Series("GOLDCOMP:PX_LAST").pct_change()
    real_rate = Series("DFII10")  # FRED 10Y TIPS yield
    if real_rate.empty:
        y10 = Series("TRYUS10Y:PX_YTM")
        be = Series("T10YIE")  # FRED 10Y breakeven
        if y10.empty or be.empty:
            return pd.Series(dtype=float, name="Gold-Real Rate Corr")
        real_rate = (y10 - be).dropna()
    rr_chg = real_rate.diff()
    s = gold_s.rolling(window).corr(rr_chg).dropna()
    s.name = "Gold-Real Rate Corr"
    return s


# ── Shipping / Trade ────────────────────────────────────────────────────────


def baltic_dry_momentum(window: int = 20) -> pd.Series:
    """Baltic Dry Index momentum (% change).

    BDI leads global trade by 2-3 months.
    Sharp moves signal commodity demand shifts.
    """
    bdi = Series("BDI-BAX:PX_LAST")
    s = bdi.pct_change(window).dropna() * 100
    s.name = "BDI Momentum"
    return s


def container_freight_proxy(freq: str = "W") -> pd.Series:
    """Container freight proxy from BDI (correlated ~0.6 with container rates).

    BDI tracks dry bulk, but trends correlate with container rates
    as both respond to global trade volume.
    """
    bdi = Series("BDI-BAX:PX_LAST", freq=freq)
    s = StandardScalar(bdi.dropna(), 52)
    s.name = "Container Freight Proxy"
    return s.dropna()


# ── Composite Alt Data Index ────────────────────────────────────────────────


def alt_data_composite(window: int = 120) -> pd.Series:
    """Alternative data composite index.

    Combines semiconductor cycle, housing, energy, and shipping
    into a single growth proxy from non-traditional data.
    """
    components = {}

    sox = sox_spx_ratio()
    if not sox.empty:
        mom = sox.pct_change(13).dropna()
        components["Semi Cycle"] = StandardScalar(mom, window)

    hs = Series("HOUST")
    if not hs.empty:
        hs_yoy = hs.pct_change(12).dropna()
        components["Housing"] = StandardScalar(hs_yoy, window)

    bdi = Series("BDI-BAX:PX_LAST")
    if not bdi.empty:
        bdi_mom = bdi.pct_change(26).dropna()
        components["Shipping"] = StandardScalar(bdi_mom, window)

    copper = Series("COPPER CURNCY:PX_LAST")
    if not copper.empty:
        cu_mom = copper.pct_change(60).dropna()
        components["Copper"] = StandardScalar(cu_mom, window)

    if not components:
        return pd.Series(dtype=float, name="Alt Data Composite")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Alt Data Composite"
    return s
