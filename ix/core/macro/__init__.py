"""Macro outlook computation engine.

Three-horizon framework for market outlook:
  1. Long-term (12M+): Global Liquidity Cycle
  2. Medium-term (3-6M): Bayesian Growth x Inflation Regime Probabilities
  3. Short-term (1-3M): Tactical Momentum & Positioning
"""

from ix.core.macro.config import (
    TargetIndex,
    TARGET_INDICES,
    REGIME_NAMES,
    LIQUIDITY_PHASES,
)
from ix.core.macro.pipeline import (
    compute_and_save,
    compute_all_targets,
    compute_full_pipeline,
)
from ix.core.macro.regime import (
    HPFilterRegime,
    GMMRegime,
    InflationRegime,
    regime_forward_returns,
    regime_transition_matrix,
)

__all__ = [
    "TargetIndex",
    "TARGET_INDICES",
    "REGIME_NAMES",
    "LIQUIDITY_PHASES",
    "compute_and_save",
    "compute_all_targets",
    "compute_full_pipeline",
    "HPFilterRegime",
    "GMMRegime",
    "InflationRegime",
    "regime_forward_returns",
    "regime_transition_matrix",
]
