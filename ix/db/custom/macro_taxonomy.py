"""Unified macro indicator registry with category taxonomy.

Every macro indicator is assigned to exactly one of four categories:
    Growth, Inflation, Liquidity, Tactical.

The module exports a single function ``build_macro_registry()`` that returns
the full list of (name, callable, category, description, invert) tuples.

Usage:
    from ix.db.custom.macro_taxonomy import build_macro_registry
    registry = build_macro_registry()
"""

from __future__ import annotations

from typing import Callable

import pandas as pd

from ix.db.query import Series as DBSeries

# ---------------------------------------------------------------------------
# Imports from existing ix.db.custom modules
# ---------------------------------------------------------------------------
from ix.db.custom import (
    # PMI
    NumOfPmiMfgPositiveMoM,
    NumOfPmiServicesPositiveMoM,
    # OECD
    oecd_cli_diffusion_world,
    oecd_cli_diffusion_developed,
    oecd_cli_diffusion_emerging,
    # ISM
    ism_new_orders,
    ism_new_orders_minus_inventories,
    ism_services_breadth,
    ism_manufacturing_breadth,
    ism_manufacturing_momentum_breadth,
    ism_manufacturing_data,
    # Sentiment / CESI
    cesi_breadth,
    cesi_momentum,
    # Trade
    asian_exports_diffusion,
    asian_exports_momentum,
    global_trade_composite,
    korea_semi_exports_yoy,
    # Earnings
    spx_revision_ratio,
    regional_eps_breadth,
    # Earnings deep
    eps_estimate_dispersion,
    earnings_momentum_score,
    earnings_composite,
    # Cross-asset
    copper_gold_ratio,
    small_large_cap_ratio,
    cyclical_defensive_ratio,
    baltic_dry_index,
    dollar_index,
    vix,
    commodities_crb,
    # Alt data
    sox_momentum,
    sox_spx_ratio,
    housing_starts,
    building_permits,
    housing_affordability_proxy,
    wti_crude,
    natural_gas,
    baltic_dry_momentum,
    # Inflation
    inflation_surprise,
    inflation_momentum,
    breakeven_momentum,
    commodity_inflation_pressure,
    # Rates
    us_10y_breakeven,
    us_10y_real,
    us_2s10s,
    us_3m10y,
    hy_spread,
    ig_spread,
    bbb_spread,
    hy_ig_ratio,
    risk_appetite,
    # Liquidity
    fed_net_liquidity,
    tga_drawdown,
    treasury_net_issuance,
    m2_us,
    m2_world_total_yoy,
    credit_impulse,
    global_liquidity_yoy,
    # Central bank
    fed_total_assets,
    fed_assets_yoy,
    fed_assets_momentum,
    g4_balance_sheet_total,
    g4_balance_sheet_yoy,
    central_bank_liquidity_composite,
    rate_cut_probability_proxy,
    global_rate_divergence,
    # FCI
    fci_us,
    fci_stress,
    # Monetary policy
    rate_cut_expectations,
    rate_expectations_momentum,
    term_premium_proxy,
    policy_rate_level,
    # Credit deep
    credit_stress_index,
    hy_spread_momentum,
    hy_spread_velocity,
    credit_cycle_phase,
    ig_hy_compression,
    financial_conditions_credit,
    # Fund flows
    margin_debt_yoy,
    equity_bond_flow_ratio,
    bank_credit_impulse,
    consumer_credit_growth,
    # China / EM
    china_credit_impulse,
    china_m2_yoy,
    china_m2_momentum,
    pboc_easing_proxy,
    em_sovereign_spread,
    # Nowcasting
    gdpnow,
    weekly_economic_index,
    wei_momentum,
    initial_claims,
    nowcast_composite,
    industrial_production_yoy,
    capacity_utilization,
    # Intermarket
    risk_on_off_breadth,
    credit_equity_divergence,
    vix_realized_vol_spread,
    # Volatility
    vix_term_structure,
    vix_term_spread,
    skew_index,
    skew_zscore,
    vol_risk_premium,
    vol_risk_premium_zscore,
    vvix_vix_ratio,
    gamma_exposure_proxy,
    realized_vol_regime,
    # Factors
    momentum_breadth,
    momentum_composite,
    # Correlation regime
    equity_bond_corr_zscore,
    safe_haven_demand,
    tail_risk_index,
    diversification_index,
    correlation_surprise,
    # Equity valuation
    erp_zscore,
    # Sentiment
    put_call_zscore,
    cftc_net,
    cftc_zscore,
    cftc_extreme_count,
    # Sector rotation
    us_sector_breadth,
    us_sector_dispersion,
    # Fund flows
    risk_rotation_index,
)

# cross_asset_correlation (full pairwise version) is not re-exported from
# __init__.py — only cross_asset_correlation_fast is.  Import directly.
from ix.db.custom.correlation_regime import cross_asset_correlation


# ---------------------------------------------------------------------------
# Database series helpers
# ---------------------------------------------------------------------------


def _load_series(code: str) -> pd.Series:
    """Load a raw series from the database by its timeseries code."""
    try:
        s = DBSeries(code)
        if isinstance(s, pd.DataFrame):
            s = s.iloc[:, 0]
        return s.dropna() if s is not None and not s.empty else pd.Series(dtype=float)
    except Exception:
        return pd.Series(dtype=float)


