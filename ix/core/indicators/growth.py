from __future__ import annotations

import numpy as np
import pandas as pd

from ix.common.data.transforms import MonthEndOffset, StandardScalar
from ix.db.query import MultiSeries, Series


# ── OECD CLI ─────────────────────────────────────────────────────────────────

OECD_CLI_CODES = [
    "USA.LOLITOAA.STSA:PX_LAST",
    "TUR.LOLITOAA.STSA:PX_LAST",
    "IND.LOLITOAA.STSA:PX_LAST",
    "IDN.LOLITOAA.STSA:PX_LAST",
    "A5M.LOLITOAA.STSA:PX_LAST",
    "CHN.LOLITOAA.STSA:PX_LAST",
    "KOR.LOLITOAA.STSA:PX_LAST",
    "BRA.LOLITOAA.STSA:PX_LAST",
    "AUS.LOLITOAA.STSA:PX_LAST",
    "CAN.LOLITOAA.STSA:PX_LAST",
    "DEU.LOLITOAA.STSA:PX_LAST",
    "ESP.LOLITOAA.STSA:PX_LAST",
    "FRA.LOLITOAA.STSA:PX_LAST",
    "G4E.LOLITOAA.STSA:PX_LAST",
    "G7M.LOLITOAA.STSA:PX_LAST",
    "GBR.LOLITOAA.STSA:PX_LAST",
    "ITA.LOLITOAA.STSA:PX_LAST",
    "JPN.LOLITOAA.STSA:PX_LAST",
    "MEX.LOLITOAA.STSA:PX_LAST",
]

OECD_CLI_EM_CODES = [
    "TUR.LOLITOAA.STSA:PX_LAST",
    "IND.LOLITOAA.STSA:PX_LAST",
    "IDN.LOLITOAA.STSA:PX_LAST",
    "CHN.LOLITOAA.STSA:PX_LAST",
    "KOR.LOLITOAA.STSA:PX_LAST",
    "BRA.LOLITOAA.STSA:PX_LAST",
    "ESP.LOLITOAA.STSA:PX_LAST",
    "ITA.LOLITOAA.STSA:PX_LAST",
    "MEX.LOLITOAA.STSA:PX_LAST",
]

OECD_CLI_DIFFUSION_WORLD_CODES = [
    "USA", "TUR", "IND", "IDN", "CHN", "KOR", "BRA",
    "AUS", "CAN", "DEU", "ESP", "FRA", "GBR", "ITA", "JPN", "MEX",
]
OECD_CLI_DIFFUSION_DEVELOPED_CODES = [
    "USA", "AUS", "CAN", "DEU", "FRA", "GBR", "ITA", "JPN",
]
OECD_CLI_DIFFUSION_EMERGING_CODES = [
    "TUR", "IND", "IDN", "CHN", "KOR", "BRA", "ESP", "MEX",
]


def _oecd_positive_mom_pct(codes: list[str]) -> pd.Series:
    data = pd.DataFrame({code: Series(code) for code in codes}).ffill().diff()
    if data.empty:
        return pd.DataFrame()
    df_numeric = data.apply(pd.to_numeric, errors="coerce")
    positive_counts = (df_numeric > 0).sum(axis=1)
    valid_counts = df_numeric.notna().sum(axis=1)
    percent_positive = (positive_counts / valid_counts) * 100
    percent_positive.index = pd.to_datetime(percent_positive.index)
    return percent_positive.sort_index()


def NumOfOECDLeadingPositiveMoM() -> pd.Series:
    """Percentage of OECD CLI series with positive MoM changes."""
    return _oecd_positive_mom_pct(OECD_CLI_CODES)


def NumOfOecdCliMoMPositiveEM() -> pd.Series:
    """Percentage of OECD CLI EM series with positive MoM changes."""
    return _oecd_positive_mom_pct(OECD_CLI_EM_CODES)


