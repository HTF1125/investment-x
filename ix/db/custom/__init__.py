from ix.db.custom.oecd import (
    OecdCliDiffusionIndex,
    NumOfOECDLeadingPositiveMoM,
    NumOfOecdCliMoMPositiveEM,
    oecd_cli_regime,
    oecd_cli_diffusion_world,
    oecd_cli_diffusion_developed,
    oecd_cli_diffusion_emerging,
    OECD_CLI_CODES,
    OECD_CLI_EM_CODES,
)
from ix.db.custom.pmi import (
    pmi_manufacturing_diffusion,
    pmi_services_diffusion,
    pmi_manufacturing_regime,
    pmi_services_regime,
    NumOfPmiMfgPositiveMoM,
    NumOfPmiServicesPositiveMoM,
    PMI_Manufacturing_Regime,
    PMI_Services_Regime,
    PMI_MANUFACTURING_CODES,
    PMI_SERVICES_CODES,
)
from ix.db.custom.fci import (
    fci_us,
    fci_kr,
    fci_stress,
    FinancialConditionsIndexUS,
    financial_conditions_us,
    FinancialConditionsKR,
    FinancialConditionsIndex1,
)
from ix.db.custom.liquidity import (
    FedNetLiquidity,
    fed_net_liquidity,
    M2,
    m2_us,
    m2_eu,
    m2_uk,
    m2_cn,
    m2_jp,
    m2_kr,
    m2_ch,
    m2_ca,
    m2_world,
    m2_world_total,
    m2_world_total_yoy,
    m2_world_contribution,
    credit_impulse,
    global_liquidity_yoy,
)
from ix.db.custom.positions import (
    investor_positions_net,
    investor_positions_vs_trend,
    usd_open_interest,
    USD_Open_Interest,
    InvestorPositionsvsTrend,
)
from ix.db.custom.indices import local_indices_performance, LocalIndices
from ix.db.custom.capex import (
    ai_capex_ntma,
    ai_capex_ltma,
    ai_capex_q,
    ai_capex_qoq,
    ai_capex_total_qoq,
    ai_capex_total_yoy,
)
from ix.db.custom.seasonality import (
    CalendarYearSeasonality,
    calendar_year_seasonality,
    calendar_year_seasonality_rebased,
)
from ix.db.custom.macro import macro_data
from ix.db.custom.earnings import (
    regional_eps_momentum,
    sector_eps_momentum,
    regional_eps_breadth,
    sector_eps_breadth,
    spx_revision_ratio,
    spx_revision_breadth,
    EarningsGrowth_NTMA,
)
from ix.db.custom.rates import (
    us_2s10s,
    us_3m10y,
    us_2s30s,
    kr_2s10s,
    us_10y_real,
    us_10y_breakeven,
    hy_spread,
    ig_spread,
    bbb_spread,
    hy_ig_ratio,
    spread_zscore,
    risk_appetite,
)
from ix.db.custom.sentiment import (
    cesi_data,
    cesi_breadth,
    cesi_momentum,
    cftc_net,
    cftc_zscore,
    cftc_extreme_count,
    put_call_raw,
    put_call_smoothed,
    put_call_zscore,
)
from ix.db.custom.ism import (
    ism_manufacturing_data,
    ism_services_data,
    ism_new_orders,
    ism_manufacturing_breadth,
    ism_services_breadth,
    ism_new_orders_minus_inventories,
    ism_new_orders_minus_customers_inventories,
    ism_manufacturing_momentum_breadth,
)
from ix.db.custom.korea import (
    korea_oecd_cli,
    korea_pmi_manufacturing,
    korea_exports_yoy,
    korea_semi_exports_yoy,
    korea_consumer_confidence,
    korea_usdkrw,
    korea_bond_10y,
)
from ix.db.custom.cross_asset import (
    dollar_index,
    copper_gold_ratio,
    em_vs_dm,
    china_sse,
    nikkei,
    vix,
    commodities_crb,
    baltic_dry_index,
    real_rate_differential,
)
from ix.db.custom.equity_valuation import (
    spx_earnings_yield,
    spx_erp_nominal,
    spx_erp_real,
    erp_zscore,
    erp_momentum,
    nasdaq_spx_relative_valuation,
)
from ix.db.custom.monetary_policy import (
    rate_cut_expectations,
    rate_expectations_momentum,
    rate_expectations_zscore,
    term_premium_proxy,
    policy_rate_level,
)
from ix.db.custom.global_trade import (
    asian_exports_yoy,
    asian_exports_diffusion,
    asian_exports_momentum,
    korea_semi_share,
    global_trade_composite,
)
from ix.db.custom.inflation import (
    inflation_momentum,
    inflation_surprise,
    breakeven_momentum,
    oil_leading_cpi,
    commodity_inflation_pressure,
)
from ix.db.custom.intermarket import (
    equity_bond_correlation,
    risk_on_off_breadth,
    small_large_cap_ratio,
    cyclical_defensive_ratio,
    credit_equity_divergence,
    vix_realized_vol_spread,
)
from ix.db.custom.sector_rotation import (
    us_sector_relative_strength,
    us_cyclical_defensive_ratio,
    us_sector_breadth,
    us_sector_dispersion,
    kr_sector_relative_strength,
    kr_cyclical_defensive_ratio,
    kr_sector_breadth,
    kr_sector_dispersion,
    kr_tech_vs_us_tech,
    kr_financials_vs_us_financials,
    kr_export_vs_domestic,
)

