"""Core computation engine. See ix/ARCHITECTURE.md for module placement guide."""

from .technical import *  # noqa: F401,F403
from ix.common.data.statistics import *  # noqa: F401,F403
from ix.common.data.preprocessing import *  # noqa: F401,F403
from ix.common.quantitative import find_similar_patterns
from .backtesting import *  # noqa: F401,F403
from . import regimes
from . import transforms  # noqa: F401
from .stress_test import compute_stress_test  # noqa: F401


# Re-export for backward compat
from ix.common.performance.utils import to_quantiles, sum_to_one, demeaned, performance_by_state  # noqa: F401
from ix.common.performance.metrics import rebase  # noqa: F401

from ix.common import ContributionToGrowth  # noqa: F401

# Attribution
from ix.common.performance.attribution import (  # noqa: F401
    brinson_fachler,
    brinson_fachler_summary,
    multi_period_attribution,
    factor_return_decomposition,
    factor_decomposition_report,
)

__all__ = [
    "regimes",
    "transforms",
    "compute_stress_test",
    "find_similar_patterns",
    # Performance utils
    "to_quantiles",
    "sum_to_one",
    "demeaned",
    "performance_by_state",
    "rebase",
    "ContributionToGrowth",
    # Attribution
    "brinson_fachler",
    "brinson_fachler_summary",
    "multi_period_attribution",
    "factor_return_decomposition",
    "factor_decomposition_report",
]
