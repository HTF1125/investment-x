"""Batch strategy system: 150+ lightweight configs as production Strategy objects."""

from .constants import (  # noqa: F401
    ASSET_CODES, MACRO_CODES, SECTORS, MULTI5, MULTI8, BROAD6,
)
from .weight_functions import (  # noqa: F401
    _available, _equal_weight, _compute_rsi,
    wf_static, wf_momentum, wf_momentum_13612w, wf_sector_momentum,
    wf_trend_sma, wf_dual_sma, wf_trend_breadth,
    wf_dual_momentum, wf_defensive_rotation,
    wf_inverse_vol, wf_vol_target,
    wf_macro_level, wf_macro_direction, wf_vix_regime,
    wf_rsi, wf_zscore, wf_seasonal,
    wf_mom_trend, wf_macro_trend, wf_triple, wf_multi_trend_momentum,
    wf_drawdown_control, wf_bond_rotation, wf_relative_value,
    wf_multi_timeframe, wf_composite_macro, wf_vol_scaled_momentum,
    wf_adaptive_momentum, wf_core_satellite, wf_roro,
    wf_cross_asset_rotation, wf_trend_vol_filter, wf_equity_rotation,
    wf_canary,
)
from .registry import _cfg, _build_configs, build_batch_registry  # noqa: F401
from .adapter import BatchStrategy, _extract_universe, _ASSET_KEYS  # noqa: F401