from typing import Union
import pandas as pd


# ── Backward-compatible namespace classes for safe_expression / saved charts ─


class EarningsIndicators:
    regional_eps_momentum = staticmethod(regional_eps_momentum)
    sector_eps_momentum = staticmethod(sector_eps_momentum)
    regional_eps_breadth = staticmethod(regional_eps_breadth)
    sector_eps_breadth = staticmethod(sector_eps_breadth)
    spx_revision_ratio = staticmethod(spx_revision_ratio)
    spx_revision_breadth = staticmethod(spx_revision_breadth)


class YieldCurve:
    us_2s10s = staticmethod(us_2s10s)
    us_3m10y = staticmethod(us_3m10y)
    us_2s30s = staticmethod(us_2s30s)
    kr_2s10s = staticmethod(kr_2s10s)


class RealRates:
    us_10y_real = staticmethod(us_10y_real)
    us_10y_breakeven = staticmethod(us_10y_breakeven)


class CreditSpreads:
    hy_spread = staticmethod(hy_spread)
    ig_spread = staticmethod(ig_spread)
    bbb_spread = staticmethod(bbb_spread)
    hy_ig_ratio = staticmethod(hy_ig_ratio)
    spread_zscore = staticmethod(spread_zscore)


class RiskAppetite:
    index = staticmethod(risk_appetite)


class CitiSurprise:
    data = staticmethod(cesi_data)
    breadth = staticmethod(cesi_breadth)
    momentum = staticmethod(cesi_momentum)


class CFTCPositioning:
    net = staticmethod(cftc_net)
    zscore = staticmethod(cftc_zscore)
    extreme_count = staticmethod(cftc_extreme_count)


class PutCallRatio:
    raw = staticmethod(put_call_raw)
    smoothed = staticmethod(put_call_smoothed)
    zscore = staticmethod(put_call_zscore)


class ISMIndicators:
    manufacturing_data = staticmethod(ism_manufacturing_data)
    services_data = staticmethod(ism_services_data)
    new_orders = staticmethod(ism_new_orders)
    manufacturing_breadth = staticmethod(ism_manufacturing_breadth)
    services_breadth = staticmethod(ism_services_breadth)
    new_orders_minus_inventories = staticmethod(ism_new_orders_minus_inventories)
    new_orders_minus_customers_inventories = staticmethod(ism_new_orders_minus_customers_inventories)
    manufacturing_momentum_breadth = staticmethod(ism_manufacturing_momentum_breadth)


class InvestorPositions:
    net = staticmethod(investor_positions_net)
    vs_trend = staticmethod(investor_positions_vs_trend)
    usd_open_interest = staticmethod(usd_open_interest)


class LocalIndicesData:
    performance = staticmethod(local_indices_performance)


class AiCapex:
    FE_CAPEX_NTMA = staticmethod(ai_capex_ntma)
    FE_CAPEX_LTMA = staticmethod(ai_capex_ltma)
    FE_CAPEX_Q = staticmethod(ai_capex_q)
    FE_CAPEX_QOQ = staticmethod(ai_capex_qoq)
    TOTAL_FE_CAPEX_QOQ = staticmethod(ai_capex_total_qoq)
    TOTAL_FE_CAPEX_YOY = staticmethod(ai_capex_total_yoy)


class KoreaLeading:
    oecd_cli = staticmethod(korea_oecd_cli)
    pmi_manufacturing = staticmethod(korea_pmi_manufacturing)
    exports_yoy = staticmethod(korea_exports_yoy)
    semi_exports_yoy = staticmethod(korea_semi_exports_yoy)
    consumer_confidence = staticmethod(korea_consumer_confidence)


class KoreaFinancial:
    usdkrw = staticmethod(korea_usdkrw)
    bond_10y = staticmethod(korea_bond_10y)


class CrossAsset:
    dollar_index = staticmethod(dollar_index)
    copper_gold_ratio = staticmethod(copper_gold_ratio)
    em_vs_dm = staticmethod(em_vs_dm)
    china_sse = staticmethod(china_sse)
    nikkei = staticmethod(nikkei)
    vix = staticmethod(vix)
    commodities_crb = staticmethod(commodities_crb)


