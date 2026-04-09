from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series, MultiSeries
from ix.common.data.transforms import StandardScalar


# ── Semiconductors & Alt Data ─────────────────────────────────────────────


# ── Semiconductor Cycle ─────────────────────────────────────────────────────


def sox_index(freq: str = "W") -> pd.Series:
    """Philadelphia Semiconductor Index (SOX).

    Leading indicator for tech sector and global growth.
    Semi cycle leads capex cycle by 6-12 months.
    """
    s = Series("SOX INDEX:PX_LAST", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "SOX Index"
    return s.dropna()


def sox_spx_ratio(freq: str = "W") -> pd.Series:
    """SOX / SPX relative performance.

    Rising = semi cycle strengthening (early/mid-cycle).
    Falling = semi cycle weakening (late-cycle warning).
    """
    sox = Series("SOX INDEX:PX_LAST", freq=freq)
    spx = Series("SPX INDEX:PX_LAST", freq=freq)
    if sox.empty or spx.empty:
        return pd.Series(dtype=float)
    s = (sox / spx).dropna()
    s.name = "SOX/SPX Ratio"
    return s


def sox_momentum(window: int = 60) -> pd.Series:
    """SOX index momentum (% change over window).

    > +20% in 60d = strong semi upcycle.
    < -20% in 60d = potential semi downturn.
    """
    sox = Series("SOX INDEX:PX_LAST")
    if sox.empty:
        return pd.Series(dtype=float)
    s = sox.pct_change(window).dropna() * 100
    s.name = "SOX Momentum"
    return s


def semi_book_to_bill() -> pd.Series:
    """Semiconductor book-to-bill proxy from SOX momentum vs earnings.

    Uses SOX relative to its 200-day MA as cycle indicator.
    > 1 = expansion phase. < 1 = contraction phase.
    """
    sox = Series("SOX INDEX:PX_LAST")
    if sox.empty:
        return pd.Series(dtype=float)
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
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "Housing Starts"
    return s.dropna()


def housing_starts_yoy(freq: str = "ME") -> pd.Series:
    """Housing starts year-over-year change (%)."""
    hs = Series("HOUST", freq=freq)
    if hs.empty:
        return pd.Series(dtype=float)
    s = hs.pct_change(12) * 100
    s.name = "Housing Starts YoY"
    return s.dropna()


def building_permits(freq: str = "ME") -> pd.Series:
    """US Building Permits (thousands, SAAR).

    Leads housing starts by 1-2 months. More forward-looking.
    """
    s = Series("PERMIT", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
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
    if s.empty:
        return pd.Series(dtype=float)
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
    if s.empty:
        return pd.Series(dtype=float)
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


def gold_oil_ratio(freq: str = "W") -> pd.Series:
    """Gold / WTI crude oil ratio (barrels per ounce).

    Rising = gold outperforming energy (deflation/risk-off).
    Falling = energy outperforming gold (reflation/growth).
    Historical norm ~15-25x; current ~45x is historically elevated.
    """
    g = Series("GOLDCOMP:PX_LAST", freq=freq)
    oil = Series("WTI:PX_LAST", freq=freq)
    if g.empty or oil.empty:
        return pd.Series(dtype=float)
    s = (g / oil).dropna()
    s.name = "Gold/Oil Ratio"
    return s


def gold_spx_ratio(freq: str = "W") -> pd.Series:
    """S&P 500 / Gold ratio — equity valuation relative to gold.

    Falling = gold outperforming equities (risk-off, debasement).
    FTSE Russell: ratio at decade low in 2026 correction.
    """
    spx = Series("SPX INDEX:PX_LAST", freq=freq)
    g = Series("GOLDCOMP:PX_LAST", freq=freq)
    if spx.empty or g.empty:
        return pd.Series(dtype=float)
    s = (spx / g).dropna()
    s.name = "S&P 500 / Gold"
    return s


def gold_bitcoin_correlation(window: int = 90) -> pd.Series:
    """Rolling correlation between gold and bitcoin daily returns.

    Positive = "digital gold" narrative active.
    Negative = decoupled regimes (gold=haven, BTC=risk asset).
    Post-2022: correlation went to -0.17, breaking digital gold thesis.
    """
    g = Series("GOLDCOMP:PX_LAST")
    btc = Series("XBTUSD CURNCY:PX_LAST")
    if g.empty or btc.empty:
        return pd.Series(dtype=float)
    df = pd.DataFrame({"g": g.pct_change(), "btc": btc.pct_change()}).dropna()
    if len(df) < window:
        return pd.Series(dtype=float)
    s = df["g"].rolling(window).corr(df["btc"]).dropna()
    s.name = f"Gold-BTC Corr ({window}d)"
    return s


def gold_etf_flows(freq: str = "W") -> pd.Series:
    """Cumulative gold ETF flows (GLD + IAU).

    Rising = institutional accumulation.
    9 consecutive positive months through Feb 2026.
    Tracks structural demand momentum.
    """
    gld = Series("GLD US EQUITY:FUND_FLOW", freq=freq)
    iau = Series("IAU US EQUITY:FUND_FLOW", freq=freq)
    if gld.empty and iau.empty:
        return pd.Series(dtype=float)
    combined = pd.DataFrame({"gld": gld, "iau": iau}).fillna(0).sum(axis=1)
    s = combined.cumsum().dropna()
    s.name = "Gold ETF Flows (Cumulative)"
    return s


# ── Shipping / Trade ────────────────────────────────────────────────────────


def baltic_dry_momentum(window: int = 20) -> pd.Series:
    """Baltic Dry Index momentum (% change).

    BDI leads global trade by 2-3 months.
    Sharp moves signal commodity demand shifts.
    """
    bdi = Series("BDI-BAX:PX_LAST")
    if bdi.empty:
        return pd.Series(dtype=float)
    s = bdi.pct_change(window).dropna() * 100
    s.name = "BDI Momentum"
    return s


def container_freight_proxy(freq: str = "W") -> pd.Series:
    """Container freight proxy from BDI (correlated ~0.6 with container rates).

    BDI tracks dry bulk, but trends correlate with container rates
    as both respond to global trade volume.
    """
    bdi = Series("BDI-BAX:PX_LAST", freq=freq)
    if bdi.empty:
        return pd.Series(dtype=float)
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


# ── AI Capex Tracking (merged from capex.py) ────────────────────────────────

AI_CAPEX_TICKERS = "Nvdia=NVDA,Google=GOOG,Microsoft=MSFT,Amazon=AMZN,Meta=META"


def _ai_capex_multi(field: str) -> pd.DataFrame:
    codes = [c.strip() for c in AI_CAPEX_TICKERS.split(",")]
    series_list = []
    for code in codes:
        if "=" in code:
            alias, real_code = code.split("=", maxsplit=1)
            s = Series(f"{real_code}:{field}", freq="B")
            s.name = alias
        else:
            s = Series(f"{code}:{field}", freq="B")
        if not s.empty:
            series_list.append(s)
    if not series_list:
        return pd.DataFrame()
    return pd.concat(series_list, axis=1).ffill().dropna()


def ai_capex_ntma() -> pd.DataFrame:
    return _ai_capex_multi("FE_CAPEX_NTMA")


def ai_capex_ltma() -> pd.DataFrame:
    return _ai_capex_multi("FE_CAPEX_LTMA")


def ai_capex_q() -> pd.DataFrame:
    return _ai_capex_multi("FE_CAPEX_Q")


def ai_capex_qoq() -> pd.DataFrame:
    return (
        ai_capex_q().dropna().resample("W-Fri").last().pct_change(52).mul(100)
    )


def ai_capex_total_qoq() -> pd.DataFrame:
    return (
        ai_capex_q()
        .sum(axis=1)
        .dropna()
        .resample("W-Fri")
        .last()
        .pct_change(52)
        .mul(100)
    )


def ai_capex_total_yoy() -> pd.DataFrame:
    ntma = ai_capex_ntma().sum(axis=1).dropna().resample("W-Fri").last()
    ltma = ai_capex_ltma().sum(axis=1).dropna().resample("W-Fri").last()
    data = (ntma / ltma - 1).mul(100)
    data.name = "YoY"
    return data


# ── Energy Infrastructure ─────────────────────────────────────────────────


# ── Rig Counts ─────────────────────────────────────────────────────────────


def us_rig_count(freq: str = "W") -> pd.Series:
    """Baker Hughes US Total Rig Count.

    Energy supply response to prices. Rising rigs = future supply
    increase. Falling rigs = future supply tightening.
    Lags oil prices by 4-6 months.
    """
    s = Series("ROUSTCNT:PX_LAST", freq=freq)
    if s.empty:
        s = Series("BARONE", freq=freq)
    s.name = "US Rig Count"
    return s.dropna()


def us_rig_count_momentum(window: int = 13) -> pd.Series:
    """Rig count change over ~1 quarter.

    Positive = drillers adding rigs (bullish on oil price).
    Negative = pullback (bearish signal for energy sector).
    """
    rigs = us_rig_count()
    if rigs.empty:
        return pd.Series(dtype=float, name="Rig Count Momentum")
    s = rigs.diff(window).dropna()
    s.name = "Rig Count Momentum"
    return s


# ── Strategic Petroleum Reserve ────────────────────────────────────────────


def strategic_petroleum_reserve(freq: str = "W") -> pd.Series:
    """US Strategic Petroleum Reserve (million barrels).

    Government supply buffer. 2022 drawdown was historic
    (~180M bbl release). Refilling creates price floor.
    Low SPR = less buffer for future price shocks.
    """
    s = Series("WTTSTUS1", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "SPR (M bbl)"
    return s.dropna()


def spr_change(window: int = 13) -> pd.Series:
    """SPR quarterly change (million barrels).

    Negative = government selling (adding supply, capping prices).
    Positive = refilling (adding demand, supporting prices).
    """
    spr = strategic_petroleum_reserve()
    if spr.empty:
        return pd.Series(dtype=float, name="SPR Change")
    s = spr.diff(window).dropna()
    s.name = "SPR Change"
    return s


# ── Crude Inventories ──────────────────────────────────────────────────────


def crude_inventories(freq: str = "W") -> pd.Series:
    """US Crude Oil Inventories excl SPR (million barrels).

    Supply/demand balance. Rising inventories = oversupply.
    Falling inventories = tight market.
    """
    s = Series("WCESTUS1", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "Crude Inventories"
    return s.dropna()


def crude_inventories_zscore(window: int = 52) -> pd.Series:
    """Z-scored crude inventories for supply regime detection.

    > 1 sigma = glut conditions. < -1 sigma = tight market.
    """
    inv = crude_inventories()
    if inv.empty:
        return pd.Series(dtype=float, name="Inventory Z-Score")
    s = StandardScalar(inv, window)
    s.name = "Inventory Z-Score"
    return s.dropna()


def crude_inventory_change(window: int = 4) -> pd.Series:
    """Crude inventory weekly change (million barrels).

    Surprise builds/draws move oil prices intraday.
    Persistent direction signals supply/demand imbalance.
    """
    inv = crude_inventories()
    if inv.empty:
        return pd.Series(dtype=float, name="Inventory Change")
    s = inv.diff(window).dropna()
    s.name = "Inventory Change"
    return s


# ── Natural Gas Storage ────────────────────────────────────────────────────


def natural_gas_storage(freq: str = "W") -> pd.Series:
    """US Natural Gas Storage (Bcf).

    Seasonal pattern: injections (Apr-Oct), withdrawals (Nov-Mar).
    Deviation from 5-year average drives price moves.
    """
    s = Series("NGTMPUS", freq=freq)
    if s.empty:
        s = Series("NATURALGAS", freq=freq)
    s.name = "NG Storage"
    return s.dropna()


def natural_gas_storage_zscore(window: int = 52) -> pd.Series:
    """Z-scored natural gas storage vs rolling history."""
    ng = natural_gas_storage()
    if ng.empty:
        return pd.Series(dtype=float, name="NG Storage Z-Score")
    s = StandardScalar(ng, window)
    s.name = "NG Storage Z-Score"
    return s.dropna()


# ── Energy Supply Composite ───────────────────────────────────────────────


def energy_supply_composite(window: int = 52) -> pd.Series:
    """Energy supply conditions composite.

    Combines rig counts, inventories, and SPR into a single signal.
    Positive = ample supply. Negative = tight supply (bullish prices).
    """
    components = {}

    inv = crude_inventories()
    if not inv.empty:
        components["Crude Inv"] = StandardScalar(inv, window)

    rigs = us_rig_count()
    if not rigs.empty:
        components["Rigs"] = StandardScalar(rigs, window)

    spr = strategic_petroleum_reserve()
    if not spr.empty:
        components["SPR"] = StandardScalar(spr, window)

    if not components:
        return pd.Series(dtype=float, name="Energy Supply Composite")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Energy Supply Composite"
    return s


# ── Real Estate ───────────────────────────────────────────────────────────


# ── Home Prices ────────────────────────────────────────────────────────────


def case_shiller_yoy(freq: str = "ME") -> pd.Series:
    """Case-Shiller US National Home Price Index YoY (%).

    Wealth effect driver. Each 10% home price gain adds ~0.3pp
    to consumer spending growth. Leads consumer confidence.
    Lags mortgage rates by 6-12 months.
    """
    cs = Series("CSUSHPINSA", freq=freq)
    if cs.empty:
        return pd.Series(dtype=float)
    s = cs.pct_change(12) * 100
    s.name = "Case-Shiller YoY"
    return s.dropna()


def case_shiller_momentum(window: int = 3) -> pd.Series:
    """Case-Shiller 3-month annualized rate (%).

    Turns faster than YoY. Captures inflection points in housing
    price cycle 6-9 months before the annual rate.
    """
    cs = Series("CSUSHPINSA")
    if cs.empty:
        return pd.Series(dtype=float)
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
    if ehs.empty:
        return pd.Series(dtype=float)
    s = ehs.pct_change(12) * 100
    s.name = "Existing Home Sales YoY"
    return s.dropna()


def new_home_sales(freq: str = "ME") -> pd.Series:
    """New Single-Family Home Sales (thousands, SAAR).

    Leading indicator vs existing — contracts signed, not closed.
    More forward-looking for construction activity.
    """
    s = Series("HSN1F", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
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


# ── Housing Composite ────────────────────────────────────────────────────


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


# ── Transportation ────────────────────────────────────────────────────────


# ── Trucking ───────────────────────────────────────────────────────────────


def truck_tonnage(freq: str = "ME") -> pd.Series:
    """ATA Truck Tonnage Index.

    70% of US freight moves by truck. Strong coincident indicator
    of real economic activity. Tonnage declines precede GDP
    contractions.
    """
    s = Series("TRFVOLUSM227NFWA", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "Truck Tonnage"
    return s.dropna()


def truck_tonnage_yoy(freq: str = "ME") -> pd.Series:
    """Truck Tonnage YoY (%)."""
    tt = Series("TRFVOLUSM227NFWA", freq=freq)
    if tt.empty:
        return pd.Series(dtype=float)
    s = tt.pct_change(12) * 100
    s.name = "Truck Tonnage YoY"
    return s.dropna()


# ── Rail ───────────────────────────────────────────────────────────────────


def rail_freight(freq: str = "ME") -> pd.Series:
    """Railroad Freight Carloads proxy.

    Industrial activity proxy. Intermodal = consumer goods.
    Carloads = raw materials (coal, chemicals, lumber).
    Falling carloads = industrial slowdown.
    """
    s = Series("RAILFRTCARLOADSD11", freq=freq)
    if s.empty:
        s = Series("RAIL", freq=freq)
    s.name = "Rail Freight"
    return s.dropna()


def rail_freight_yoy(freq: str = "ME") -> pd.Series:
    """Rail freight YoY (%)."""
    rail = rail_freight()
    if rail.empty:
        return pd.Series(dtype=float, name="Rail Freight YoY")
    s = rail.pct_change(12) * 100
    s.name = "Rail Freight YoY"
    return s.dropna()


# ── Air Travel ─────────────────────────────────────────────────────────────


def air_passengers(freq: str = "ME") -> pd.Series:
    """Air Revenue Passenger-Miles (millions).

    Consumer spending/travel proxy. Strong seasonal patterns.
    YoY comparison smooths seasonality.
    """
    s = Series("AIRRPMTSID11", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "Air Passengers"
    return s.dropna()


def air_passengers_yoy(freq: str = "ME") -> pd.Series:
    """Air passenger-miles YoY (%)."""
    air = Series("AIRRPMTSID11", freq=freq)
    if air.empty:
        return pd.Series(dtype=float)
    s = air.pct_change(12) * 100
    s.name = "Air Passengers YoY"
    return s.dropna()


# ── Vehicle Sales ──────────────────────────────────────────────────────────


def vehicle_sales(freq: str = "ME") -> pd.Series:
    """Total Vehicle Sales (millions, SAAR).

    Big-ticket consumer spending barometer.
    Above 17M = strong. Below 14M = recessionary.
    Sensitive to interest rates and credit availability.
    """
    s = Series("TOTALSA", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "Vehicle Sales (M)"
    return s.dropna()


def vehicle_sales_yoy(freq: str = "ME") -> pd.Series:
    """Vehicle Sales YoY (%)."""
    vs = Series("TOTALSA", freq=freq)
    if vs.empty:
        return pd.Series(dtype=float)
    s = vs.pct_change(12) * 100
    s.name = "Vehicle Sales YoY"
    return s.dropna()


# ── Transport Composite ──────────────────────────────────────────────────


def real_economy_transport_composite(window: int = 120) -> pd.Series:
    """Physical economy composite from transportation data.

    Combines trucking, rail, air, and vehicle sales.
    Positive = expanding real activity. Negative = contracting.
    """
    components = {}

    tt = Series("TRFVOLUSM227NFWA")
    if not tt.empty:
        tt_yoy = tt.pct_change(12).dropna()
        components["Trucks"] = StandardScalar(tt_yoy, window)

    rail = rail_freight()
    if not rail.empty:
        rail_yoy = rail.pct_change(12).dropna()
        components["Rail"] = StandardScalar(rail_yoy, window)

    vs = Series("TOTALSA")
    if not vs.empty:
        vs_yoy = vs.pct_change(12).dropna()
        components["Vehicles"] = StandardScalar(vs_yoy, window)

    air = Series("AIRRPMTSID11")
    if not air.empty:
        air_yoy = air.pct_change(12).dropna()
        components["Air"] = StandardScalar(air_yoy, window)

    if not components:
        return pd.Series(dtype=float, name="Transport Composite")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Transport Composite"
    return s


# ── Baker Hughes Rig Count (granular) ────────────────────────────────────


def baker_hughes_total() -> pd.Series:
    """Baker Hughes US Total Rig Count.

    Total active drilling rigs in the US (oil + gas + misc).
    Rising rigs = future supply increase. Lags oil prices by 4-6 months.

    Source: Baker Hughes (BHRRIG@US).
    """
    s = Series("BHRRIG@US")
    if s.empty:
        return pd.Series(dtype=float, name="Baker Hughes Total Rigs")
    s.name = "Baker Hughes Total Rigs"
    return s.dropna()


def baker_hughes_oil() -> pd.Series:
    """Baker Hughes US Oil Rig Count.

    Active oil-directed rigs. More relevant than total for crude
    supply outlook. Tracks WTI breakeven economics.

    Source: Baker Hughes (BHRRIGOIL@US).
    """
    s = Series("BHRRIGOIL@US")
    if s.empty:
        return pd.Series(dtype=float, name="Baker Hughes Oil Rigs")
    s.name = "Baker Hughes Oil Rigs"
    return s.dropna()


def baker_hughes_gas() -> pd.Series:
    """Baker Hughes US Gas Rig Count.

    Active gas-directed rigs. Tracks natural gas supply response
    to Henry Hub prices.

    Source: Baker Hughes (BHRRIGGAS@US).
    """
    s = Series("BHRRIGGAS@US")
    if s.empty:
        return pd.Series(dtype=float, name="Baker Hughes Gas Rigs")
    s.name = "Baker Hughes Gas Rigs"
    return s.dropna()


def baker_hughes_oil_gas_ratio() -> pd.Series:
    """Baker Hughes oil rigs / gas rigs ratio.

    Rising = drillers favoring oil over gas (higher oil returns).
    Falling = gas drilling more attractive (cheap oil or expensive gas).

    Source: Baker Hughes (BHRRIGOIL@US / BHRRIGGAS@US).
    """
    oil = Series("BHRRIGOIL@US")
    gas = Series("BHRRIGGAS@US")
    if oil.empty or gas.empty:
        return pd.Series(dtype=float, name="Oil/Gas Rig Ratio")
    s = (oil / gas).replace([np.inf, -np.inf], np.nan).dropna()
    s.name = "Oil/Gas Rig Ratio"
    return s


# ── Mortgage Rates (FactSet) ─────────────────────────────────────────────


def mortgage_rate_30y() -> pd.Series:
    """US 30-Year Fixed Rate Mortgage average (%).

    Primary driver of housing affordability. Each 1% increase
    reduces purchasing power by ~10%.

    Source: Freddie Mac / FactSet (USIR0008775).
    """
    s = Series("USIR0008775")
    if s.empty:
        return pd.Series(dtype=float, name="30Y Mortgage Rate")
    s.name = "30Y Mortgage Rate"
    return s.dropna()


def mortgage_rate_15y() -> pd.Series:
    """US 15-Year Fixed Rate Mortgage average (%).

    Typically ~50-75bp below the 30Y rate. Preferred by
    refinancers and borrowers with higher equity.

    Source: Freddie Mac / FactSet (USIR0008777).
    """
    s = Series("USIR0008777")
    if s.empty:
        return pd.Series(dtype=float, name="15Y Mortgage Rate")
    s.name = "15Y Mortgage Rate"
    return s.dropna()


def mortgage_spread() -> pd.Series:
    """30Y mortgage rate minus 10Y Treasury yield spread.

    Measures credit/prepayment risk premium in mortgage market.
    Rising = tightening mortgage credit conditions or MBS stress.
    Normal range: 150-200bp. Above 250bp = stressed.

    Source: USIR0008775 minus 10Y Treasury.
    """
    mort = Series("USIR0008775")
    tsy = Series("TRYUS10Y:PX_YTM")
    if mort.empty or tsy.empty:
        return pd.Series(dtype=float, name="Mortgage-Treasury Spread")
    s = (mort - tsy).dropna()
    s.name = "Mortgage-Treasury Spread"
    return s


# ── Henry Hub Natural Gas (spot) ─────────────────────────────────────────


def henry_hub_spot() -> pd.Series:
    """Henry Hub Natural Gas spot price (USD/MMBtu).

    Benchmark US natural gas price. Seasonal demand patterns
    (winter heating, summer cooling). Structural shifts from
    LNG exports and renewable displacement.

    Source: FactSet (HHGAS-FDS:FG_PRICE).
    """
    s = Series("HHGAS-FDS:FG_PRICE")
    if s.empty:
        return pd.Series(dtype=float, name="Henry Hub Spot")
    s.name = "Henry Hub Spot"
    return s.dropna()


# ── CRB Raw Industrials ─────────────────────────────────────────────────


def crb_raw_industrials() -> pd.Series:
    """CRB Raw Industrials Index.

    Basket of industrial commodity prices (metals, fibers, fats/oils).
    Leading indicator for PPI and manufacturing input costs.
    No energy component — purer industrial demand signal.

    Source: CRB / FactSet (USCM1020424).
    """
    s = Series("USCM1020424")
    if s.empty:
        return pd.Series(dtype=float, name="CRB Raw Industrials")
    s.name = "CRB Raw Industrials"
    return s.dropna()


def crb_raw_industrials_yoy() -> pd.Series:
    """CRB Raw Industrials Index year-over-year change (%).

    Positive = rising industrial commodity prices (inflationary).
    Negative = falling prices (deflationary / demand weakness).

    Source: CRB / FactSet (USCM1020424).
    """
    s = Series("USCM1020424")
    if s.empty:
        return pd.Series(dtype=float, name="CRB Raw Industrials YoY")
    yoy = s.pct_change(12) * 100
    yoy.name = "CRB Raw Industrials YoY"
    return yoy.dropna()


# ── Precious Metals (spot) ───────────────────────────────────────────────


def silver_spot() -> pd.Series:
    """Silver spot price (USD/oz).

    Dual role: precious metal (monetary hedge) and industrial metal
    (solar panels, electronics). More volatile than gold.

    Source: FactSet (SILVCOMP-FDS:FG_PRICE).
    """
    s = Series("SILVCOMP-FDS:FG_PRICE")
    if s.empty:
        return pd.Series(dtype=float, name="Silver Spot")
    s.name = "Silver Spot"
    return s.dropna()


def platinum_spot() -> pd.Series:
    """Platinum spot price (USD/oz).

    Industrial precious metal — automotive catalysts, jewelry,
    hydrogen fuel cells. Discount to gold signals weak
    industrial demand or auto sector stress.

    Source: FactSet (PLATI-FDS:FG_PRICE).
    """
    s = Series("PLATI-FDS:FG_PRICE")
    if s.empty:
        return pd.Series(dtype=float, name="Platinum Spot")
    s.name = "Platinum Spot"
    return s.dropna()


def palladium_spot() -> pd.Series:
    """Palladium spot price (USD/oz).

    Primarily used in gasoline catalytic converters. Supply
    concentrated in Russia and South Africa — geopolitical
    risk premium. EV adoption is structural demand headwind.

    Source: FactSet (PASP-FDS:FG_PRICE).
    """
    s = Series("PASP-FDS:FG_PRICE")
    if s.empty:
        return pd.Series(dtype=float, name="Palladium Spot")
    s.name = "Palladium Spot"
    return s.dropna()


# ── Commodity Futures ────────────────────────────────────────────────────

COMMODITY_FUTURES_CODES = {
    "Crude Oil": "CL00-USA:P_FUT_PRICE_CLOSE",
    "Gold": "GC00-USA:P_FUT_PRICE_CLOSE",
    "Corn": "C00-USA:P_FUT_PRICE_CLOSE",
    "Soybean Oil": "BO00-USA:P_FUT_PRICE_CLOSE",
    "Cotton": "CT00-USA:P_FUT_PRICE_CLOSE",
    "Coffee": "KC00-USA:P_FUT_PRICE_CLOSE",
    "Sugar": "SB00-USA:P_FUT_PRICE_CLOSE",
    "Cattle": "LC00-USA:P_FUT_PRICE_CLOSE",
    "Lean Hogs": "LH00-USA:P_FUT_PRICE_CLOSE",
    "Brent": "BRN00-IFEU:P_FUT_PRICE_CLOSE",
}


def commodity_futures() -> pd.DataFrame:
    """Front-month futures prices for 10 major commodity contracts.

    Columns: Crude Oil (WTI), Gold, Corn, Soybean Oil, Cotton,
    Coffee, Sugar, Cattle, Lean Hogs, Brent.

    Source: FactSet continuous front-month futures.
    """
    data = {name: Series(code) for name, code in COMMODITY_FUTURES_CODES.items()}
    if data.empty:
        return pd.DataFrame()
    df = pd.DataFrame(data).dropna(how="all")
    return df
