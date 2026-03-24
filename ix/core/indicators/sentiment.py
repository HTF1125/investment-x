from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series
from ix.core.transforms import StandardScalar


# ── Sentiment & Surveys ─────────────────────────────────────────────────────

# Citi Economic Surprise Index codes by region
CESI_CODES = {
    "US": "USFXCESIUSD",
    "Euro Zone": "EUZFXCESIEUR",
    "UK": "GBFXCESIGBP",
    "Japan": "JPFXCESIJPY",
    "China": "CNFXCESICNY",
    "Canada": "CAFXCESICAD",
    "Australia": "AUFXCESIAUD",
    "Switzerland": "CHFXCESICHF",
    "Sweden": "SEFXCESISEK",
    "Norway": "NOFXCESINOK",
    "G10": "WDFXCESIG10",
    "EM": "WDFXCESIEM",
    "Asia Pacific": "WDFXCESIAPAC",
}


# ── Citi Surprise ────────────────────────────────────────────────────────────

def cesi_data() -> pd.DataFrame:
    """All regional CESI series as a DataFrame."""
    data = {name: Series(code) for name, code in CESI_CODES.items()}
    df = pd.DataFrame(data).dropna(how="all")
    if df.empty:
        return pd.DataFrame()
    return df


def cesi_breadth(smooth: int = 20) -> pd.Series:
    """% of regions with positive Citi Surprise reading (smoothed).

    Raw daily breadth flickers as individual regions hover near zero.
    A 20-day moving average produces a clean, tradeable signal.
    """
    data = {name: Series(code) for name, code in CESI_CODES.items()}
    df = pd.DataFrame(data).dropna(how="all")
    if df.empty:
        return pd.Series(dtype=float, name="CESI Breadth")
    positive = (df > 0).sum(axis=1)
    valid = df.notna().sum(axis=1)
    result = (positive / valid * 100).rolling(smooth, min_periods=1).mean().dropna()
    result.name = "CESI Breadth"
    return result


def cesi_momentum(smooth: int = 20) -> pd.Series:
    """% of regions with improving (MoM) Citi Surprise readings (smoothed).

    Uses 5-day diff instead of 1-day to reduce noise, then 20-day MA.
    """
    data = {name: Series(code) for name, code in CESI_CODES.items()}
    df = pd.DataFrame(data).dropna(how="all")
    if df.empty:
        return pd.Series(dtype=float, name="CESI Momentum Breadth")
    changes = df.diff(5)
    positive = (changes > 0).sum(axis=1)
    valid = changes.notna().sum(axis=1)
    result = (positive / valid * 100).rolling(smooth, min_periods=1).mean().dropna()
    result.name = "CESI Momentum Breadth"
    return result


# ── CFTC Positioning ─────────────────────────────────────────────────────────

CFTC_ASSETS = {
    "S&P500": ("CFTNCLALLSP500EMINCMEF_US", "CFTNCSALLSP500EMINCMEF_US"),
    "USD": ("CFTNCLALLJUSDNYBTF_US", "CFTNCSALLJUSDNYBTF_US"),
    "Gold": ("CFTNCLALLGOLDCOMF_US", "CFTNCSALLGOLDCOMF_US"),
    "JPY": ("CFTNCLALLYENCMEF_US", "CFTNCSALLYENCMEF_US"),
    "UST 10Y": ("CFTNCLALLTN10YCBOTF_US", "CFTNCSALLTN10YCBOTF_US"),
}


def cftc_net() -> pd.DataFrame:
    """Net positioning (long - short) for each asset."""
    data = {}
    for name, (long_code, short_code) in CFTC_ASSETS.items():
        long_s = Series(long_code)
        short_s = Series(short_code)
        if not long_s.empty and not short_s.empty:
            data[name] = long_s - short_s
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data).dropna(how="all")


def cftc_zscore(window: int = 52) -> pd.DataFrame:
    """Rolling z-score of net positioning."""
    net = cftc_net()
    roll = net.rolling(window)
    return net.sub(roll.mean()).div(roll.std()).dropna(how="all")


def cftc_extreme_count(window: int = 52, threshold: float = 1.5) -> pd.Series:
    """Number of assets with extreme (|z| > threshold) positioning."""
    z = cftc_zscore(window)
    result = (z.abs() > threshold).sum(axis=1)
    result.name = "CFTC Extreme Count"
    return result.dropna()


