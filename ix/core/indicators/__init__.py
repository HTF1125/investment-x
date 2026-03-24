"""Macro indicator library — consolidated into domain modules.

All public functions are re-exported here for backward compatibility.
The safe_expression DSL discovers names via ``dir(ix.core.indicators)``.
"""
from __future__ import annotations

from typing import Union
import pandas as pd

# ── Auto-export all public names from each domain module ───────────────────
# Adding a new function to any module automatically makes it available
# in the chart expression DSL — no manual registration needed.

from ix.core.indicators.growth import *          # noqa: F401,F403
from ix.core.indicators.fci import *             # noqa: F401,F403
from ix.core.indicators.liquidity import *        # noqa: F401,F403
from ix.core.indicators.central_bank import *     # noqa: F401,F403
from ix.core.indicators.rates import *            # noqa: F401,F403
from ix.core.indicators.credit_deep import *      # noqa: F401,F403
from ix.core.indicators.earnings import *         # noqa: F401,F403
from ix.core.indicators.equity import *           # noqa: F401,F403
from ix.core.indicators.sentiment import *        # noqa: F401,F403
from ix.core.indicators.volatility import *       # noqa: F401,F403
from ix.core.indicators.cross_asset import *      # noqa: F401,F403
from ix.core.indicators.inflation import *        # noqa: F401,F403
from ix.core.indicators.economy import *          # noqa: F401,F403
from ix.core.indicators.regional import *         # noqa: F401,F403
from ix.core.indicators.real_assets import *      # noqa: F401,F403
from ix.core.indicators.policy import *           # noqa: F401,F403
from ix.core.indicators.macro import *            # noqa: F401,F403


# ── Namespace classes for chart expression DSL ─────────────────────────────
# These provide grouped access: e.g. ``YieldCurve.us_2s10s()``
# All function names referenced below are imported by the wildcard imports above.


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
    inversion_duration = staticmethod(yield_curve_inversion_duration)
    inversion_depth = staticmethod(yield_curve_inversion_depth)


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
    lead_composite = staticmethod(ism_lead_composite)


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
    lei = staticmethod(korea_lei)
    lei_yoy = staticmethod(korea_lei_yoy)
    recession_risk = staticmethod(korea_recession_risk)


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
    baltic_capesize = staticmethod(baltic_capesize_index)
    baltic_capesize_yoy = staticmethod(baltic_capesize_yoy)


class FinancialConditionsIndex:
    us = staticmethod(fci_us)
    us_components = staticmethod(fci_us_components)
    kr = staticmethod(fci_kr)
    stress = staticmethod(fci_stress)
    ism_lead = staticmethod(fci_ism_lead)
    stlfsi = staticmethod(stlfsi)
    kcfsi = staticmethod(kcfsi)
    fed_stress = staticmethod(fed_stress_composite)


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
    fear_composite = staticmethod(market_fear_composite)
    move_vix = staticmethod(move_vix_ratio)
    move_vix_z = staticmethod(move_vix_ratio_zscore)


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


class VolatilitySurface:
    term_structure = staticmethod(vix_term_structure)
    term_spread = staticmethod(vix_term_spread)
    skew = staticmethod(skew_index)
    skew_zscore = staticmethod(skew_zscore)
    risk_premium = staticmethod(vol_risk_premium)
    risk_premium_zscore = staticmethod(vol_risk_premium_zscore)
    vvix = staticmethod(vol_of_vol)
    vvix_vix_ratio = staticmethod(vvix_vix_ratio)
    gamma_proxy = staticmethod(gamma_exposure_proxy)
    realized_regime = staticmethod(realized_vol_regime)


class FundFlows:
    margin_debt = staticmethod(margin_debt)
    margin_debt_yoy = staticmethod(margin_debt_yoy)
    margin_vs_spx = staticmethod(margin_debt_vs_spx)
    risk_rotation = staticmethod(risk_rotation_index)
    equity_bond_flow = staticmethod(equity_bond_flow_ratio)
    em_flow = staticmethod(em_flow_proxy)
    commodity_flow = staticmethod(commodity_flow_proxy)
    bank_credit_impulse = staticmethod(bank_credit_impulse)
    consumer_credit = staticmethod(consumer_credit_growth)