def oecd_cli_regime() -> pd.DataFrame:
    """OECD CLI regime percentages."""
    from ix.core.technical.regime import Regime1
    from ix.core.technical.moving_average import MACD

    regime_dict = {}
    for key in OECD_CLI_CODES:
        s = Series(key)
        if s.empty:
            continue
        regime_dict[key] = Regime1(MACD(s).histogram).regime
    if not regime_dict:
        return pd.DataFrame()
    data = pd.DataFrame(regime_dict).sort_index().dropna(how="all")
    if data.empty:
        return pd.DataFrame()
    data.index = pd.to_datetime(data.index)
    regimes = (
        data.apply(lambda x: x.value_counts(normalize=True) * 100, axis=1)
        .astype(float)
        .sort_index()
        .fillna(0)
    )
    return regimes


def _oecd_cli_diffusion(codes: list[str], lead_months: int = 3, freq: str = "W-FRI") -> pd.Series:
    """Compute OECD CLI diffusion index for given country codes."""
    series_dict = {
        c: Series(f"{c}.LOLITOAA.STSA:PX_LAST", freq="ME")
        for c in codes
    }
    cli_data = MultiSeries(**series_dict)
    cli_diff = cli_data.diff().dropna(how="all")
    pos_count = (cli_diff > 0).sum(axis=1)
    valid_count = cli_diff.notna().sum(axis=1)
    raw = (pos_count / valid_count).replace(
        [np.inf, -np.inf], np.nan
    ).fillna(0) * 100

    diffusion = MonthEndOffset(
        raw.to_frame(), lead_months
    ).iloc[:, 0].resample(freq).ffill()
    return diffusion


def oecd_cli_diffusion_world(lead_months: int = 3, freq: str = "W-FRI") -> pd.Series:
    """OECD CLI Diffusion Index — World."""
    s = _oecd_cli_diffusion(OECD_CLI_DIFFUSION_WORLD_CODES, lead_months, freq)
    s.name = "OECD CLI Diffusion (World)"
    return s.dropna()


def oecd_cli_diffusion_developed(lead_months: int = 3, freq: str = "W-FRI") -> pd.Series:
    """OECD CLI Diffusion Index — Developed Markets."""
    s = _oecd_cli_diffusion(OECD_CLI_DIFFUSION_DEVELOPED_CODES, lead_months, freq)
    s.name = "OECD CLI Diffusion (DM)"
    return s.dropna()


def oecd_cli_diffusion_emerging(lead_months: int = 3, freq: str = "W-FRI") -> pd.Series:
    """OECD CLI Diffusion Index — Emerging Markets."""
    s = _oecd_cli_diffusion(OECD_CLI_DIFFUSION_EMERGING_CODES, lead_months, freq)
    s.name = "OECD CLI Diffusion (EM)"
    return s.dropna()


def oecd_cli_above_trend(freq: str = "W-FRI") -> pd.Series:
    """% of OECD countries with CLI above long-term trend (>100).

    The OECD CLI is normalized to 100 = long-term trend. Countries with
    CLI > 100 are in above-trend growth; below 100 = below trend.
    This diffusion measures the breadth of the global expansion.

    Covers 16 countries: USA, CHN, DEU, JPN, KOR, GBR, FRA, ITA, ESP,
    AUS, CAN, BRA, MEX, IND, IDN, TUR.

    Interpretation:
      - >75%: broad global expansion (most countries above trend)
      - 40-75%: mixed / transitioning
      - <25%: broad contraction (most countries below trend)

    Empirical: r=-0.21 vs SPX 6M fwd returns (contrarian — when everyone
    is above trend, forward returns are lower). MoM diffusion (existing)
    has r=+0.20 which is more useful for momentum. This indicator is
    better as a regime classifier than a return predictor.

    Source: OECD Composite Leading Indicators (CLI).
    """
    series_dict = {
        c: Series(f"{c}.LOLITOAA.STSA:PX_LAST", freq="ME")
        for c in OECD_CLI_DIFFUSION_WORLD_CODES
    }
    cli_data = pd.DataFrame(series_dict).ffill().dropna(how="all")
    if cli_data.empty:
        return pd.Series(dtype=float, name="OECD CLI Above Trend (%)")
    above = (cli_data > 100).sum(axis=1)
    valid = cli_data.notna().sum(axis=1)
    raw = (above / valid * 100).replace([np.inf, -np.inf], np.nan).fillna(0)
    result = raw.resample(freq).last().ffill()
    result.name = "OECD CLI Above Trend (%)"
    return result.dropna()


