"""Probabilistic regime classification framework.

All public regime models are 1D (single dimension). Multi-axis composites
(e.g. growth × inflation) are generated on demand by /api/regimes/compose
from any combination of registered axis regimes.

Built-in 1D regimes:

* :class:`GrowthRegime`     — Expansion / Contraction
* :class:`InflationRegime`  — Rising / Falling
* :class:`LiquidityRegime`  — Easing / Tightening
* :class:`CreditLevelRegime` / :class:`CreditTrendRegime`
* :class:`DollarTrendRegime`

Usage::

    from ix.core.regimes import LiquidityRegime
    liq = LiquidityRegime().build(z_window=36, sensitivity=1.0, smooth_halflife=3)
"""

from .base import Regime, load_series, zscore, zscore_ism, zscore_roc, sigmoid, LW, RW

# Grouped subpackages — each re-exports its regime classes.
from .fundamentals import (
    GrowthRegime,
    InflationRegime,
    LaborRegime,
    CBSurpriseRegime,
)
from .flow import (
    LiquidityRegime,
    LiquidityImpulseRegime,
    YieldCurveRegime,
    RealRatesRegime,
)
from .markets import (
    CreditLevelRegime,
    CreditTrendRegime,
    DollarTrendRegime,
    CommodityCycleRegime,
)
from .risk import (
    VolatilityTermStructureRegime,
    BreadthRegime,
    EarningsRevisionsRegime,
    PositioningRegime,
    RiskAppetiteRegime,
    DispersionRegime,
)

from .registry import (
    RegimeRegistration,
    register_regime,
    get_regime,
    list_regimes,
    get_phase_pair,
)
from .compute import RegimeComputer, compute_regime
from .analyzer import MultiDimRegimeAnalyzer
from .sensitivity import SensitivityAuditResult, audit_regime_sensitivity
from .balance import StateBalance, compute_state_balance

__all__ = [
    "Regime",
    # fundamentals
    "GrowthRegime",
    "InflationRegime",
    "LaborRegime",
    "CBSurpriseRegime",
    # flow
    "LiquidityRegime",
    "LiquidityImpulseRegime",
    "YieldCurveRegime",
    "RealRatesRegime",
    # markets
    "CreditLevelRegime",
    "CreditTrendRegime",
    "DollarTrendRegime",
    "CommodityCycleRegime",
    # risk
    "VolatilityTermStructureRegime",
    "BreadthRegime",
    "EarningsRevisionsRegime",
    "PositioningRegime",
    "RiskAppetiteRegime",
    "DispersionRegime",
    # base helpers
    "load_series",
    "zscore",
    "zscore_ism",
    "zscore_roc",
    "sigmoid",
    "LW",
    "RW",
    # registry + computation
    "RegimeRegistration",
    "register_regime",
    "get_regime",
    "list_regimes",
    "get_phase_pair",
    "RegimeComputer",
    "compute_regime",
    # multi-dimensional analyzer
    "MultiDimRegimeAnalyzer",
    # parameter sensitivity audit
    "SensitivityAuditResult",
    "audit_regime_sensitivity",
    # state-distribution balance
    "StateBalance",
    "compute_state_balance",
]
