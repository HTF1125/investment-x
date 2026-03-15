"""Backward-compat shim -- canonical location is ix.core.macro.wf_backtest."""

from ix.core.macro.wf_backtest import *  # noqa: F401,F403
from ix.core.macro.wf_backtest import (  # noqa: F401
    run_full_wf_pipeline,
    REGIME_ALLOC,
    INDEX_MAP,
)