class CreditDeep:
    stress_index = staticmethod(credit_stress_index)
    distress_proxy = staticmethod(hy_distress_proxy)
    spread_momentum = staticmethod(hy_spread_momentum)
    spread_velocity = staticmethod(hy_spread_velocity)
    leveraged_loan = staticmethod(leveraged_loan_spread)
    leveraged_loan_zscore = staticmethod(leveraged_loan_spread_zscore)
    cdx_hy = staticmethod(cdx_hy_proxy)
    cdx_ig = staticmethod(cdx_ig_proxy)
    cycle_phase = staticmethod(credit_cycle_phase)
    ig_hy_compression = staticmethod(ig_hy_compression)
    conditions = staticmethod(financial_conditions_credit)
    sloos = staticmethod(sloos_lending_standards)
    sloos_cc = staticmethod(sloos_credit_card_standards)
    sloos_composite = staticmethod(sloos_composite)


class Nowcasting:
    gdpnow = staticmethod(gdpnow)
    wei = staticmethod(weekly_economic_index)
    wei_momentum = staticmethod(wei_momentum)
    ads = staticmethod(ads_business_conditions)
    initial_claims = staticmethod(initial_claims)
    claims_4wma = staticmethod(initial_claims_4wma)
    continued_claims = staticmethod(continued_claims)
    claims_ratio = staticmethod(claims_ratio)
    ip_yoy = staticmethod(industrial_production_yoy)
    capacity_util = staticmethod(capacity_utilization)
    recession_prob = staticmethod(recession_probability)
    recession_signal = staticmethod(recession_probability_signal)
    lei = staticmethod(conference_board_lei)
    lei_yoy = staticmethod(lei_yoy)
    lei_recession = staticmethod(lei_recession_signal)
    coincident_lagging = staticmethod(coincident_lagging_ratio)
    coincident_lagging_yoy = staticmethod(coincident_lagging_ratio_yoy)
    composite = staticmethod(nowcast_composite)
    recession_risk = staticmethod(recession_risk_composite)


class ChinaEM:
    credit_impulse = staticmethod(china_credit_impulse)
    m2_yoy = staticmethod(china_m2_yoy)
    m2_momentum = staticmethod(china_m2_momentum)
    pmi_composite = staticmethod(china_pmi_composite)
    pmi_momentum = staticmethod(china_pmi_momentum)
    pboc_easing = staticmethod(pboc_easing_proxy)
    em_spread = staticmethod(em_sovereign_spread)
    em_spread_zscore = staticmethod(em_sovereign_spread_zscore)
    em_spread_momentum = staticmethod(em_sovereign_spread_momentum)
    usdcny = staticmethod(usdcny)
    usdcny_momentum = staticmethod(usdcny_momentum)
    em_dm_momentum = staticmethod(em_dm_relative_momentum)
    em_composite = staticmethod(em_composite_indicator)


class CentralBankWatch:
    fed_assets = staticmethod(fed_total_assets)
    fed_yoy = staticmethod(fed_assets_yoy)
    fed_momentum = staticmethod(fed_assets_momentum)
    ecb_assets = staticmethod(ecb_total_assets)
    boj_assets = staticmethod(boj_total_assets)
    pboc_assets = staticmethod(pboc_total_assets)
    g4_total = staticmethod(g4_balance_sheet_total)
    g4_yoy = staticmethod(g4_balance_sheet_yoy)
    fed_funds = staticmethod(fed_funds_implied)
    rate_cut_proxy = staticmethod(rate_cut_probability_proxy)
    rate_divergence = staticmethod(global_rate_divergence)
    liquidity_composite = staticmethod(central_bank_liquidity_composite)


