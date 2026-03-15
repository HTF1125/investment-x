"""Backward-compat shim -- canonical location is ix.core.macro.strategy_utils."""

from ix.core.macro.strategy_utils import *  # noqa: F401,F403
from ix.core.macro.strategy_utils import (  # noqa: F401
    INDEX_MAP,
    HORIZON_MAP,
    CATEGORY_HORIZONS,
    PUBLICATION_LAGS,
    CONTRARIAN_INDICATORS,
    load_index,
    load_all_indicators,
    resample_to_freq,
    compute_forward_returns,
    rolling_zscore,
)