def oecd_cli_above_trend_by_country(freq: str = "ME") -> pd.DataFrame:
    """Per-country above/below trend status (1 = above, 0 = below).

    Returns a DataFrame with country columns showing binary above-trend
    status. Useful for identifying which specific countries are driving
    global expansion or contraction.

    Source: OECD Composite Leading Indicators (CLI).
    """
    series_dict = {
        c: Series(f"{c}.LOLITOAA.STSA:PX_LAST", freq=freq)
        for c in OECD_CLI_DIFFUSION_WORLD_CODES
    }
    cli_data = pd.DataFrame(series_dict).ffill().dropna(how="all")
    if cli_data.empty:
        return pd.DataFrame()
    result = (cli_data > 100).astype(int)
    return result.dropna(how="all")


# Backward-compatible wrapper
class OecdCliDiffusionIndex:
    def __init__(self, lead_months: int = 3, freq: str = "W-FRI") -> None:
        self.lead_months = lead_months
        self.freq = freq

    @property
    def world(self) -> pd.Series:
        return oecd_cli_diffusion_world(self.lead_months, self.freq)

    @property
    def developed(self) -> pd.Series:
        return oecd_cli_diffusion_developed(self.lead_months, self.freq)

    @property
    def emerging(self) -> pd.Series:
        return oecd_cli_diffusion_emerging(self.lead_months, self.freq)


# ── PMI ──────────────────────────────────────────────────────────────────────

PMI_MANUFACTURING_CODES = [
    "NTCPMIMFGSA_WLD:PX_LAST",
    "NTCPMIMFGMESA_US:PX_LAST",
    "ISMPMI_M:PX_LAST",
    "NTCPMIMFGSA_CA:PX_LAST",
    "NTCPMIMFGSA_EUZ:PX_LAST",
    "NTCPMIMFGSA_DE:PX_LAST",
    "NTCPMIMFGSA_FR:PX_LAST",
    "NTCPMIMFGSA_IT:PX_LAST",
    "NTCPMIMFGSA_ES:PX_LAST",
    "NTCPMIMFGSA_GB:PX_LAST",
    "NTCPMIMFGSA_JP:PX_LAST",
    "NTCPMIMFGSA_KR",
    "NTCPMIMFGSA_IN:PX_LAST",
    "NTCPMIMFGNSA_CN:PX_LAST",
]

PMI_SERVICES_CODES = [
    "NTCPMISVCBUSACTSA_WLD:PX_LAST",
    "NTCPMISVCBUSACTMESA_US:PX_LAST",
    "ISMNMI_NM:PX_LAST",
    "NTCPMISVCBUSACTSA_EUZ:PX_LAST",
    "NTCPMISVCBUSACTSA_DE:PX_LAST",
    "NTCPMISVCBUSACTSA_FR:PX_LAST",
    "NTCPMISVCBUSACTSA_IT:PX_LAST",
    "NTCPMISVCBUSACTSA_ES:PX_LAST",
    "NTCPMISVCBUSACTSA_GB:PX_LAST",
    "NTCPMISVCPSISA_AU:PX_LAST",
    "NTCPMISVCBUSACTSA_JP:PX_LAST",
    "NTCPMISVCBUSACTSA_CN:PX_LAST",
    "NTCPMISVCBUSACTSA_IN:PX_LAST",
    "NTCPMISVCBUSACTSA_BR:PX_LAST",
]


