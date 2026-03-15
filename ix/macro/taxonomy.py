"""Backward-compat shim -- canonical location is ix.core.macro.taxonomy."""

from ix.core.macro.taxonomy import *  # noqa: F401,F403
from ix.core.macro.taxonomy import (  # noqa: F401
    build_macro_registry,
    get_eligible_factors,
    GEO_TAGS,
    INDEX_GEO_ELIGIBILITY,
)
