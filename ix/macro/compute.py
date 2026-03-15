"""Backward-compat shim -- canonical location is ix.core.macro.wf_compute."""

from ix.core.macro.wf_compute import *  # noqa: F401,F403
from ix.core.macro.wf_compute import (  # noqa: F401
    OPTIMIZED_PARAMS,
    compute_and_save,
    compute_all,
    serialize_backtest,
    serialize_factors,
    serialize_current_signal,
)