def _pmi_positive_mom_pct(codes: list[str]) -> pd.Series:
    data = pd.DataFrame({code: Series(code) for code in codes}).ffill().diff()
    if data.empty:
        return pd.DataFrame()
    df_numeric = data.apply(pd.to_numeric, errors="coerce")
    positive_counts = (df_numeric > 0).sum(axis=1)
    valid_counts = df_numeric.notna().sum(axis=1)
    percent_positive = (positive_counts / valid_counts) * 100
    percent_positive.index = pd.to_datetime(percent_positive.index)
    return percent_positive.sort_index()


def _regime_percentages(codes: list[str]) -> pd.DataFrame:
    from ix import core

    regimes = []
    for code in codes:
        regime = core.Regime1(core.MACD(Series(code)).histogram).regime
        regimes.append(regime)

    regimes_df = pd.concat(regimes, axis=1)
    regime_counts = regimes_df.apply(
        lambda row: row.value_counts(normalize=True) * 100, axis=1
    )
    regime_pct = regime_counts.fillna(0).round(2)
    return regime_pct[["Expansion", "Slowdown", "Contraction", "Recovery"]].dropna()


def pmi_manufacturing_diffusion() -> pd.Series:
    """% of PMI Mfg series with positive MoM changes."""
    raw = {code: Series(code) for code in PMI_MANUFACTURING_CODES}
    data = pd.DataFrame(raw).ffill().diff()
    if data.empty:
        return pd.Series(dtype=float)
    data = data.dropna(thresh=10)
    df_numeric = data.apply(pd.to_numeric, errors="coerce")
    positive_counts = (df_numeric > 0).sum(axis=1)
    valid_counts = df_numeric.notna().sum(axis=1)
    return (positive_counts / valid_counts) * 100


def pmi_services_diffusion() -> pd.Series:
    """% of PMI Services series with positive MoM changes."""
    return _pmi_positive_mom_pct(PMI_SERVICES_CODES)


def pmi_manufacturing_regime() -> pd.DataFrame:
    """PMI Manufacturing regime percentages."""
    return _regime_percentages(PMI_MANUFACTURING_CODES)


def pmi_services_regime() -> pd.DataFrame:
    """PMI Services regime percentages."""
    result = _regime_percentages(PMI_SERVICES_CODES)
    result.index = pd.to_datetime(result.index)
    return result.sort_index()


# Backward-compatible aliases
def NumOfPmiMfgPositiveMoM() -> pd.Series:
    return pmi_manufacturing_diffusion()


def NumOfPmiServicesPositiveMoM() -> pd.Series:
    return pmi_services_diffusion()


def PMI_Manufacturing_Regime() -> pd.DataFrame:
    return pmi_manufacturing_regime()


def PMI_Services_Regime() -> pd.DataFrame:
    return pmi_services_regime()


# ── ISM ──────────────────────────────────────────────────────────────────────

# ISM Manufacturing sub-component codes
ISM_MFG_CODES = {
    "PMI": "ISMPMI_M",
    "New Orders": "ISMNOR_M",
    "Production": "ISMPRD_M",
    "Employment": "ISMEMP_M",
    "Supplier Deliveries": "ISMSUP_M",
    "Inventories": "ISMINV_M",
    "Customers Inventories": "ISMCINV_M",
    "Backlog of Orders": "ISMBOR_M",
    "New Export Orders": "ISMEXP_M",
    "Imports": "ISMIMP_M",
    "Prices": "ISMPRI_M",
}

# ISM Services sub-component codes
ISM_SVC_CODES = {
    "PMI": "ISMNMI_NM",
    "Business Activity": "ISMBUS_NM",
    "New Orders": "ISMNOR_NM",
    "Employment": "ISMEMP_NM",
    "Supplier Deliveries": "ISMSUP_NM",
    "Inventories": "ISMICH_NM",
    "Inventory Sentiment": "ISMINV_NM",
    "Backlog of Orders": "ISMBOR_NM",
    "New Export Orders": "ISMEXP_NM",
    "Imports": "ISMIMP_NM",
    "Prices": "ISMPRI_NM",
}