def _yoy_change(code: str) -> pd.Series:
    """Load series and compute YoY % change."""
    s = _load_series(code)
    if s.empty:
        return s
    return s.pct_change(periods=12 if len(s) < 500 else 252).dropna() * 100


def _momentum(code: str, periods: int = 13) -> pd.Series:
    """Load series and compute N-period momentum (% change)."""
    s = _load_series(code)
    if s.empty:
        return s
    return s.pct_change(periods=periods).dropna() * 100


# ---------------------------------------------------------------------------
# Wrapper helpers for special-case existing functions
# ---------------------------------------------------------------------------


def _ism_prices_paid() -> pd.Series:
    """ISM Manufacturing Prices Paid sub-component."""
    try:
        df = ism_manufacturing_data()
        if "Prices" in df.columns:
            return df["Prices"].dropna()
    except Exception:
        pass
    return pd.Series(dtype=float)


def _cpi_3m_ann() -> pd.Series:
    """CPI 3-month annualized rate from inflation_momentum()."""
    try:
        df = inflation_momentum()
        if "CPI 3m Ann" in df.columns:
            return df["CPI 3m Ann"].dropna()
    except Exception:
        pass
    return pd.Series(dtype=float)


def _eps_dispersion_series() -> pd.Series:
    """eps_estimate_dispersion may return DataFrame; extract first column."""
    try:
        result = eps_estimate_dispersion()
        if isinstance(result, pd.DataFrame):
            return result.iloc[:, 0].dropna()
        return result.dropna()
    except Exception:
        return pd.Series(dtype=float)


def _us_10y_breakeven_weekly() -> pd.Series:
    """10Y breakeven resampled to weekly for inflation tracking."""
    try:
        s = us_10y_breakeven()
        if s.empty:
            return s
        return s.resample("W").last().dropna()
    except Exception:
        return pd.Series(dtype=float)


def _cftc_position(asset: str) -> pd.Series:
    """Extract a single asset's net positioning from cftc_net() DataFrame."""
    try:
        df = cftc_net()
        if asset in df.columns:
            return df[asset].dropna()
    except Exception:
        pass
    return pd.Series(dtype=float)


# ---------------------------------------------------------------------------
# Category constants
# ---------------------------------------------------------------------------

GROWTH = "Growth"
INFLATION = "Inflation"
LIQUIDITY = "Liquidity"
TACTICAL = "Tactical"


# ---------------------------------------------------------------------------
# Registry builder
# ---------------------------------------------------------------------------


def build_macro_registry() -> list[tuple[str, Callable, str, str, bool]]:
    """Build the unified macro indicator registry.

    Returns
    -------
    list of (name, callable, category, description, invert)
        name : str         -- display name
        callable : Callable -- zero-arg function returning pd.Series
        category : str      -- one of "Growth", "Inflation", "Liquidity", "Tactical"
        description : str   -- short description
        invert : bool       -- True if higher raw value is bearish for that axis
    """
    registry: list[tuple[str, Callable, str, str, bool]] = []
    registry.extend(_growth_indicators())
    registry.extend(_inflation_indicators())
    registry.extend(_liquidity_indicators())
    registry.extend(_tactical_indicators())
    return registry


# ===================================================================
# GROWTH  (63 indicators)
# ===================================================================