class FinancialConditionsIndex:
    us = staticmethod(fci_us)
    kr = staticmethod(fci_kr)
    stress = staticmethod(fci_stress)


class PmiDiffusionIndex:
    manufacturing_diffusion = staticmethod(pmi_manufacturing_diffusion)
    services_diffusion = staticmethod(pmi_services_diffusion)
    manufacturing_regime = staticmethod(pmi_manufacturing_regime)
    services_regime = staticmethod(pmi_services_regime)


class EquityValuation:
    earnings_yield = staticmethod(spx_earnings_yield)
    erp_nominal = staticmethod(spx_erp_nominal)
    erp_real = staticmethod(spx_erp_real)
    erp_zscore = staticmethod(erp_zscore)
    erp_momentum = staticmethod(erp_momentum)
    nasdaq_spx = staticmethod(nasdaq_spx_relative_valuation)


class MonetaryPolicy:
    rate_cuts = staticmethod(rate_cut_expectations)
    rate_momentum = staticmethod(rate_expectations_momentum)
    rate_zscore = staticmethod(rate_expectations_zscore)
    term_premium = staticmethod(term_premium_proxy)
    policy_rate = staticmethod(policy_rate_level)


class GlobalTrade:
    exports_yoy = staticmethod(asian_exports_yoy)
    diffusion = staticmethod(asian_exports_diffusion)
    momentum = staticmethod(asian_exports_momentum)
    semi_share = staticmethod(korea_semi_share)
    composite = staticmethod(global_trade_composite)


class InflationIndicators:
    momentum = staticmethod(inflation_momentum)
    surprise = staticmethod(inflation_surprise)
    breakeven_momentum = staticmethod(breakeven_momentum)
    oil_leading_cpi = staticmethod(oil_leading_cpi)
    commodity_pressure = staticmethod(commodity_inflation_pressure)


class IntermarketSignals:
    equity_bond_corr = staticmethod(equity_bond_correlation)
    risk_on_breadth = staticmethod(risk_on_off_breadth)
    small_large_cap = staticmethod(small_large_cap_ratio)
    cyclical_defensive = staticmethod(cyclical_defensive_ratio)
    credit_equity_div = staticmethod(credit_equity_divergence)
    vix_realized_spread = staticmethod(vix_realized_vol_spread)


class USSectorRotation:
    relative_strength = staticmethod(us_sector_relative_strength)
    cyclical_defensive = staticmethod(us_cyclical_defensive_ratio)
    breadth = staticmethod(us_sector_breadth)
    dispersion = staticmethod(us_sector_dispersion)


class KRSectorRotation:
    relative_strength = staticmethod(kr_sector_relative_strength)
    cyclical_defensive = staticmethod(kr_cyclical_defensive_ratio)
    breadth = staticmethod(kr_sector_breadth)
    dispersion = staticmethod(kr_sector_dispersion)
    tech_vs_us_tech = staticmethod(kr_tech_vs_us_tech)
    financials_vs_us = staticmethod(kr_financials_vs_us_financials)
    export_vs_domestic = staticmethod(kr_export_vs_domestic)


# ── CustomSeries dispatcher ─────────────────────────────────────────────────


def CustomSeries(code: str) -> Union[pd.Series, pd.DataFrame, None]:
    """Return custom calculated series based on code.

    Returns pd.Series or pd.DataFrame depending on the code requested.
    Returns None if code is not recognized.
    """
    if code == "GlobalGrowthRegime-Expansion":
        return PMI_Manufacturing_Regime()["Expansion"]
    if code == "GlobalGrowthRegime-Slowdown":
        return PMI_Manufacturing_Regime()["Slowdown"]
    if code == "GlobalGrowthRegime-Contraction":
        return PMI_Manufacturing_Regime()["Contraction"]
    if code == "GlobalGrowthRegime-Recovery":
        return PMI_Manufacturing_Regime()["Recovery"]
    if code == "NumOfOECDLeadingPositiveMoM":
        return NumOfOECDLeadingPositiveMoM()
    if code == "NumOfPmiPositiveMoM":
        return NumOfPmiMfgPositiveMoM()
    if code == "GlobalM2":
        return m2_world_total()
    if code == "LocalIndices2":
        return local_indices_performance()
    if code == "FedNetLiquidity":
        return fed_net_liquidity()
    if code == "OecdCliRegime-Expansion":
        return oecd_cli_regime()["Expansion"]
    if code == "OecdCliRegime-Slowdown":
        return oecd_cli_regime()["Slowdown"]
    if code == "OecdCliRegime-Contraction":
        return oecd_cli_regime()["Contraction"]
    if code == "OecdCliRegime-Recovery":
        return oecd_cli_regime()["Recovery"]
    return None


def GetChart(name: str):
    """Legacy helper removed with charts table decommission; always returns None."""
    return None