def ism_manufacturing_data() -> pd.DataFrame:
    """All ISM Manufacturing sub-components as DataFrame."""
    data = {name: Series(code) for name, code in ISM_MFG_CODES.items()}
    df = pd.DataFrame(data).dropna(how="all")
    if df.empty:
        return pd.DataFrame()
    return df


def ism_services_data() -> pd.DataFrame:
    """All ISM Services sub-components as DataFrame."""
    data = {name: Series(code) for name, code in ISM_SVC_CODES.items()}
    df = pd.DataFrame(data).dropna(how="all")
    if df.empty:
        return pd.DataFrame()
    return df


def ism_new_orders(freq: str = "ME") -> pd.Series:
    """ISM Manufacturing New Orders index."""
    s = Series("ISMNOR_M:PX_LAST", freq=freq).ffill()
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "ISM New Orders"
    return s.dropna()


def ism_manufacturing_breadth() -> pd.Series:
    """% of ISM Manufacturing sub-components above 50."""
    data = {name: Series(code) for name, code in ISM_MFG_CODES.items()}
    df = pd.DataFrame(data).dropna(how="all")
    if df.empty:
        return pd.Series(dtype=float, name="ISM Mfg Breadth (>50)")
    above_50 = (df > 50).sum(axis=1)
    valid = df.notna().sum(axis=1)
    result = (above_50 / valid * 100).dropna()
    result.name = "ISM Mfg Breadth (>50)"
    return result


def ism_services_breadth() -> pd.Series:
    """% of ISM Services sub-components above 50."""
    data = {name: Series(code) for name, code in ISM_SVC_CODES.items()}
    df = pd.DataFrame(data).dropna(how="all")
    if df.empty:
        return pd.Series(dtype=float, name="ISM Svc Breadth (>50)")
    above_50 = (df > 50).sum(axis=1)
    valid = df.notna().sum(axis=1)
    result = (above_50 / valid * 100).dropna()
    result.name = "ISM Svc Breadth (>50)"
    return result


def ism_new_orders_minus_inventories() -> pd.Series:
    """ISM Manufacturing New Orders - Inventories spread.

    Classic leading indicator: rising = building demand,
    falling = inventory overhang.
    """
    noi = Series("ISMNOR_M") - Series("ISMINV_M")
    if noi.empty:
        return pd.Series(dtype=float)
    noi.name = "ISM New Orders - Inventories"
    return noi.dropna()


def ism_new_orders_minus_customers_inventories() -> pd.Series:
    """ISM Manufacturing New Orders - Customers' Inventories spread.

    Even more forward-looking than Orders - Inventories.
    """
    spread = Series("ISMNOR_M") - Series("ISMCINV_M")
    if spread.empty:
        return pd.Series(dtype=float)
    spread.name = "ISM New Orders - Customers Inv"
    return spread.dropna()


def ism_manufacturing_momentum_breadth() -> pd.Series:
    """% of ISM Manufacturing sub-components with positive MoM change."""
    data = {name: Series(code) for name, code in ISM_MFG_CODES.items()}
    df = pd.DataFrame(data).dropna(how="all")
    if df.empty:
        return pd.Series(dtype=float, name="ISM Mfg Momentum Breadth")
    changes = df.diff()
    positive = (changes > 0).sum(axis=1)
    valid = changes.notna().sum(axis=1)
    result = (positive / valid * 100).dropna()
    result.name = "ISM Mfg Momentum Breadth"
    return result