def _growth_indicators() -> list[tuple[str, Callable, str, str, bool]]:
    G = GROWTH
    return [
        # -- PMI -------------------------------------------------------
        ("PMI Mfg Diffusion", NumOfPmiMfgPositiveMoM, G,
         "Share of countries with rising manufacturing PMI", False),
        ("PMI Services Diffusion", NumOfPmiServicesPositiveMoM, G,
         "Share of countries with rising services PMI", False),

        # -- OECD CLI --------------------------------------------------
        ("OECD CLI World", oecd_cli_diffusion_world, G,
         "OECD composite leading indicator diffusion - world", False),
        ("OECD CLI Developed", oecd_cli_diffusion_developed, G,
         "OECD CLI diffusion - developed markets", False),
        ("OECD CLI Emerging", oecd_cli_diffusion_emerging, G,
         "OECD CLI diffusion - emerging markets", False),

        # -- ISM -------------------------------------------------------
        ("ISM New Orders", ism_new_orders, G,
         "ISM Manufacturing New Orders index", False),
        ("ISM NO-Inv Spread", ism_new_orders_minus_inventories, G,
         "ISM New Orders minus Inventories spread", False),
        ("ISM Services Breadth", ism_services_breadth, G,
         "Pct of ISM Services sub-components above 50", False),
        ("ISM Mfg Breadth", ism_manufacturing_breadth, G,
         "Pct of ISM Manufacturing sub-components above 50", False),
        ("ISM Mfg Momentum", ism_manufacturing_momentum_breadth, G,
         "Pct of ISM Mfg sub-components with positive MoM change", False),

        # -- CESI / Sentiment ------------------------------------------
        ("CESI Breadth", cesi_breadth, G,
         "Citi Economic Surprise breadth across regions", False),
        ("CESI Momentum", cesi_momentum, G,
         "Citi Economic Surprise momentum", False),

        # -- Trade -----------------------------------------------------
        ("Asian Exports Diffusion", asian_exports_diffusion, G,
         "Share of Asian economies with rising exports", False),
        ("Asian Exports Momentum", asian_exports_momentum, G,
         "Momentum of Asian export growth", False),
        ("Global Trade Composite", global_trade_composite, G,
         "Composite global trade activity indicator", False),
        ("Korea Semi Exports", korea_semi_exports_yoy, G,
         "Korea semiconductor exports YoY growth", False),

        # -- Earnings --------------------------------------------------
        ("SPX Revision Ratio", spx_revision_ratio, G,
         "S&P 500 earnings revision ratio (up/down)", False),
        ("EPS Breadth", regional_eps_breadth, G,
         "Regional earnings revision breadth", False),
        ("EPS Dispersion Z", _eps_dispersion_series, G,
         "Cross-sectional dispersion of EPS estimates", False),
        ("Earnings Momentum", earnings_momentum_score, G,
         "Composite earnings momentum score", False),
        ("Earnings Composite", earnings_composite, G,
         "Broad earnings health composite", False),

        # -- Cross-asset growth proxies --------------------------------
        ("Copper/Gold", lambda: copper_gold_ratio(freq="W"), G,
         "Copper-to-gold ratio - growth expectation proxy", False),
        ("Small/Large Cap", lambda: small_large_cap_ratio(freq="W"), G,
         "Small-cap vs large-cap relative performance", False),
        ("Cyclical/Defensive", lambda: cyclical_defensive_ratio(freq="W"), G,
         "Cyclical vs defensive sector ratio", False),
        ("Baltic Dry Index", lambda: baltic_dry_index(freq="W"), G,
         "Baltic Dry Index - global shipping demand", False),
        ("SOX Momentum", sox_momentum, G,
         "Philadelphia Semiconductor Index momentum", False),
        ("SOX/SPX Ratio", sox_spx_ratio, G,
         "SOX relative to S&P 500", False),

        # -- Nowcasting ------------------------------------------------
        ("GDPNow", gdpnow, G,
         "Atlanta Fed GDPNow real-time GDP estimate", False),
        ("Weekly Economic Index", weekly_economic_index, G,
         "NY Fed Weekly Economic Index", False),
        ("WEI Momentum", wei_momentum, G,
         "Weekly Economic Index rate of change", False),
        ("Initial Claims", initial_claims, G,
         "Initial jobless claims - high is bearish", True),
        ("Nowcast Composite", nowcast_composite, G,
         "Composite nowcasting indicator", False),
        ("Industrial Production YoY", industrial_production_yoy, G,
         "US industrial production year-over-year", False),
        ("Capacity Utilization", capacity_utilization, G,
         "US capacity utilization rate", False),

        # -- Housing / Alt ---------------------------------------------
        ("Housing Starts", housing_starts, G,
         "US new housing starts", False),
        ("Building Permits", building_permits, G,
         "US building permits issued", False),
        ("Housing Affordability", housing_affordability_proxy, G,
         "Housing affordability proxy index", False),
        ("Baltic Dry Momentum", baltic_dry_momentum, G,
         "Baltic Dry Index momentum", False),

        # -- New [N]: Global PMI from DB -------------------------------
        ("Global Composite PMI",
         lambda: _load_series("MPMIGLCA INDEX:PX_LAST"), G,
         "JPMorgan Global Composite PMI", False),
        ("Global Mfg PMI",
         lambda: _load_series("MPMIGLMA INDEX:PX_LAST"), G,
         "JPMorgan Global Manufacturing PMI", False),
        ("Global Services PMI",
         lambda: _load_series("MPMIGLSA INDEX:PX_LAST"), G,
         "JPMorgan Global Services PMI", False),
        ("China Caixin Mfg PMI",
         lambda: _load_series("MPMICNMA INDEX:PX_LAST"), G,
         "Caixin China Manufacturing PMI", False),
        ("China Caixin Services PMI",
         lambda: _load_series("MPMICNSA INDEX:PX_LAST"), G,
         "Caixin China Services PMI", False),
        ("Eurozone Composite PMI",
         lambda: _load_series("MPMIEZCA INDEX:PX_LAST"), G,
         "Eurozone Composite PMI", False),
        ("ASEAN Mfg PMI",
         lambda: _load_series("NTCPMIASNMANHE:PX_LAST"), G,
         "ASEAN Manufacturing PMI", False),
        ("US OECD CLI",
         lambda: _load_series("USA.LOLITOAA.STSA:PX_LAST"), G,
         "OECD Composite Leading Indicator for the US", False),

        # -- New [N]: Consumer / Business Confidence -------------------
        ("Consumer Confidence",
         lambda: _load_series("CCI INDEX:PX_LAST"), G,
         "Conference Board Consumer Confidence Index", False),
        ("Consumer Confidence Present",
         lambda: _load_series("CCIPRESENT INDEX:PX_LAST"), G,
         "Consumer Confidence present situation component", False),
        ("UMich Consumer Sentiment",
         lambda: _load_series("CONSSENT INDEX:PX_LAST"), G,
         "University of Michigan Consumer Sentiment", False),
        ("NFIB Small Biz Optimism",
         lambda: _load_series("USSU0062552:PX_LAST"), G,
         "NFIB Small Business Optimism Index", False),

        # -- New [N]: Activity indices ---------------------------------
        ("CFNAI 3M MA",
         lambda: _load_series("CFNAIMA3 INDEX:PX_LAST"), G,
         "Chicago Fed National Activity Index 3-month moving average", False),
        ("Leading Economic Index",
         lambda: _load_series("USLEI:PX_LAST"), G,
         "Conference Board Leading Economic Index", False),
        ("Durable Goods YoY",
         lambda: _load_series("DGNOYOY INDEX:PX_LAST"), G,
         "Durable goods orders year-over-year", False),
        ("Retail Sales ex-Auto",
         lambda: _load_series("CENRETAIL&FS_MVP_US:PX_LAST"), G,
         "Retail sales excluding auto", False),

        # -- New [N]: Labor market -------------------------------------
        ("JOLTS Job Openings",
         lambda: _load_series("JOLTTOTL INDEX:PX_LAST"), G,
         "JOLTS total job openings", False),
        ("NFP MoM Change",
         lambda: _load_series("NFP TCH INDEX:PX_LAST"), G,
         "Non-farm payrolls month-over-month change", False),
        ("Temp Help Employment",
         lambda: _load_series("BLSCES6056132001:PX_LAST"), G,
         "Temporary help services employment - leading labor indicator", False),

        # -- New [N]: Regional Fed surveys -----------------------------
        ("Philly Fed Mfg",
         lambda: _load_series("PNMABNIN INDEX:PX_LAST"), G,
         "Philadelphia Fed Manufacturing Index", False),
        ("Empire State Mfg",
         lambda: _load_series("EMPRGBCI INDEX:PX_LAST"), G,
         "Empire State Manufacturing Index", False),

        # -- New [N]: China activity -----------------------------------
        ("China IP YoY",
         lambda: _load_series("EHIUCNY INDEX:PX_LAST"), G,
         "China industrial production year-over-year", False),
        ("China Official Mfg PMI",
         lambda: _load_series("CPMINDX INDEX:PX_LAST"), G,
         "NBS China Official Manufacturing PMI", False),

        # -- New [N]: Housing deep -------------------------------------
        ("Case-Shiller Home Prices",
         lambda: _load_series("CSUSHPINSA:PX_LAST"), G,
         "S&P/Case-Shiller US National Home Price Index", False),
        ("New Home Sales",
         lambda: _load_series("CENHSOLDTOT_US:PX_LAST"), G,
         "US new home sales", False),
    ]