class AltData:
    sox = staticmethod(sox_index)
    sox_spx = staticmethod(sox_spx_ratio)
    sox_momentum = staticmethod(sox_momentum)
    semi_btb = staticmethod(semi_book_to_bill)
    housing_starts = staticmethod(housing_starts)
    housing_yoy = staticmethod(housing_starts_yoy)
    permits = staticmethod(building_permits)
    affordability = staticmethod(housing_affordability_proxy)
    mortgage = staticmethod(mortgage_rate)
    wti = staticmethod(wti_crude)
    brent = staticmethod(brent_crude)
    crack = staticmethod(crack_spread)
    oil_inventory = staticmethod(oil_inventory_proxy)
    natgas = staticmethod(natural_gas)
    gold = staticmethod(gold)
    gold_silver = staticmethod(gold_silver_ratio)
    gold_real_rate = staticmethod(gold_real_rate_relationship)
    bdi_momentum = staticmethod(baltic_dry_momentum)
    container_freight = staticmethod(container_freight_proxy)
    composite = staticmethod(alt_data_composite)


class CrossAssetFactors:
    momentum = staticmethod(cross_asset_momentum)
    momentum_breadth = staticmethod(momentum_breadth)
    momentum_composite = staticmethod(momentum_composite)
    equity_carry = staticmethod(equity_carry)
    bond_carry = staticmethod(bond_carry)
    fx_carry = staticmethod(fx_carry)
    commodity_carry = staticmethod(commodity_carry)
    carry_composite = staticmethod(carry_composite)
    equity_value = staticmethod(equity_value)
    bond_value = staticmethod(bond_value)
    fx_value = staticmethod(fx_value)
    value_composite = staticmethod(value_composite)
    factor_score = staticmethod(macro_factor_score)


class CorrelationRegime:
    eq_bond_regime = staticmethod(equity_bond_corr_regime)
    eq_bond_zscore = staticmethod(equity_bond_corr_zscore)
    cross_asset_corr = staticmethod(cross_asset_correlation_fast)
    diversification = staticmethod(diversification_index)
    corr_surprise = staticmethod(correlation_surprise)
    safe_haven = staticmethod(safe_haven_demand)
    tail_risk = staticmethod(tail_risk_index)


class EarningsDeep:
    dispersion = staticmethod(eps_estimate_dispersion)
    dispersion_zscore = staticmethod(eps_dispersion_zscore)
    surprise_persistence = staticmethod(earnings_surprise_persistence)
    momentum_score = staticmethod(earnings_momentum_score)
    guidance = staticmethod(guidance_proxy)
    guidance_momentum = staticmethod(guidance_momentum)
    yield_gap = staticmethod(earnings_yield_gap)
    regional_divergence = staticmethod(regional_earnings_divergence)
    us_vs_world = staticmethod(us_vs_world_earnings)
    composite = staticmethod(earnings_composite)


class LaborMarket:
    jolts_openings = staticmethod(jolts_job_openings)
    quits_rate = staticmethod(jolts_quits_rate)
    hires_rate = staticmethod(jolts_hires_rate)
    openings_unemployed = staticmethod(jolts_openings_unemployed_ratio)
    wage_tracker = staticmethod(atlanta_fed_wage_tracker)
    eci = staticmethod(employment_cost_index)
    eci_yoy = staticmethod(employment_cost_index_yoy)
    ulc_yoy = staticmethod(unit_labor_costs_yoy)
    productivity_yoy = staticmethod(nonfarm_productivity_yoy)
    u6 = staticmethod(u6_unemployment)
    temp = staticmethod(temp_employment)
    temp_yoy = staticmethod(temp_employment_yoy)
    composite = staticmethod(labor_market_composite)
    sahm = staticmethod(sahm_rule)
    sahm_signal = staticmethod(sahm_rule_signal)


class ConsumerHealth:
    michigan = staticmethod(michigan_sentiment)
    expectations = staticmethod(michigan_expectations)
    sentiment_momentum = staticmethod(michigan_sentiment_momentum)
    confidence = staticmethod(conference_board_confidence)
    expectations_spread = staticmethod(consumer_expectations_spread)
    retail_yoy = staticmethod(retail_sales_yoy)
    real_income = staticmethod(real_personal_income_ex_transfers)
    savings_rate = staticmethod(personal_savings_rate)
    delinquency = staticmethod(consumer_delinquency_rate)
    debt_service = staticmethod(household_debt_service_ratio)
    delinquency_momentum = staticmethod(consumer_credit_delinquency_momentum)
    composite = staticmethod(consumer_health_composite)