def ism_lead_composite(
    lead_weeks: int = 8,
    z_window: int = 78,
    halflife: int = 3,
) -> pd.Series:
    """ISM Manufacturing lead composite (2-month forward signal).

    Two-tier composite of indicators that empirically lead the ISM PMI:

    Tier 1 (40% weight) — Regional Fed surveys, released ~2w before ISM:
      - Philadelphia Fed Manufacturing Index

    Tier 2 (60% weight) — Macro leading signals with 8-13w genuine lead:
      - -NFCI (Chicago Fed financial conditions, inverted: loose = positive)
      - Credit Impulse (2nd derivative of bank credit)
      - Building Permits YoY (housing cycle leads manufacturing)
      - -Initial Claims (fewer claims = stronger labor market)
      - LEI momentum (Conference Board LEI % change)

    Empirical performance (Pearson r vs ISM):
      0w: +0.42, 4w: +0.34, 8w: +0.23, 13w: +0.08

    Limitations:
      - Lead is modest (8w / ~2 months), not the 5-9 months GMI claims
      - r=0.23 at the 8w lead is weak — useful for direction, not magnitude
      - Most "financial conditions lead ISM" relationships are concurrent
        or cyclical artifacts, not genuine causal leads
      - The Philly Fed component is more of a 2-week preview than a true
        leading indicator — it surveys the same population earlier
      - Regional Fed surveys (Philly, Empire State) dominate the signal;
        the macro components (credit, permits, claims) add modest value

    Source: Composite of FRED/Bloomberg series. Methodology inspired by
    GMI/CrossBorder Capital (Raoul Pal, Julien Bittel) but with
    empirically validated components and honest lead assessment.
    """
    from ix.core.indicators.liquidity import credit_impulse as _credit_impulse

    # Tier 1: Regional Fed (2w natural lead over ISM release)
    philly = Series("USSU0008906", freq="W")
    tier1_parts = {}
    if not philly.empty:
        tier1_parts["Philly"] = StandardScalar(philly, z_window)

    # Tier 2: Macro leading signals
    nfci = Series("NFCI:PX_LAST", freq="W")
    permits = Series("PERMIT", freq="W")
    claims = Series("ICSA", freq="W")
    lei = Series("US.LEI:PX_LAST", freq="W")

    tier2_parts = {}
    if not nfci.empty:
        tier2_parts["NFCI_ease"] = -StandardScalar(nfci, z_window)
    ci = _credit_impulse("ME").resample("W").last().ffill()
    if not ci.empty:
        tier2_parts["Credit"] = StandardScalar(ci, z_window)
    if not permits.empty:
        p_yoy = permits.pct_change(52).mul(100).dropna()
        if not p_yoy.empty:
            tier2_parts["Permits_YoY"] = StandardScalar(p_yoy, z_window)
    if not claims.empty:
        tier2_parts["Claims_inv"] = -StandardScalar(claims, z_window)
    if not lei.empty:
        lei_mom = lei.pct_change(12).mul(100).dropna()
        if not lei_mom.empty:
            tier2_parts["LEI_mom"] = StandardScalar(lei_mom, z_window)

    # Combine tiers
    tier1 = pd.DataFrame(tier1_parts).mean(axis=1) if tier1_parts else pd.Series(dtype=float)
    tier2 = pd.DataFrame(tier2_parts).mean(axis=1) if tier2_parts else pd.Series(dtype=float)

    if tier1.empty and tier2.empty:
        return pd.Series(dtype=float, name="ISM Lead Composite")

    if tier1.empty:
        composite = tier2
    elif tier2.empty:
        composite = tier1
    else:
        composite = (0.4 * tier1 + 0.6 * tier2).dropna()

    # Smooth and shift forward
    composite = composite.ewm(halflife=halflife).mean()
    composite.index = composite.index + pd.Timedelta(weeks=lead_weeks)
    composite.name = "ISM Lead Composite"
    return composite.dropna()


# ── Global PMI Manufacturing ──────────────────────────────────────────────