# ===================================================================
# INFLATION  (37 indicators)
# ===================================================================


def _inflation_indicators() -> list[tuple[str, Callable, str, str, bool]]:
    I = INFLATION
    return [
        # -- Existing [E] ----------------------------------------------
        ("Inflation Surprise", inflation_surprise, I,
         "CPI YoY deviation from 12M moving average", False),
        ("10Y Breakeven", _us_10y_breakeven_weekly, I,
         "US 10Y breakeven inflation rate (weekly)", False),
        ("Breakeven Momentum", breakeven_momentum, I,
         "Rate of change in 10Y breakeven inflation", False),
        ("Commodity Inflation Pressure", commodity_inflation_pressure, I,
         "Composite z-score of oil, copper, CRB YoY", False),
        ("CRB Index", lambda: commodities_crb(freq="W"), I,
         "CRB Commodity Index (weekly)", False),
        ("WTI Crude", wti_crude, I,
         "WTI crude oil price", False),
        ("Natural Gas", natural_gas, I,
         "Natural gas price", False),
        ("ISM Prices Paid", _ism_prices_paid, I,
         "ISM Manufacturing Prices Paid sub-component", False),
        ("CPI 3M Annualized", _cpi_3m_ann, I,
         "CPI 3-month annualized rate", False),

        # -- New [N]: Core inflation -----------------------------------
        ("PCE Core YoY",
         lambda: _load_series("PCE CYOY INDEX:PX_LAST"), I,
         "Core PCE deflator year-over-year", False),
        ("Cleveland Fed Inflation Nowcast",
         lambda: _load_series("CLEVCPYC INDEX:PX_LAST"), I,
         "Cleveland Fed inflation nowcast", False),
        ("Sticky CPI 3M Ann",
         lambda: _load_series("SCPIS3MO INDEX:PX_LAST"), I,
         "Atlanta Fed Sticky CPI 3-month annualized", False),

        # -- New [N]: Inflation expectations / swaps -------------------
        ("5Y Breakeven",
         lambda: _load_series("T5YIE:PX_LAST"), I,
         "US 5-year breakeven inflation rate", False),
        ("5Y5Y Forward Inflation Swap",
         lambda: _load_series("FWISUS55 INDEX:PX_LAST"), I,
         "US 5Y5Y forward inflation expectation swap", False),
        ("1Y Inflation Swap",
         lambda: _load_series("USSWIT1 CURNCY:PX_LAST"), I,
         "US 1-year inflation swap rate", False),
        ("2Y Inflation Swap",
         lambda: _load_series("USSWIT2 CURNCY:PX_LAST"), I,
         "US 2-year inflation swap rate", False),
        ("Euro 5Y5Y Forward Swap",
         lambda: _load_series("FWISEU55 INDEX:PX_LAST"), I,
         "Eurozone 5Y5Y forward inflation swap", False),

        # -- New [N]: Citi Inflation Surprise family -------------------
        ("Citi Inflation Surprise US",
         lambda: _load_series("CSIIUSD INDEX:PX_LAST"), I,
         "Citi Inflation Surprise Index - US", False),
        ("Citi Inflation Surprise EZ",
         lambda: _load_series("EUZPRCSIIEUR:PX_LAST"), I,
         "Citi Inflation Surprise Index - Eurozone", False),
        ("Citi Inflation Surprise UK",
         lambda: _load_series("GBPRCSIIGBP:PX_LAST"), I,
         "Citi Inflation Surprise Index - UK", False),
        ("Citi Inflation Surprise JP",
         lambda: _load_series("JPPRCSIIJPY:PX_LAST"), I,
         "Citi Inflation Surprise Index - Japan", False),
        ("Citi Inflation Surprise G10",
         lambda: _load_series("WDPRCSIIG10:PX_LAST"), I,
         "Citi Inflation Surprise Index - G10", False),
        ("Citi Inflation Surprise EM",
         lambda: _load_series("WDPRCSIIEM:PX_LAST"), I,
         "Citi Inflation Surprise Index - Emerging Markets", False),
        ("Citi Inflation Surprise World",
         lambda: _load_series("WDSU8280922:PX_LAST"), I,
         "Citi Inflation Surprise Index - World", False),

        # -- New [N]: PPI / Import prices ------------------------------
        ("PPI Final Demand YoY",
         lambda: _load_series("FDIUFDYO INDEX:PX_LAST"), I,
         "PPI Final Demand year-over-year", False),
        ("PPI Core YoY",
         lambda: _load_series("FDIUSGYO INDEX:PX_LAST"), I,
         "PPI Core (ex food & energy) year-over-year", False),
        ("Import Prices YoY",
         lambda: _load_series("IMP1YOY% INDEX:PX_LAST"), I,
         "Import Price Index year-over-year", False),

        # -- New [N]: Wage / labor cost inflation ----------------------
        ("Atlanta Fed Wage Growth",
         lambda: _load_series("WGTROVER INDEX:PX_LAST"), I,
         "Atlanta Fed Wage Growth Tracker", False),
        ("Avg Hourly Earnings",
         lambda: _load_series("US.LMWAGES:PX_LAST"), I,
         "Average hourly earnings", False),
        ("ECI YoY",
         lambda: _load_series("ECI YOY INDEX:PX_LAST"), I,
         "Employment Cost Index year-over-year", False),

        # -- New [N]: CPI components -----------------------------------
        ("Shelter CPI",
         lambda: _load_series("CPSHSHLT INDEX:PX_LAST"), I,
         "CPI Shelter component", False),
        ("Used Cars CPI",
         lambda: _load_series("CUSR0000SETA02:PX_LAST"), I,
         "CPI Used Cars and Trucks index", False),

        # -- New [N]: Business price plans -----------------------------
        ("NFIB Price Plans",
         lambda: _load_series("SBOIPPNP INDEX:PX_LAST"), I,
         "NFIB net percent planning price increases", False),
        ("NFIB Higher Prices",
         lambda: _load_series("SBOIPRIC INDEX:PX_LAST"), I,
         "NFIB percent reporting higher selling prices", False),

        # -- New [N]: Consumer inflation expectations ------------------
        ("UMich 1Y Inflation Expect",
         lambda: _load_series("USSU0014396:PX_LAST"), I,
         "University of Michigan 1-year inflation expectation", False),
        ("UMich 5Y Inflation Expect",
         lambda: _load_series("USSU1094524:PX_LAST"), I,
         "University of Michigan 5-year inflation expectation", False),

        # -- New [N]: International inflation --------------------------
        ("Eurozone HICP YoY",
         lambda: _load_series("ECCPEMUY INDEX:PX_LAST"), I,
         "Eurozone Harmonized CPI year-over-year", False),
    ]


