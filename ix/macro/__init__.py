"""Backward-compat shim -- canonical location is ix.core.macro."""

from ix.core.macro.wf_backtest import run_full_wf_pipeline  # noqa: F401
from ix.core.macro.taxonomy import build_macro_registry, GEO_TAGS, INDEX_GEO_ELIGIBILITY  # noqa: F401
from ix.core.macro.strategy_utils import INDEX_MAP, load_index, load_all_indicators  # noqa: F401
