from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series
from ix.core.transforms import StandardScalar


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
    ratio = (eem / spy).dropna()
    s = ratio.pct_change(window).rolling(5).mean().dropna() * 100
    s.name = "EM Flow Proxy"
    return s


def commodity_flow_proxy(window: int = 20) -> pd.Series:
    """Commodity fund flow proxy from DBC/SPY relative performance."""
    dbc = Series("BCOM-CME:PX_LAST")
    spy = Series("SPX INDEX:PX_LAST")
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
    s = cc.pct_change(12) * 100
    s.name = "Consumer Credit YoY"
    return s.dropna()