# ── Put/Call Ratio ───────────────────────────────────────────────────────────

def put_call_raw() -> pd.Series:
    """Total CBOE Put/Call ratio."""
    s = Series("PCRTEQTY INDEX")
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "Put/Call Ratio"
    return s.dropna()


def put_call_smoothed(window: int = 10) -> pd.Series:
    """Moving average of Put/Call ratio."""
    s = Series("PCRTEQTY INDEX").rolling(window).mean()
    if s.empty:
        return pd.Series(dtype=float)
    s.name = f"Put/Call {window}d MA"
    return s.dropna()


def put_call_zscore(window: int = 252) -> pd.Series:
    """Rolling z-score of Put/Call ratio (high = fear)."""
    s = Series("PCRTEQTY INDEX")
    if s.empty:
        return pd.Series(dtype=float, name="Put/Call Z-Score")
    return StandardScalar(s, window)


# ── Investor Positions ───────────────────────────────────────────────────────

POSITION_ASSETS = {
    "S&P500": ("CFTNCLOI%ALLS5C3512CMEOF_US", "CFTNCSOI%ALLS5C3512CMEOF_US"),
    "USD": ("CFTNCLOI%ALLJUSDNYBTOF_US", "CFTNCSOI%ALLJUSDNYBTOF_US"),
    "Gold": ("CFTNCLOI%ALLGOLDCOMOF_US", "CFTNCSOI%ALLGOLDCOMOF_US"),
    "JPY": ("CFTNCLOI%ALLYENCMEOF_US", "CFTNCSOI%ALLYENCMEOF_US"),
    "UST-10Y": ("CFTNCLOI%ALLTN10YCBOTOF_US", "CFTNCSOI%ALLTN10YCBOTOF_US"),
    "UST-Ultra": ("CFTNCLOI%ALLLUT3163CBOTOF_US", "CFTNCSOI%ALLLUT3163CBOTOF_US"),
    "Commodities": ("CFTNCLOI%ALLDJUBSERCBOTOF_US", "CFTNCSOI%ALLDJUBSERCBOTOF_US"),
}


def investor_positions_net() -> pd.DataFrame:
    """Net positioning (long - short) for each asset."""
    data = {}
    for name, (long_code, short_code) in POSITION_ASSETS.items():
        long_s = Series(long_code)
        short_s = Series(short_code)
        if not long_s.empty and not short_s.empty:
            data[name] = long_s - short_s
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)


def investor_positions_vs_trend(weeks: int = 52) -> pd.DataFrame:
    """Net positioning vs rolling mean trend."""
    data = investor_positions_net()
    return data - data.rolling(weeks).mean()


def usd_open_interest() -> pd.Series:
    """USD open interest (long - short)."""
    long_s = Series("CFTNCLOI%ALLJUSDNYBTOF_US")
    short_s = Series("CFTNCSOI%ALLJUSDNYBTOF_US")
    if long_s.empty or short_s.empty:
        return pd.Series(dtype=float)
    return long_s - short_s


# Backward-compatible aliases
def USD_Open_Interest() -> pd.Series:
    return usd_open_interest()


def InvestorPositionsvsTrend(weeks: int = 52) -> pd.DataFrame:
    return investor_positions_vs_trend(weeks=weeks)


# ── Fund Flows & Leverage ───────────────────────────────────────────────────

# ── Margin Debt / Leverage Cycle ────────────────────────────────────────────


def margin_debt() -> pd.Series:
    """FINRA margin debt (debit balances in margin accounts, USD billions).

    Rising margin debt = increasing leverage / risk appetite.
    YoY declines >20% historically coincide with bear markets.
    """
    s = Series("BOGZ1FL663067003Q")  # Broker-dealer margin lending proxy
    if s.empty:
        # Fallback: use total bank credit as leverage proxy
        s = Series("TOTBKCR")
    s.name = "Margin Debt"
    return s.dropna()


def margin_debt_yoy() -> pd.Series:
    """Margin debt year-over-year growth (%).

    Leads equity market by 1-3 months at extremes.
    > +30% = frothy. < -20% = deleveraging.
    """
    md = margin_debt()
    yoy = md.pct_change(4 if md.index.freq and "Q" in str(md.index.freq) else 12) * 100
    yoy.name = "Margin Debt YoY"
    return yoy.dropna()


