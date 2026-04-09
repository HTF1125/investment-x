"""Indicator definitions and data loading for the macro outlook model.

Each loader tuple has the shape:
    (name, fn, needs_freq, needs_weekly_resample, invert, pub_lag_weeks, monthly)

- name: display name for the indicator
- fn: callable that returns a pd.Series or pd.DataFrame
- needs_freq: whether to pass freq= to the loader
- needs_weekly_resample: whether to resample to weekly after loading
- invert: whether to negate the z-score (e.g., VIX is inversely correlated with risk-on)
- pub_lag_weeks: publication delay in weeks (shifted to avoid look-ahead bias)
- monthly: True if the indicator is released monthly (uses shorter z-score window)
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)

from ix.db.query import Series
from ix.core.indicators import (
    # Growth axis
    NumOfPmiMfgPositiveMoM,
    NumOfPmiServicesPositiveMoM,
    oecd_cli_diffusion_world,
    oecd_cli_diffusion_developed,
    oecd_cli_diffusion_emerging,
    ism_new_orders,
    ism_new_orders_minus_inventories,
    ism_services_breadth,
    ism_manufacturing_data,
    ism_manufacturing_breadth,
    ism_manufacturing_momentum_breadth,
    cesi_breadth,
    cesi_momentum,
    asian_exports_diffusion,
    asian_exports_momentum,
    global_trade_composite,
    spx_revision_ratio,
    regional_eps_breadth,
    copper_gold_ratio,
    small_large_cap_ratio,
    cyclical_defensive_ratio,
    baltic_dry_index,
    # Inflation axis
    inflation_surprise,
    inflation_momentum,
    us_10y_breakeven,
    breakeven_momentum,
    commodity_inflation_pressure,
    commodities_crb,
    # Liquidity cycle (long-term)
    fed_net_liquidity,
    tga_drawdown,
    treasury_net_issuance,
    m2_world_total_yoy,
    credit_impulse,
    global_liquidity_yoy,
    fci_us,
    us_3m10y,
    us_10y_real,
    policy_rate_level,
    rate_cut_expectations,
    rate_expectations_momentum,
    term_premium_proxy,
    # Tactical (short-term)
    risk_appetite,
    fci_stress,
    vix,
    put_call_zscore,
    risk_on_off_breadth,
    credit_equity_divergence,
    vix_realized_vol_spread,
    hy_spread,
    hy_ig_ratio,
    erp_zscore,
    dollar_index,
    us_sector_breadth,
    # Korea
    korea_oecd_cli,
    korea_exports_yoy,
    korea_pmi_manufacturing,
    korea_semi_exports_yoy,
    korea_consumer_confidence,
    kr_sector_breadth,
)


# ==============================================================================
# WRAPPER FUNCTIONS
# ==============================================================================


def _ism_prices_paid() -> pd.Series:
    """Extract ISM Prices Paid from manufacturing data."""
    try:
        df = ism_manufacturing_data()
        if "Prices Paid" in df.columns:
            return df["Prices Paid"].dropna()
    except Exception:
        logger.debug("Failed to load ISM Prices Paid", exc_info=True)
    return pd.Series(dtype=float)


def _cpi_3m_annualized() -> pd.Series:
    """CPI 3-month annualized rate -- catches inflation turning points."""
    try:
        df = inflation_momentum()
        if "CPI 3m Ann" in df.columns:
            return df["CPI 3m Ann"].dropna()
    except Exception:
        logger.debug("Failed to load CPI 3m annualized", exc_info=True)
    return pd.Series(dtype=float)


# ==============================================================================
# LOADER DEFINITIONS
# ==============================================================================
# Each tuple: (name, fn, needs_freq, needs_weekly_resample, invert, pub_lag_weeks, monthly)

GROWTH_LOADERS = [
    ("PMI Diffusion", NumOfPmiMfgPositiveMoM, False, False, False, 2, True),
    ("OECD CLI World", oecd_cli_diffusion_world, False, True, False, 4, False),
    ("OECD CLI EM", oecd_cli_diffusion_emerging, False, True, False, 4, False),
    ("ISM New Orders", ism_new_orders, False, False, False, 1, True),
    ("ISM NO-Inv Spread", ism_new_orders_minus_inventories, False, False, False, 1, True),
    ("ISM Services Breadth", ism_services_breadth, False, False, False, 1, True),
    ("CESI Breadth", cesi_breadth, False, True, False, 0, False),
    ("CESI Momentum", cesi_momentum, False, True, False, 0, False),
    ("Asian Exports Diff", asian_exports_diffusion, False, False, False, 2, True),
    ("Global Trade", global_trade_composite, False, False, False, 2, True),
    ("SPX Revision Ratio", spx_revision_ratio, False, False, False, 2, True),
    ("EPS Breadth", regional_eps_breadth, False, True, False, 2, False),
    ("Copper/Gold", copper_gold_ratio, True, False, False, 0, False),
    ("Small/Large Cap", small_large_cap_ratio, True, False, False, 0, False),
    ("Cyclical/Defensive", cyclical_defensive_ratio, True, False, False, 0, False),
    ("PMI Services Diff", NumOfPmiServicesPositiveMoM, False, False, False, 2, True),
    ("OECD CLI DM", oecd_cli_diffusion_developed, False, True, False, 4, False),
    ("ISM Mfg Breadth", ism_manufacturing_breadth, False, False, False, 1, True),
    ("ISM Mfg Momentum", ism_manufacturing_momentum_breadth, False, False, False, 1, True),
    ("Asian Exports Mom", asian_exports_momentum, False, False, False, 2, True),
    ("Baltic Dry", baltic_dry_index, True, False, False, 0, False),
]

INFLATION_LOADERS = [
    ("Inflation Surprise", inflation_surprise, False, False, False, 3, True),
    ("10Y Breakeven", us_10y_breakeven, False, True, False, 0, False),
    ("Breakeven Momentum", breakeven_momentum, False, True, False, 0, False),
    ("Commodity Pressure", commodity_inflation_pressure, False, True, False, 0, False),
    ("CRB Index", commodities_crb, True, False, False, 0, False),
    ("ISM Prices Paid", _ism_prices_paid, False, False, False, 1, True),
    ("CPI 3M Annualized", _cpi_3m_annualized, False, False, False, 3, True),
]

LIQUIDITY_LOADERS = [
    # --- Predictive indicators (|IC| > 0.05 for 13wk SPX/KOSPI fwd returns) ---
    # FCI US: NOT inverted (contrarian). Tight conditions → high z → predicts
    # HIGHER forward returns (IC=+0.156). Same logic as VIX for tactical.
    ("FCI US", fci_us, False, False, False, 0, False),
    ("Fed Net Liquidity", fed_net_liquidity, False, True, False, 0, False),
    ("US 10Y Real", us_10y_real, False, True, True, 0, False),
    # --- TGA / Fiscal flow indicators ---
    # TGA Drawdown: inverted because positive change = TGA refilling = drains liquidity
    ("TGA Drawdown", tga_drawdown, False, True, True, 0, False),
    # Treasury Net Issuance: inverted because rising issuance = supply pressure = bearish
    ("Treasury Issuance", treasury_net_issuance, False, True, True, 0, False),
    # --- Moderate signal indicators ---
    ("US 3M10Y", us_3m10y, False, True, False, 0, False),
    ("Policy Rate", policy_rate_level, False, False, True, 0, False),
    ("Rate Cut Expect", rate_cut_expectations, False, True, False, 0, False),
    ("Rate Expect Mom", rate_expectations_momentum, False, True, False, 0, False),
    ("Term Premium", term_premium_proxy, False, True, True, 0, False),
    ("Credit Impulse", credit_impulse, False, False, False, 4, True),
    # --- Low/zero IC indicators (kept for display, excluded from composite via weights) ---
    ("Global M2 YoY", m2_world_total_yoy, False, False, False, 6, True),
    ("Global Liquidity YoY", global_liquidity_yoy, False, False, False, 4, True),
]

# IC-based weights for the liquidity composite.
# Derived from Spearman rank correlation with 13-week forward equity returns
# across S&P 500 and KOSPI (20-year sample). Indicators with |IC| < 0.03
# are excluded (set to 0) to avoid noise dilution.
# Reviewed 2026-03-08. Should be re-validated periodically.
LIQUIDITY_WEIGHTS = {
    "FCI US": +0.45,           # IC ≈ +0.16 (contrarian: tight → bullish)
    "Fed Net Liquidity": +0.30,  # IC ≈ +0.10
    "US 10Y Real": +0.25,     # IC ≈ +0.09 (inverted: low real yield → bullish)
    # Excluded from composite (zero or near-zero IC for 13wk prediction):
    # Global M2 YoY, Global Liquidity YoY, US 3M10Y
}

TACTICAL_LOADERS = [
    # Pro-cyclical: positive = healthy risk environment
    ("Risk Appetite", risk_appetite, False, True, False, 0, False),
    ("Risk On/Off", risk_on_off_breadth, False, False, False, 0, False),
    ("US Sector Breadth", us_sector_breadth, False, False, False, 0, False),
    ("ERP Z-Score", erp_zscore, False, False, False, 0, False),
    # Contrarian: NOT inverted — high fear readings = bullish (buy the dip)
    # VIX spike, elevated put/call, fear premium → markets oversold → overweight
    ("VIX", vix, True, False, False, 0, False),
    ("Put/Call Z", put_call_zscore, False, False, False, 0, False),
    ("VIX-RVol Spread", vix_realized_vol_spread, False, False, False, 0, False),
    # Credit stress: inverted — wide spreads = genuine deterioration = bearish
    ("FCI Stress", fci_stress, False, True, True, 0, False),
    ("Credit-Equity Div", credit_equity_divergence, False, False, True, 0, False),
    ("HY Spread", hy_spread, False, True, True, 0, False),
    ("HY/IG Ratio", hy_ig_ratio, False, True, True, 0, False),
    ("Dollar Index", dollar_index, True, False, True, 0, False),
]

KOREA_LOADERS = [
    ("OECD CLI Korea", korea_oecd_cli, False, False, False, 4, True),
    ("Korea Exports YoY", korea_exports_yoy, False, False, False, 1, True),
    ("Korea PMI Mfg", korea_pmi_manufacturing, False, False, False, 1, True),
    ("Korea Semi Exports", korea_semi_exports_yoy, False, False, False, 1, True),
    ("Korea Consumer Conf", korea_consumer_confidence, False, False, False, 2, True),
    ("KR Sector Breadth", kr_sector_breadth, False, False, False, 0, False),
]

# Human-readable descriptions for each indicator
INDICATOR_DESCRIPTIONS = {
    "PMI Diffusion": "% of countries with rising PMI",
    "OECD CLI World": "% of OECD CLIs with positive MoM",
    "OECD CLI EM": "EM CLI breadth",
    "ISM New Orders": "US ISM Mfg New Orders",
    "ISM NO-Inv Spread": "ISM New Orders minus Inventories",
    "ISM Services Breadth": "% of ISM Services sub-indices above 50",
    "CESI Breadth": "% of regions with positive Citi Economic Surprise",
    "CESI Momentum": "% of regions with improving CESI",
    "Asian Exports Diff": "% of Asian export series with positive YoY",
    "Global Trade": "Z-scored export composite",
    "SPX Revision Ratio": "S&P 500 EPS revision ratio (up/total)",
    "EPS Breadth": "% of regions with positive EPS momentum",
    "Copper/Gold": "Market-implied growth expectations",
    "Small/Large Cap": "Russell 2000 / S&P 500 (growth confidence)",
    "Cyclical/Defensive": "SPY/XLP (sector-implied growth)",
    "Inflation Surprise": "CPI YoY deviation from trend",
    "10Y Breakeven": "Market inflation expectations",
    "Breakeven Momentum": "Rate of change in breakevens",
    "Commodity Pressure": "Oil/copper/CRB z-score composite",
    "CRB Index": "Broad commodity index level",
    "ISM Prices Paid": "Manufacturing input prices",
    "Fed Net Liquidity": "Fed balance sheet net of TGA+RRP",
    "TGA Drawdown": "Treasury General Account 13-week change (inverted: drawdown = bullish)",
    "Treasury Issuance": "Net Treasury supply pressure (inverted: low issuance = bullish)",
    "Global M2 YoY": "Global M2 money supply YoY growth",
    "FCI US": "US Financial Conditions (contrarian: tight conditions = bullish forward returns)",
    "US 3M10Y": "3M-10Y yield curve spread",
    "US 10Y Real": "10Y TIPS real yield (inverted)",
    "Policy Rate": "Implied policy rate (inverted)",
    "Credit Impulse": "2nd derivative of credit growth",
    "Global Liquidity YoY": "Central bank liquidity YoY growth",
    "Risk Appetite": "Composite risk appetite score",
    "FCI Stress": "Financial stress index (inverted)",
    "VIX": "CBOE VIX (contrarian: high fear = bullish)",
    "Put/Call Z": "Put/call ratio z-score (contrarian: high hedging = bullish)",
    "Risk On/Off": "% of cross-asset signals in risk-on",
    "Credit-Equity Div": "SPX vs HY divergence (inverted)",
    "VIX-RVol Spread": "Fear premium (contrarian: high premium = bullish)",
    "HY Spread": "High-yield credit spread (inverted)",
    "HY/IG Ratio": "HY/IG spread ratio (inverted)",
    "ERP Z-Score": "Equity risk premium z-score",
    "Dollar Index": "DXY dollar index (inverted)",
    "US Sector Breadth": "% of US sectors outperforming SPX",
    "PMI Services Diff": "% of countries with rising services PMI",
    "OECD CLI DM": "Developed market CLI breadth",
    "ISM Mfg Breadth": "% of ISM Mfg sub-indices above 50",
    "ISM Mfg Momentum": "% of ISM Mfg sub-indices improving",
    "Asian Exports Mom": "Asian exports momentum",
    "Baltic Dry": "Baltic Dry Index (shipping demand)",
    "CPI 3M Annualized": "CPI 3-month annualized rate",
    "Rate Cut Expect": "Market-implied rate cut expectations",
    "Rate Expect Mom": "Rate expectations momentum",
    "Term Premium": "Term premium proxy (inverted)",
    "OECD CLI Korea": "Korea OECD CLI",
    "Korea Exports YoY": "Korea exports YoY growth",
    "Korea PMI Mfg": "Korea manufacturing PMI",
    "Korea Semi Exports": "Korea semiconductor exports YoY",
    "Korea Consumer Conf": "Korea consumer confidence",
    "KR Sector Breadth": "% of Korean sectors outperforming KOSPI",
}


# ==============================================================================
# DATA LOADING
# ==============================================================================


def _to_weekly(s: pd.Series) -> pd.Series:
    """Resample to weekly if the series is higher frequency (>40 obs/year)."""
    if s.empty:
        return s
    years = max((s.index[-1] - s.index[0]).days / 365.25, 1)
    if len(s) / years > 40:
        return s.resample("W-SUN").last().dropna()
    return s


def _load_group(loaders, freq="W"):
    """Load indicator group with parallel execution.

    Uses ThreadPoolExecutor because each loader performs DB I/O which
    is thread-safe through SQLAlchemy's connection pooling.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _load_one(name, loader, needs_freq, needs_weekly):
        try:
            raw = loader(freq=freq) if needs_freq else loader()
            return name, _to_weekly(raw) if needs_weekly else raw
        except Exception:
            return name, None

    data = {}
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(_load_one, name, loader, nf, nw): name
            for name, loader, nf, nw, _inv, _lag, _monthly in loaders
        }
        for future in as_completed(futures):
            name, result = future.result()
            if result is not None:
                data[name] = result
    return data