GLOBAL_PMI_MFG_CODES = {
    "Eurozone": "NTCPMIMFGSA@EUZ",
    "China": "NTCPMIMFGSA@CN",
    "Japan": "NTCPMIMFGSA@JP",
    "UK": "NTCPMIMFGSA@GB",
    "India": "NTCPMIMFGSA@IN",
    "Brazil": "NTCPMIMFGSA@BR",
}


def global_pmi_manufacturing() -> pd.DataFrame:
    """Manufacturing PMI for 6 major economies.

    Columns: Eurozone, China (Caixin), Japan, UK, India, Brazil.
    PMI > 50 = expansion, < 50 = contraction.

    Source: S&P Global / Markit Manufacturing PMI (SA).
    """
    data = {name: Series(code) for name, code in GLOBAL_PMI_MFG_CODES.items()}
    df = pd.DataFrame(data).dropna(how="all")
    if df.empty:
        return pd.DataFrame()
    return df


def global_pmi_breadth() -> pd.Series:
    """Percentage of countries with Manufacturing PMI above 50.

    100% = all 6 economies expanding. 0% = all contracting.
    Breadth above 67% = broad global expansion.

    Source: S&P Global / Markit Manufacturing PMI.
    """
    df = global_pmi_manufacturing()
    if df.empty:
        return pd.Series(dtype=float, name="Global PMI Breadth")
    above_50 = (df > 50).sum(axis=1)
    valid = df.notna().sum(axis=1)
    s = (above_50 / valid * 100).dropna()
    s.name = "Global PMI Breadth"
    return s


def global_pmi_momentum() -> pd.Series:
    """Percentage of countries with Manufacturing PMI rising MoM.

    Measures acceleration of global manufacturing activity.
    100% = all countries improving. 0% = all deteriorating.

    Source: S&P Global / Markit Manufacturing PMI.
    """
    df = global_pmi_manufacturing()
    if df.empty:
        return pd.Series(dtype=float, name="Global PMI Momentum")
    changes = df.diff()
    positive = (changes > 0).sum(axis=1)
    valid = changes.notna().sum(axis=1)
    s = (positive / valid * 100).dropna()
    s.name = "Global PMI Momentum"
    return s


# ── S&P 500 Breadth & Revisions ─────────────────────────────────────────────


def spx_pct_above_50dma() -> pd.Series:
    """Percentage of S&P 500 stocks above their 50-day moving average.

    Market breadth indicator. High values (>80%) suggest overbought,
    low values (<20%) suggest oversold.
    Source: FactSet (SP50:FMA_PCT_ABOVE_50).
    """
    s = Series("SP50:FMA_PCT_ABOVE_50")
    if s.empty:
        return pd.Series(dtype=float, name="S&P 500 % Above 50 DMA")
    s.name = "S&P 500 % Above 50 DMA"
    return s.dropna()


def spx_revision_spread() -> pd.Series:
    """S&P 500 earnings revision spread: upgrades minus downgrades (1-month).

    Net percentage of companies with upward FY0 EPS revisions.
    Positive = more upgrades than downgrades. Leading indicator for EPS growth.
    Source: FactSet (SP50:FMA_COS_UP_FY0_1M, SP50:FMA_COS_DOWN_FY0_1M).
    """
    up = Series("SP50:FMA_COS_UP_FY0_1M")
    down = Series("SP50:FMA_COS_DOWN_FY0_1M")
    if up.empty or down.empty:
        return pd.Series(dtype=float, name="S&P 500 Revision Spread")
    df = pd.DataFrame({"up": up, "down": down}).dropna()
    result = df["up"] - df["down"]
    result.name = "S&P 500 Revision Spread"
    return result.dropna()


def spx_forward_eps() -> pd.Series:
    """S&P 500 forward (next-twelve-months) EPS estimate.

    Source: FactSet (SP50:FMA_EPS_NTMA).
    """
    s = Series("SP50:FMA_EPS_NTMA")
    if s.empty:
        return pd.Series(dtype=float, name="S&P 500 Forward EPS")
    s.name = "S&P 500 Forward EPS"
    return s.dropna()