def margin_debt_vs_spx(window: int = 52) -> pd.Series:
    """Margin debt momentum vs SPX momentum divergence.

    When leverage grows faster than prices, a correction is brewing.
    When leverage falls faster than prices, bottom may be near.
    """
    md = margin_debt().resample("W").last().ffill()
    spx = Series("SPX INDEX:PX_LAST", freq="W")
    if spx.empty:
        return pd.Series(dtype=float)
    md_mom = md.pct_change(26) * 100
    spx_mom = spx.pct_change(26) * 100
    div = (StandardScalar(md_mom.dropna(), window)
           - StandardScalar(spx_mom.dropna(), window))
    s = div.dropna()
    s.name = "Margin Debt vs SPX Divergence"
    return s


# ── Risk Rotation Proxy ─────────────────────────────────────────────────────


def risk_rotation_index(window: int = 60) -> pd.Series:
    """Risk asset rotation index from relative volume and price action.

    Combines SPY vs TLT momentum, HY vs IG spread changes,
    and small-cap vs large-cap performance to measure risk appetite rotation.
    """
    # Equity vs bond momentum
    spy = Series("SPY US EQUITY:PX_LAST")
    tlt = Series("TLT US EQUITY:PX_LAST")
    eq_bond = StandardScalar((spy / tlt).dropna().pct_change(window).dropna(), window * 2)

    # HY vs IG spread differential
    hy = Series("BAMLH0A0HYM2")
    ig = Series("BAMLC0A4CBBB")
    credit = -StandardScalar((hy - ig).dropna().diff(window).dropna(), window * 2)

    # Small vs large cap
    rty = Series("RTY INDEX:PX_LAST")
    spx = Series("SPX INDEX:PX_LAST")
    if spy.empty or tlt.empty or hy.empty:
        return pd.Series(dtype=float)
    size = StandardScalar((rty / spx).dropna().pct_change(window).dropna(), window * 2)

    s = pd.concat([eq_bond, credit, size], axis=1).mean(axis=1).dropna()
    s.name = "Risk Rotation Index"
    return s


# ── ETF Flow Proxies ────────────────────────────────────────────────────────


def equity_bond_flow_ratio(window: int = 20) -> pd.Series:
    """Equity vs bond ETF relative momentum as flow proxy.

    Uses SPY/TLT relative performance as a proxy for equity-bond rotation.
    Rising = flows favoring equities over bonds.
    """
    spy = Series("SPY US EQUITY:PX_LAST")
    tlt = Series("TLT US EQUITY:PX_LAST")
    if spy.empty or tlt.empty:
        return pd.Series(dtype=float)
    ratio = (spy / tlt).dropna()
    s = ratio.pct_change(window).rolling(5).mean().dropna() * 100
    s.name = "Equity/Bond Flow Proxy"
    return s


def em_flow_proxy(window: int = 20) -> pd.Series:
    """EM fund flow proxy from EEM/SPY relative performance.

    Rising = EM outperforming (inflows). Falling = EM underperforming (outflows).
    """
    eem = Series("891800:FG_TOTAL_RET_IDX")
    spy = Series("SPX INDEX:PX_LAST")
    if eem.empty or spy.empty:
        return pd.Series(dtype=float)
    ratio = (eem / spy).dropna()
    s = ratio.pct_change(window).rolling(5).mean().dropna() * 100
    s.name = "EM Flow Proxy"
    return s


def commodity_flow_proxy(window: int = 20) -> pd.Series:
    """Commodity fund flow proxy from DBC/SPY relative performance."""
    dbc = Series("BCOM-CME:PX_LAST")
    spy = Series("SPX INDEX:PX_LAST")
    if dbc.empty or spy.empty:
        return pd.Series(dtype=float)
    ratio = (dbc / spy).dropna()
    s = ratio.pct_change(window).rolling(5).mean().dropna() * 100
    s.name = "Commodity Flow Proxy"
    return s


# ── Leverage Cycle ──────────────────────────────────────────────────────────


def bank_credit_impulse(freq: str = "ME") -> pd.Series:
    """Bank credit impulse: acceleration of total bank credit growth.

    Second derivative of credit — leads economic activity by 6-9 months.
    Positive = credit expanding at an increasing rate (stimulative).
    Negative = credit decelerating (contractionary).
    """
    credit = Series("TOTBKCR", freq=freq)
    if credit.empty:
        return pd.Series(dtype=float)
    yoy = credit.pct_change(12) * 100
    impulse = yoy.diff(3)
    impulse.name = "Bank Credit Impulse"
    return impulse.dropna()


