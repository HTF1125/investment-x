from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series, MultiSeries
from ix.core.transforms import StandardScalar


# ── Deficit & Spending ─────────────────────────────────────────────────────


def federal_deficit_gdp(freq: str = "QE") -> pd.Series:
    """Federal Surplus/Deficit as % of GDP.

    Negative = deficit. Large deficits (< -5%) are stimulative
    but raise long-term rate concerns. Surplus (> 0) is rare
    and contractionary.
    """
    s = Series("FYFSGDA188S", freq=freq)
    s.name = "Federal Deficit/GDP"
    return s.dropna()


def federal_receipts_yoy(freq: str = "QE") -> pd.Series:
    """Federal Government Current Receipts YoY (%).

    Tax revenue growth = economy's health check.
    Declining receipts precede recessions as incomes/profits fall.
    """
    receipts = Series("FGRECPT", freq=freq)
    if receipts.empty:
        receipts = Series("W006RC1Q027SBEA", freq=freq)
    s = receipts.pct_change(4) * 100
    s.name = "Federal Receipts YoY"
    return s.dropna()


def federal_spending_yoy(freq: str = "QE") -> pd.Series:
    """Federal Government Total Expenditures YoY (%).

    Direct GDP contributor. Spending surges (COVID, infrastructure)
    boost growth but increase deficit concerns.
    """
    spending = Series("FGEXPND", freq=freq)
    if spending.empty:
        spending = Series("W019RCQ027SBEA", freq=freq)
    s = spending.pct_change(4) * 100
    s.name = "Federal Spending YoY"
    return s.dropna()


def fiscal_impulse(freq: str = "QE") -> pd.Series:
    """Fiscal Impulse — change in deficit/GDP (pp).

    2nd derivative of fiscal policy. Positive = fiscal loosening
    (stimulus increasing). Negative = fiscal tightening.
    This is what matters for growth, not the deficit level.
    """
    deficit_gdp = Series("FYFSGDA188S", freq=freq)
    if deficit_gdp.empty:
        return pd.Series(dtype=float, name="Fiscal Impulse")
    # Change in deficit/GDP: more negative = more stimulus
    # Invert so positive = stimulative
    s = -deficit_gdp.diff(4).dropna()
    s.name = "Fiscal Impulse"
    return s


# ── Public Debt ────────────────────────────────────────────────────────────


def public_debt_gdp(freq: str = "QE") -> pd.Series:
    """Federal Debt Held by Public as % of GDP.

    Structural measure. Above 100% raises sustainability concerns.
    Rate of change matters more than level for markets.
    """
    s = Series("FYGFDPUN", freq=freq)
    if s.empty:
        s = Series("GFDEGDQ188S", freq=freq)
    s.name = "Public Debt/GDP"
    return s.dropna()


def interest_payments_gdp(freq: str = "QE") -> pd.Series:
    """Federal Interest Payments as % of GDP.

    The fiscal constraint that actually binds. When interest costs
    exceed defense spending, it forces policy tradeoffs.
    Rising trajectory = higher term premium risk.
    """
    interest = Series("A091RC1Q027SBEA", freq=freq)
    gdp = Series("GDP", freq=freq)
    if interest.empty or gdp.empty:
        return pd.Series(dtype=float, name="Interest/GDP")
    s = (interest / gdp * 100).dropna()
    s.name = "Interest/GDP (%)"
    return s


# ── Composite ──────────────────────────────────────────────────────────────


def fiscal_monetary_impulse(window: int = 120) -> pd.Series:
    """Combined fiscal + monetary policy impulse.

    Sums fiscal impulse with Fed balance sheet YoY change.
    When both are positive = maximum policy support for risk assets.
    When both negative = double tightening headwind.
    """
    components = {}

    fi = fiscal_impulse()
    if not fi.empty:
        components["Fiscal"] = StandardScalar(fi, window)

    fed_yoy = Series("WALCL")
    if not fed_yoy.empty:
        fed_chg = fed_yoy.pct_change(52).dropna()
        components["Monetary"] = StandardScalar(fed_chg, window)

    if not components:
        return pd.Series(dtype=float, name="Fiscal-Monetary Impulse")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Fiscal-Monetary Impulse"
    return s
