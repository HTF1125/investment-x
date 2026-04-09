"""Shared chart code execution and rendering utilities.

Thin compatibility shim — all logic now lives in ``ix.common.charting``.
Existing imports from ``ix.api.routers.charts.code_execution`` continue
to work via re-exports below.
"""
from ix.common.viz.charting import (  # noqa: F401
    execute_custom_code,
    render_chart_image,
    get_clean_figure_json,
    simplify_figure,
    decode_plotly_binary_arrays,
    prepare_custom_chart_code,
    build_chart_global_scope,
    apply_chart_theme,
    legacy_get_color as _legacy_get_color,
    legacy_add_zero_line as _legacy_add_zero_line,
    legacy_get_value_label as _legacy_get_value_label,
    df_plot as _df_plot,
)