# ===================================================================
# LIQUIDITY  (52 indicators)
# ===================================================================


def _liquidity_indicators() -> list[tuple[str, Callable, str, str, bool]]:
    L = LIQUIDITY
    return [
        # -- Central bank balance sheets -------------------------------
        ("Fed Total Assets", fed_total_assets, L,
         "Federal Reserve total assets", False),
        ("Fed Assets YoY", fed_assets_yoy, L,
         "Fed total assets year-over-year change", False),
        ("Fed Assets Momentum", fed_assets_momentum, L,
         "Fed total assets rate of change momentum", False),
        ("Fed Net Liquidity", fed_net_liquidity, L,
         "Fed balance sheet minus TGA minus reverse repo", False),
        ("G4 Balance Sheet Total", g4_balance_sheet_total, L,
         "G4 central banks combined balance sheet", False),
        ("G4 Balance Sheet YoY", g4_balance_sheet_yoy, L,
         "G4 combined balance sheet year-over-year", False),
        ("CB Liquidity Composite", central_bank_liquidity_composite, L,
         "Central bank liquidity composite indicator", False),

        # -- Treasury / fiscal -----------------------------------------
        ("TGA Drawdown", tga_drawdown, L,
         "Treasury General Account drawdown - high TGA drains liquidity", True),
        ("Treasury Net Issuance", treasury_net_issuance, L,
         "Net Treasury issuance - high issuance drains liquidity", True),

        # -- Money supply ----------------------------------------------
        ("US M2", lambda: m2_us(), L,
         "US M2 money supply", False),
        ("Global M2 YoY", lambda: m2_world_total_yoy(), L,
         "Global M2 aggregate year-over-year", False),
        ("Global Liquidity YoY", lambda: global_liquidity_yoy(), L,
         "Global liquidity aggregate year-over-year", False),
        ("China M2 YoY", lambda: china_m2_yoy(), L,
         "China M2 money supply year-over-year", False),
        ("China M2 Momentum", lambda: china_m2_momentum(), L,
         "China M2 rate of change momentum", False),

        # -- Credit impulse --------------------------------------------
        ("Credit Impulse", lambda: credit_impulse(), L,
         "US credit impulse - second derivative of credit growth", False),
        ("Bank Credit Impulse", lambda: bank_credit_impulse(), L,
         "Bank lending credit impulse", False),
        ("Consumer Credit Growth", lambda: consumer_credit_growth(), L,
         "Consumer credit outstanding growth rate", False),
        ("China Credit Impulse", lambda: china_credit_impulse(), L,
         "China total social financing credit impulse", False),

        # -- Financial conditions --------------------------------------
        ("FCI US", fci_us, L,
         "US Financial Conditions Index", False),
        ("Financial Conditions Credit", financial_conditions_credit, L,
         "Credit component of financial conditions", False),

        # -- Monetary policy / rates -----------------------------------
        ("Policy Rate", policy_rate_level, L,
         "Fed Funds effective rate - higher rate tightens liquidity", True),
        ("Rate Cut Expectations", rate_cut_expectations, L,
         "Market-implied rate cut expectations", False),
        ("Rate Expectations Momentum", rate_expectations_momentum, L,
         "Momentum of rate cut expectations", False),
        ("Rate Cut Probability Proxy", rate_cut_probability_proxy, L,
         "Proxy for probability of next rate cut", False),
        ("Term Premium", term_premium_proxy, L,
         "Term premium proxy - higher premium tightens conditions", True),
        ("G4 Rate Divergence", global_rate_divergence, L,
         "G4 policy rate divergence - wider divergence tightens", True),

        # -- Yield curve -----------------------------------------------
        ("US 3M10Y", us_3m10y, L,
         "US 3-month vs 10-year yield spread", False),
        ("US 2s10s", us_2s10s, L,
         "US 2-year vs 10-year yield spread", False),
        ("US 10Y Real", us_10y_real, L,
         "US 10-year real yield - higher real yield tightens", True),

        # -- EM / China policy -----------------------------------------
        ("PBoC Easing Proxy", lambda: pboc_easing_proxy(), L,
         "PBoC monetary easing proxy", False),
        ("EM Sovereign Spread", em_sovereign_spread, L,
         "EM sovereign bond spread - wider spread = tighter conditions", True),
        ("Margin Debt YoY", margin_debt_yoy, L,
         "NYSE margin debt year-over-year change", False),

        # -- New [N]: Fed balance sheet detail -------------------------
        ("Treasury Securities Held",
         lambda: _load_series("WSHOSHO:PX_LAST"), L,
         "Fed holdings of Treasury securities", False),
        ("US M2 Level (Bloomberg)",
         lambda: _load_series("M2 INDEX:PX_LAST"), L,
         "US M2 money stock level from Bloomberg", False),
        ("ECB M2 YoY",
         lambda: _load_series("ECMSM2Y INDEX:PX_LAST"), L,
         "ECB M2 money supply year-over-year", False),

        # -- New [N]: Bank lending / credit ----------------------------
        ("Senior Loan Officer Survey",
         lambda: _load_series("DRTSCIS:PX_LAST"), L,
         "Senior Loan Officer Survey tightening - higher = tighter", True),
        ("Commercial Paper Outstanding",
         lambda: _load_series("COMPOUT:PX_LAST"), L,
         "Commercial paper outstanding", False),
        ("Bank Loans & Leases",
         lambda: _load_series("TOTLL:PX_LAST"), L,
         "Total bank loans and leases", False),
        ("Business Loans",
         lambda: _load_series("BUSLOANS:PX_LAST"), L,
         "Commercial and industrial loans at banks", False),
        ("Consumer Revolving Credit",
         lambda: _load_series("CCLACBW027SBOG:PX_LAST"), L,
         "Consumer revolving credit outstanding", False),
        ("Real Estate Loans",
         lambda: _load_series("REALLN:PX_LAST"), L,
         "Real estate loans at commercial banks", False),

        # -- New [N]: Financial conditions indices ---------------------
        ("Bloomberg US FCI",
         lambda: _load_series("BFCIUS INDEX:PX_LAST"), L,
         "Bloomberg US Financial Conditions Index", False),
        ("Chicago Fed NFCI",
         lambda: _load_series("NFCIINDX:PX_LAST"), L,
         "Chicago Fed National Financial Conditions Index", False),
        ("Chicago Fed NFCI Credit",
         lambda: _load_series("NFCICRDT:PX_LAST"), L,
         "Chicago Fed NFCI credit sub-index", False),

        # -- New [N]: Policy rates -------------------------------------
        ("ECB Deposit Rate",
         lambda: _load_series("EUORDEPO INDEX:PX_LAST"), L,
         "ECB deposit facility rate - higher = tighter", True),
        ("1Y Real Interest Rate",
         lambda: _load_series("REAINTRATREARAT1YE:PX_LAST"), L,
         "1-year real interest rate - higher = tighter", True),
        ("5Y Real Yield",
         lambda: _load_series("DFII5:PX_LAST"), L,
         "5-year TIPS real yield - higher = tighter", True),
        ("Real 10Y Core CPI Based",
         lambda: _load_series("RR10CUS INDEX:PX_LAST"), L,
         "Real 10Y yield (core CPI based) - higher = tighter", True),

        # -- New [N]: EM liquidity -------------------------------------
        ("EMBI Global Spread",
         lambda: _load_series("JPEIGLSP INDEX:PX_LAST"), L,
         "JP Morgan EMBI Global spread - wider = tighter", True),
        ("EM Currency Index",
         lambda: _load_series("FXJPEMCS INDEX:PX_LAST"), L,
         "JP Morgan EM Currency Index", False),

        # -- New [N]: Reserves / China lending -------------------------
        ("Reserve Balances",
         lambda: _load_series("FARWCUR INDEX:PX_LAST"), L,
         "Reserve balances held at Federal Reserve Banks", False),
        ("China New Loans",
         lambda: _load_series("CKAJJU:PX_LAST"), L,
         "China new yuan loans", False),
    ]