def consumer_credit_growth(freq: str = "ME") -> pd.Series:
    """Consumer credit outstanding YoY growth (%).

    Captures household leverage trends. Decelerating consumer credit
    leads consumer spending weakness by 2-4 quarters.
    """
    cc = Series("TOTALSL", freq=freq)
    if cc.empty:
        return pd.Series(dtype=float)
    s = cc.pct_change(12) * 100
    s.name = "Consumer Credit YoY"
    return s.dropna()


# ── CFTC Net Speculative Positioning ──────────────────────────────────────

CFTC_SPEC_CODES = {
    "sp500": ("CFTNCLALLSP500EMINCMEF@US", "CFTNCSALLSP500EMINCMEF@US"),
    "gold": ("CFTNCLALLGOLDCOMF@US", "CFTNCSALLGOLDCOMF@US"),
    "10y": ("CFTNCLALLTN10YCBOTF@US", "CFTNCSALLTN10YCBOTF@US"),
    "euro": ("CFTNCLALLEUROCMEF@US", "CFTNCSALLEUROCMEF@US"),
    "yen": ("CFTNCLALLYENCMEF@US", "CFTNCSALLYENCMEF@US"),
    "copper": ("CFTNCLALLCOPP1COMF@US", "CFTNCSALLCOPP1COMF@US"),
    "natgas": ("CFTNCLALLNGASNYMF@US", "CFTNCSALLNGASNYMF@US"),
    "silver": ("CFTNCLALLSILCOMF@US", "CFTNCSALLSILCOMF@US"),
}

CFTC_SPEC_LABELS = {
    "sp500": "S&P 500",
    "gold": "Gold",
    "10y": "10Y Treasury",
    "euro": "Euro FX",
    "yen": "Yen",
    "copper": "Copper",
    "natgas": "Natural Gas",
    "silver": "Silver",
}


def cftc_net_speculative(contract: str) -> pd.Series:
    """Net non-commercial positioning (long - short) for a CFTC contract.

    Args:
        contract: One of 'sp500', 'gold', '10y', 'euro', 'yen',
                  'copper', 'natgas', 'silver'.

    Source: CFTC Commitments of Traders — non-commercial (speculative) positions.
    """
    key = contract.lower()
    if key not in CFTC_SPEC_CODES:
        raise ValueError(f"Unknown contract '{contract}'. Choose from: {list(CFTC_SPEC_CODES)}")
    long_code, short_code = CFTC_SPEC_CODES[key]
    net = Series(long_code) - Series(short_code)
    if net.empty:
        return pd.Series(dtype=float, name=f"CFTC Net {CFTC_SPEC_LABELS[key]}")
    net.name = f"CFTC Net {CFTC_SPEC_LABELS[key]}"
    return net.dropna()


def cftc_net_speculative_zscore(contract: str, window: int = 78) -> pd.Series:
    """Z-scored net speculative positioning for a CFTC contract.

    Args:
        contract: One of 'sp500', 'gold', '10y', 'euro', 'yen',
                  'copper', 'natgas', 'silver'.
        window: Rolling z-score window (default 78 weeks / ~1.5 years).

    Source: CFTC Commitments of Traders — non-commercial positions, z-scored.
    """
    net = cftc_net_speculative(contract)
    if net.empty:
        label = CFTC_SPEC_LABELS.get(contract.lower(), contract)
        return pd.Series(dtype=float, name=f"CFTC Net {label} Z")
    s = StandardScalar(net, window)
    label = CFTC_SPEC_LABELS[contract.lower()]
    s.name = f"CFTC Net {label} Z"
    return s.dropna()


def cftc_speculative_sentiment() -> pd.DataFrame:
    """Z-scored net speculative positioning for all 8 CFTC contracts.

    Returns a DataFrame with one column per contract (S&P 500, Gold,
    10Y Treasury, Euro FX, Yen, Copper, Natural Gas, Silver).
    Uses a 78-week rolling z-score window.

    Source: CFTC Commitments of Traders — non-commercial positions.
    """
    data = {}
    for key, label in CFTC_SPEC_LABELS.items():
        z = cftc_net_speculative_zscore(key)
        if not z.empty:
            data[label] = z
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data).dropna(how="all")
