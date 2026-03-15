"""Macro outlook and walk-forward strategy engine.

Three-horizon framework for market outlook:
  1. Long-term (12M+): Global Liquidity Cycle
  2. Medium-term (3-6M): Bayesian Growth x Inflation Regime Probabilities
  3. Short-term (1-3M): Tactical Momentum & Positioning

Walk-forward IC-ranked backtest:
  - taxonomy: ~200 macro indicator registry
  - strategy_utils: index universe, data loaders, z-score helpers
  - wf_backtest: walk-forward backtest engine (empirical IC signs)
  - wf_compute: DB serialization & persistence
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
from ix.core.macro.wf_backtest import run_full_wf_pipeline  # noqa: F401
from ix.core.macro.strategy_utils import INDEX_MAP  # noqa: F401

__all__ = [
    # 3-horizon outlook
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
    # Walk-forward strategy
    "run_full_wf_pipeline",
    "INDEX_MAP",
]