class MoneyMarkets:
    sofr = staticmethod(sofr_rate)
    sofr_ffr_spread = staticmethod(sofr_fed_funds_spread)
    cp_spread = staticmethod(commercial_paper_spread)
    cp_spread_zscore = staticmethod(commercial_paper_spread_zscore)
    mmf_assets = staticmethod(money_market_fund_assets)
    mmf_yoy = staticmethod(money_market_fund_yoy)
    mmf_vs_equities = staticmethod(money_market_vs_equities)
    rrp = staticmethod(reverse_repo_usage)
    rrp_momentum = staticmethod(reverse_repo_momentum)
    funding_stress = staticmethod(funding_stress_index)


class FiscalPolicy:
    deficit_gdp = staticmethod(federal_deficit_gdp)
    receipts_yoy = staticmethod(federal_receipts_yoy)
    spending_yoy = staticmethod(federal_spending_yoy)
    impulse = staticmethod(fiscal_impulse)
    debt_gdp = staticmethod(public_debt_gdp)
    interest_gdp = staticmethod(interest_payments_gdp)
    fiscal_monetary = staticmethod(fiscal_monetary_impulse)


class RealEstate:
    case_shiller = staticmethod(case_shiller_yoy)
    home_price_momentum = staticmethod(case_shiller_momentum)
    existing_sales = staticmethod(existing_home_sales)
    existing_sales_yoy = staticmethod(existing_home_sales_yoy)
    new_sales = staticmethod(new_home_sales)
    nahb = staticmethod(nahb_housing_market_index)
    cre_price = staticmethod(commercial_real_estate_price)
    purchase_apps = staticmethod(mortgage_purchase_index)
    purchase_apps_yoy = staticmethod(mortgage_purchase_yoy)
    composite = staticmethod(housing_composite)


class PolicyUncertainty:
    epu = staticmethod(economic_policy_uncertainty)
    epu_zscore = staticmethod(policy_uncertainty_zscore)
    trade = staticmethod(trade_policy_uncertainty)
    supply_chain = staticmethod(global_supply_chain_pressure)
    supply_chain_momentum = staticmethod(supply_chain_momentum)
    gpr = staticmethod(geopolitical_risk_index)
    gpr_zscore = staticmethod(geopolitical_risk_zscore)
    composite = staticmethod(uncertainty_composite)


class Transportation:
    trucks = staticmethod(truck_tonnage)
    trucks_yoy = staticmethod(truck_tonnage_yoy)
    rail = staticmethod(rail_freight)
    rail_yoy = staticmethod(rail_freight_yoy)
    air = staticmethod(air_passengers)
    air_yoy = staticmethod(air_passengers_yoy)
    vehicles = staticmethod(vehicle_sales)
    vehicles_yoy = staticmethod(vehicle_sales_yoy)
    composite = staticmethod(real_economy_transport_composite)


class EnergyInfra:
    rig_count = staticmethod(us_rig_count)
    rig_momentum = staticmethod(us_rig_count_momentum)
    spr = staticmethod(strategic_petroleum_reserve)
    spr_change = staticmethod(spr_change)
    crude_inv = staticmethod(crude_inventories)
    crude_inv_zscore = staticmethod(crude_inventories_zscore)
    crude_inv_change = staticmethod(crude_inventory_change)
    ng_storage = staticmethod(natural_gas_storage)
    ng_storage_zscore = staticmethod(natural_gas_storage_zscore)
    composite = staticmethod(energy_supply_composite)


class GlobalRates:
    german_10y = staticmethod(german_10y)
    japan_10y = staticmethod(japan_10y)
    uk_10y = staticmethod(uk_10y)
    us_de_spread = staticmethod(us_germany_spread)
    us_jp_spread = staticmethod(us_japan_spread)
    g4_dispersion = staticmethod(g4_yield_dispersion)
    global_real_rate = staticmethod(global_real_rate_composite)
    embi = staticmethod(embi_spread)
    embi_zscore = staticmethod(embi_spread_zscore)


# ── CustomSeries dispatcher ───────────────────────────────────────────────


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