# ===================================================================
# TACTICAL  (64 indicators)
# ===================================================================


def _tactical_indicators() -> list[tuple[str, Callable, str, str, bool]]:
    T = TACTICAL
    return [
        # -- Volatility surface ----------------------------------------
        ("VIX", lambda: vix(freq="W"), T,
         "CBOE VIX - contrarian signal, NOT inverted", False),
        ("VIX Term Structure", vix_term_structure, T,
         "VIX vs VIX3M term structure", False),
        ("VIX Term Spread", vix_term_spread, T,
         "VIX term structure spread", False),
        ("VIX-Realized Vol Spread", vix_realized_vol_spread, T,
         "Implied vs realized volatility gap", False),
        ("Vol Risk Premium Z", vol_risk_premium_zscore, T,
         "Volatility risk premium z-score", False),
        ("SKEW Index", skew_index, T,
         "CBOE SKEW Index - tail risk pricing", False),
        ("SKEW Z-Score", skew_zscore, T,
         "SKEW Index z-score", False),
        ("VVIX/VIX Ratio", vvix_vix_ratio, T,
         "Vol-of-vol to VIX ratio", False),
        ("Gamma Exposure Proxy", gamma_exposure_proxy, T,
         "Market maker gamma exposure proxy", False),
        ("Realized Vol Regime", realized_vol_regime, T,
         "Realized volatility regime - high vol is bearish", True),

        # -- Credit spreads --------------------------------------------
        ("HY Spread", hy_spread, T,
         "High yield OAS spread - wider = risk-off", True),
        ("IG Spread", ig_spread, T,
         "Investment grade OAS spread - wider = risk-off", True),
        ("BBB Spread", bbb_spread, T,
         "BBB corporate spread - wider = risk-off", True),
        ("HY/IG Ratio", hy_ig_ratio, T,
         "High yield to IG spread ratio - higher = stress", True),
        ("HY Spread Momentum", lambda: hy_spread_momentum(), T,
         "High yield spread rate of change - rising = bearish", True),
        ("HY Spread Velocity", lambda: hy_spread_velocity(), T,
         "High yield spread acceleration - rising = bearish", True),
        ("IG/HY Compression", ig_hy_compression, T,
         "IG-HY spread compression indicator", False),
        ("Credit Stress Index", lambda: credit_stress_index(), T,
         "Composite credit stress gauge - higher = stress", True),
        ("Credit Cycle Phase", credit_cycle_phase, T,
         "Credit cycle phase indicator", False),

        # -- Financial stress ------------------------------------------
        ("FCI Stress", fci_stress, T,
         "Financial conditions stress indicator - higher = stress", True),
        ("Credit-Equity Divergence", credit_equity_divergence, T,
         "Credit vs equity market divergence - divergence = warning", True),

        # -- Sentiment / positioning -----------------------------------
        ("Put/Call Z-Score", put_call_zscore, T,
         "Put/call ratio z-score - contrarian, NOT inverted", False),
        ("ERP Z-Score", erp_zscore, T,
         "Equity risk premium z-score", False),
        ("Risk Appetite", risk_appetite, T,
         "Credit-spread-based risk appetite index", False),
        ("Risk On/Off Breadth", risk_on_off_breadth, T,
         "Breadth of risk-on vs risk-off asset moves", False),

        # -- Sector / factor rotation ----------------------------------
        ("US Sector Breadth", us_sector_breadth, T,
         "US sector positive momentum breadth", False),
        ("US Sector Dispersion", us_sector_dispersion, T,
         "US sector return dispersion", False),
        ("Momentum Breadth", momentum_breadth, T,
         "Cross-asset momentum breadth", False),
        ("Momentum Composite", momentum_composite, T,
         "Cross-asset momentum composite score", False),
        ("Risk Rotation Index", risk_rotation_index, T,
         "Risk-on / risk-off fund flow rotation", False),
        ("Equity/Bond Flow Proxy", lambda: equity_bond_flow_ratio(), T,
         "Equity vs bond fund flow ratio proxy", False),

        # -- Correlation / diversification -----------------------------
        ("Eq/Bond Correlation Z", equity_bond_corr_zscore, T,
         "Equity-bond correlation z-score", False),
        ("Safe Haven Demand", safe_haven_demand, T,
         "Safe haven vs risk asset relative performance - high = fear", True),
        ("Tail Risk Index", tail_risk_index, T,
         "Composite tail risk indicator - high = tail risk", True),
        ("Cross-Asset Correlation", cross_asset_correlation, T,
         "Average pairwise cross-asset correlation - high = crisis", True),
        ("Diversification Index", diversification_index, T,
         "Portfolio diversification benefit index", False),
        ("Correlation Surprise", correlation_surprise, T,
         "Short-term vs long-term correlation divergence", False),

        # -- FX / Positioning ------------------------------------------
        ("Dollar Index", lambda: dollar_index(freq="W"), T,
         "DXY Dollar Index - strong dollar is risk-off", True),
        ("CFTC Extreme Count", cftc_extreme_count, T,
         "Count of CFTC positioning at extremes", False),

        # -- CFTC individual positions ---------------------------------
        ("CFTC SPX Net", lambda: _cftc_position("S&P500"), T,
         "CFTC non-commercial net positioning in S&P 500", False),
        ("CFTC USD Net", lambda: _cftc_position("USD"), T,
         "CFTC non-commercial net positioning in USD", False),
        ("CFTC Gold Net", lambda: _cftc_position("Gold"), T,
         "CFTC non-commercial net positioning in gold", False),
        ("CFTC 10Y Net", lambda: _cftc_position("UST-10Y"), T,
         "CFTC non-commercial net positioning in 10Y Treasuries", False),
        ("CFTC JPY Net", lambda: _cftc_position("JPY"), T,
         "CFTC non-commercial net positioning in JPY", False),

        # -- New [N]: Volatility indices -------------------------------
        ("VXN (Nasdaq Vol)",
         lambda: _load_series("VXN INDEX:PX_LAST"), T,
         "CBOE Nasdaq 100 Volatility Index", False),
        ("RVX (Russell Vol)",
         lambda: _load_series("RVX INDEX:PX_LAST"), T,
         "CBOE Russell 2000 Volatility Index", False),
        ("OVX (Oil Vol)",
         lambda: _load_series("OVX INDEX:PX_LAST"), T,
         "CBOE Crude Oil Volatility Index", False),
        ("GVZ (Gold Vol)",
         lambda: _load_series("GVZ INDEX:PX_LAST"), T,
         "CBOE Gold Volatility Index", False),

        # -- New [N]: Bloomberg credit OAS -----------------------------
        ("Bloomberg HY OAS",
         lambda: _load_series("LF98OAS INDEX:PX_LAST"), T,
         "Bloomberg US Corporate High Yield OAS - wider = stress", True),
        ("Bloomberg IG OAS",
         lambda: _load_series("LUACOAS INDEX:PX_LAST"), T,
         "Bloomberg US Corporate Investment Grade OAS - wider = stress", True),
        ("CMBS OAS",
         lambda: _load_series("LUCMOAS INDEX:PX_LAST"), T,
         "Bloomberg CMBS OAS - wider = stress", True),
        ("MBS OAS",
         lambda: _load_series("LUMSOAS INDEX:PX_LAST"), T,
         "Bloomberg MBS OAS - wider = stress", True),

        # -- New [N]: Options volume -----------------------------------
        ("CBOE Put Volume",
         lambda: _load_series("OPIXEQTP INDEX:PX_LAST"), T,
         "CBOE total equity put volume", False),
        ("CBOE Call Volume",
         lambda: _load_series("OPIXEQTC INDEX:PX_LAST"), T,
         "CBOE total equity call volume", False),

        # -- New [N]: CFTC additional ----------------------------------
        ("CFTC 2Y Treasury Net",
         lambda: _load_series("CFTC_UST2Y_NET"), T,
         "CFTC non-commercial net positioning in 2Y Treasuries", False),
        ("CFTC EUR Net",
         lambda: _load_series("CFTC_EUR_NET"), T,
         "CFTC non-commercial net positioning in EUR", False),
        ("CFTC Oil Net",
         lambda: _load_series("CFTC_OIL_NET"), T,
         "CFTC non-commercial net positioning in crude oil", False),

        # -- New [N]: Business / sentiment surveys ---------------------
        ("NFIB Profits",
         lambda: _load_series("SBOIPROF INDEX:PX_LAST"), T,
         "NFIB net percent expecting higher real sales / profits", False),

        # -- New [N]: Gold demand --------------------------------------
        ("Gold ETF Demand",
         lambda: _load_series("SGLDWDEQ INDEX:PX_LAST"), T,
         "Gold ETF demand in tonnes", False),
        ("CB Gold Demand",
         lambda: _load_series("SGLDWDUQ INDEX:PX_LAST"), T,
         "Central bank gold demand in tonnes", False),

        # -- New [N]: Macro risk indices -------------------------------
        ("Citi Macro Risk ST",
         lambda: _load_series("WDPRMRIST INDEX:PX_LAST"), T,
         "Citi Macro Risk Index short-term - higher = risk", True),
        ("Citi Macro Risk LT",
         lambda: _load_series("WDPRMRILT INDEX:PX_LAST"), T,
         "Citi Macro Risk Index long-term - higher = risk", True),
        ("Citi EM Macro Risk",
         lambda: _load_series("MRIEM INDEX:PX_LAST"), T,
         "Citi EM Macro Risk Index - higher = risk", True),

        # -- New [N]: Market internals ---------------------------------
        ("NYSE Down Volume",
         lambda: _load_series("DVOLNYE INDEX:PX_LAST"), T,
         "NYSE declining volume - higher = selling pressure", True),
    ]