def load_growth_data(freq: str = "W") -> dict:
    """Load all growth axis indicators."""
    return _load_group(GROWTH_LOADERS, freq)


def load_inflation_data(freq: str = "W") -> dict:
    """Load all inflation axis indicators."""
    return _load_group(INFLATION_LOADERS, freq)


def load_liquidity_data(freq: str = "W") -> dict:
    """Load all liquidity cycle indicators."""
    return _load_group(LIQUIDITY_LOADERS, freq)


def load_tactical_data(freq: str = "W") -> dict:
    """Load all tactical (short-term) indicators."""
    return _load_group(TACTICAL_LOADERS, freq)


def load_korea_data(freq: str = "W") -> dict:
    """Load Korea-specific indicators."""
    return _load_group(KOREA_LOADERS, freq)


def load_target_index(ticker: str, freq: str = "W") -> pd.Series:
    """Load a target index price series."""
    return Series(ticker, freq=freq)


# ==============================================================================
# VAMS INDEX / ASSET LOADING
# ==============================================================================


def load_index(index_name: str) -> pd.Series:
    """Load daily price for a VAMS index from DB, with yfinance fallback."""
    from ix.core.macro.config import INDEX_MAP, YF_FALLBACK

    db_code = INDEX_MAP.get(index_name, "ACWI US EQUITY:PX_LAST")
    s = Series(db_code)
    if s.empty:
        yf_ticker = YF_FALLBACK.get(index_name, "ACWI")
        try:
            import yfinance as yf
            df = yf.download(yf_ticker, period="max", auto_adjust=True)
            s = df["Close"].squeeze()
        except Exception:
            return pd.Series(dtype=float)
    s.name = index_name
    return s.dropna()


def load_asset_proxy(code: str, yf_ticker: str) -> pd.Series:
    """Load a single asset class proxy from DB, with yfinance fallback."""
    s = Series(code)
    if s.empty:
        try:
            import yfinance as yf
            df = yf.download(yf_ticker, period="max", auto_adjust=True)
            s = df["Close"].squeeze()
        except Exception:
            return pd.Series(dtype=float)
    return s.dropna()


def resample_weekly(s: pd.Series) -> pd.Series:
    """Resample to weekly (Wednesday) frequency."""
    if s.empty:
        return s
    from ix.common.data.transforms import Resample
    return Resample(s, "W-WED", ffill=True)
