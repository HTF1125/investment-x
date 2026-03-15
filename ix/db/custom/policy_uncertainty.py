from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series, MultiSeries
from ix.core.transforms import StandardScalar


# ── Economic Policy Uncertainty ────────────────────────────────────────────


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


# ── Supply Chain ───────────────────────────────────────────────────────────


def global_supply_chain_pressure(freq: str = "ME") -> pd.Series:
    """NY Fed Global Supply Chain Pressure Index (GSCPI).

    Composite of shipping costs, delivery times, backlogs across
    global PMI data. Zero = average. Positive = pressure above normal.

    2021-2022 peak was ~4.3σ. Post-normalization, watch for
    re-acceleration as early inflation/growth signal.
    """
    s = Series("GSCPI", freq=freq)
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


# ── Geopolitical Risk ──────────────────────────────────────────────────────


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


# ── Composite ──────────────────────────────────────────────────────────────


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
