from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series, MultiSeries
from ix.common.data.transforms import StandardScalar


# ── Fiscal Policy (from fiscal.py) ──────────────────────────────────────────


def federal_deficit_gdp(freq: str = "QE") -> pd.Series:
    """Federal Surplus/Deficit as % of GDP.

    Negative = deficit. Large deficits (< -5%) are stimulative
    but raise long-term rate concerns. Surplus (> 0) is rare
    and contractionary.
    """
    s = Series("FYFSGDA188S", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
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


# ── Policy Uncertainty (from policy_uncertainty.py) ─────────────────────────


def economic_policy_uncertainty(freq: str = "ME") -> pd.Series:
    """Baker-Bloom-Davis Economic Policy Uncertainty Index.

    Based on newspaper coverage of policy-related economic uncertainty.
    Spikes during elections, fiscal cliffs, trade wars, pandemics.
    High EPU → reduced capex, hiring, and investment.
    """
    s = Series("USEPUINDXD", freq=freq)
    if s.empty:
        s = Series("USEPUINDXM", freq=freq)
    s.name = "Policy Uncertainty"
    return s.dropna()


def policy_uncertainty_zscore(window: int = 252) -> pd.Series:
    """Z-scored EPU for regime detection.

    > 2σ = extreme uncertainty (crisis-level). Contrarian signal:
    peaks in uncertainty often coincide with equity bottoms.
    """
    epu = economic_policy_uncertainty()
    if epu.empty:
        return pd.Series(dtype=float, name="EPU Z-Score")
    s = StandardScalar(epu, window)
    s.name = "EPU Z-Score"
    return s.dropna()


def trade_policy_uncertainty(freq: str = "ME") -> pd.Series:
    """Trade Policy Uncertainty Index.

    Subset of EPU focused on trade/tariff news. Especially relevant
    during trade wars and tariff escalation periods.
    """
    s = Series("TRADEPOLICYUNCERT", freq=freq)
    if s.empty:
        s = Series("TPUINDXM", freq=freq)
    s.name = "Trade Policy Uncertainty"
    return s.dropna()


def global_supply_chain_pressure(freq: str = "ME") -> pd.Series:
    """NY Fed Global Supply Chain Pressure Index (GSCPI).

    Composite of shipping costs, delivery times, backlogs across
    global PMI data. Zero = average. Positive = pressure above normal.

    2021-2022 peak was ~4.3σ. Post-normalization, watch for
    re-acceleration as early inflation/growth signal.
    """
    s = Series("GSCPI", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "Supply Chain Pressure"
    return s.dropna()


def supply_chain_momentum(window: int = 3) -> pd.Series:
    """GSCPI momentum — month-over-month direction.

    Rising GSCPI = supply chain stress building (inflationary).
    Falling = normalization (disinflationary).
    """
    gscpi = Series("GSCPI")
    if gscpi.empty:
        return pd.Series(dtype=float, name="GSCPI Momentum")
    s = gscpi.diff(window).dropna()
    s.name = "GSCPI Momentum"
    return s


def geopolitical_risk_index(freq: str = "ME") -> pd.Series:
    """Caldara-Iacoviello Geopolitical Risk Index.

    Based on newspaper articles about geopolitical tensions.
    Spikes during wars, sanctions, nuclear threats.
    Strong predictor of oil price moves and EM risk premium.
    """
    s = Series("GEOPOLITICALRISK", freq=freq)
    if s.empty:
        s = Series("GPRINDEX", freq=freq)
    s.name = "Geopolitical Risk"
    return s.dropna()


def geopolitical_risk_zscore(window: int = 120) -> pd.Series:
    """Z-scored GPR for regime detection."""
    gpr = geopolitical_risk_index()
    if gpr.empty:
        return pd.Series(dtype=float, name="GPR Z-Score")
    s = StandardScalar(gpr, window)
    s.name = "GPR Z-Score"
    return s.dropna()


def uncertainty_composite(window: int = 120) -> pd.Series:
    """Composite uncertainty index from policy, trade, and supply chain.

    Positive = elevated uncertainty. Negative = calm environment.
    Contrarian signal for equities: extreme uncertainty often
    marks buying opportunities.
    """
    components = {}

    epu = economic_policy_uncertainty()
    if not epu.empty:
        components["EPU"] = StandardScalar(epu, window)

    gscpi = Series("GSCPI")
    if not gscpi.empty:
        components["GSCPI"] = StandardScalar(gscpi.dropna(), window)

    gpr = geopolitical_risk_index()
    if not gpr.empty:
        components["GPR"] = StandardScalar(gpr, window)

    if not components:
        return pd.Series(dtype=float, name="Uncertainty Composite")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Uncertainty Composite"
    return s
