"""Parameterized strategy families — 22 classes, 191 configurations."""

from .static import StaticAllocation  # noqa: F401
from .momentum import MomentumStrategy, Momentum13612W, SectorMomentum  # noqa: F401
from .trend import TrendSMA, DualSMA, TrendBreadth  # noqa: F401
from .dual_momentum import DualMomentum, DefensiveRotation  # noqa: F401
from .risk_parity import InverseVol, VolTarget  # noqa: F401
from .macro import MacroLevel, MacroDirection, VixRegime  # noqa: F401
from .mean_reversion import MeanReversionStrategy  # noqa: F401
from .seasonal import SeasonalStrategy  # noqa: F401
from .ensemble import MomentumTrend, MacroTrendEnsemble, TripleSignal, MultiAssetTrendMom  # noqa: F401
from .risk_control import DrawdownControl, BondRotation, RelativeValue  # noqa: F401
from .advanced import MultiTimeframe, CompositeMacro, VolScaledMomentum, AdaptiveMomentum, TrendVolFilter  # noqa: F401
from .rotation import CoreSatellite, RiskOnRiskOff, CrossAssetRotation, EquityRotation, CanaryStrategy  # noqa: F401
from .registry import build_family_specs, build_family_registry  # noqa: F401
