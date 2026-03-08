from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go


@dataclass(frozen=True)
class Color:
    """Centralized color management for the Investment-X design system."""

    # Core palette
    CYAN: str = "#00D2FF"
    MAGENTA: str = "#FF69B4"
    PURPLE: str = "#A020F0"
    EMERALD: str = "#00FF66"
    AMBER: str = "#FFB84D"
    ROSE: str = "#ef4444"
    SKY: str = "#3b82f6"
    SLATE: str = "#94a3b8"

    # Theme primitives
    BG_DARK: str = "#0B0E14"
    BG_LIGHT: str = "#FFFFFF"

    # Domain mapping (stable signature colors by name)
    ASSET_MAP: Dict[str, str] = field(
        default_factory=lambda: {
            "s&p 500": "#00D2FF",
            "spx": "#00D2FF",
            "s&p500": "#00D2FF",
            "equity": "#00D2FF",
            "gold": "#FF69B4",
            "xau": "#FF69B4",
            "commodities": "#A020F0",
            "crb": "#A020F0",
            "usd": "#00FF66",
            "dxy": "#00FF66",
            "ust 10y": "#FFB84D",
            "rates": "#FFB84D",
            "btc": "#f59e0b",
            "crypto": "#f59e0b",
            "volatility": "#ef4444",
            "vix": "#ef4444",
        }
    )

    @property
    def colorway(self) -> List[str]:
        return [
            self.CYAN,
            self.MAGENTA,
            self.PURPLE,
            self.EMERALD,
            self.AMBER,
            self.ROSE,
            self.SKY,
        ]

    def get_asset(self, name: str) -> Optional[str]:
        if not name:
            return None
        return self.ASSET_MAP.get(name.lower().strip())


# Trace types that manage their own internal color schemes.
# Explicitly excluded from palette assignment.
_SKIP_COLOR_TYPES = frozenset(
    {
        "candlestick",
        "ohlc",
        "heatmap",
        "heatmapgl",
        "choropleth",
        "choroplethmapbox",
        "densitymapbox",
        "parcats",
        "parcoords",
        "sunburst",
        "treemap",
        "icicle",
        "funnelarea",
        "pie",
    }
)


@dataclass(frozen=True)
class ChartTheme:
    """
    Canonical chart theme used by dashboard/studio delivery.

    Covers:
    - Responsive sizing (autosize, no fixed width/height)
    - Dark / light mode tokens for all layout properties
    - Automatic legend visibility decision
    - Index-based palette assignment with asset-name overrides
    - Axis sanitization: invalid ranges, log-scale safety, scaleanchor removal
    - Date axis right-side breathing room
    """

    palette: Color = field(default_factory=Color)
    margin: Dict[str, int] = field(default_factory=lambda: dict(t=50, l=0, r=0, b=0))
    font_main: str = "Arial, Helvetica, sans-serif"
    font_mono: str = "Inter, SF Mono, monospace"
    padding_ratio: float = 0.10
    datetime_tickformat: str = "%Y-%m-%d"
    title_x: float = 0.01
    title_y: float = 0.98
    legend_x: float = 0.01
    legend_y: float = 0.98
    legend_gap: int = 0

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _is_datetime_values(values: Any) -> bool:
        if values is None:
            return False
        try:
            s = pd.Series(list(values)).dropna()
            if s.empty:
                return False
            if pd.api.types.is_datetime64_any_dtype(s):
                return True
            if isinstance(s.iloc[0], (datetime, pd.Timestamp)):
                return True
            # Reject purely numeric data — pd.to_datetime interprets numbers
            # as nanosecond offsets from epoch, giving false positives for
            # scatter/quadrant charts with numeric axes (e.g. -200 to 200).
            if pd.api.types.is_numeric_dtype(s):
                return False
            parsed = pd.to_datetime(s, errors="coerce")
            return parsed.notna().mean() >= 0.8
        except Exception:
            return False

    @staticmethod
    def _datetime_bounds(
        values: Any,
    ) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
        try:
            s = pd.Series(list(values)).dropna()
            if s.empty:
                return None, None
            parsed = pd.to_datetime(s, errors="coerce")
            if parsed.notna().mean() < 0.8:
                return None, None
            parsed = parsed.dropna()
            if parsed.empty:
                return None, None
            return parsed.min(), parsed.max()
        except Exception:
            return None, None

    @staticmethod
    def _axis_names(fig: go.Figure, prefix: str) -> list[str]:
        base = [prefix]
        try:
            layout_dict = fig.layout.to_plotly_json()
            for k in layout_dict.keys():
                if k.startswith(prefix) and k != prefix:
                    suffix = k[len(prefix) :]
                    if suffix.isdigit():
                        base.append(k)
        except Exception:
            pass

        def _key(name: str) -> int:
            suffix = name[len(prefix) :]
            return int(suffix) if suffix.isdigit() else 1

        return sorted(list(set(base)), key=_key)

    @staticmethod
    def _axis_ref_from_name(axis_name: str, axis_prefix: str) -> str:
        if axis_name == axis_prefix:
            return axis_prefix[0]
        suffix = axis_name[len(axis_prefix) :]
        return f"{axis_prefix[0]}{suffix}"

    def _x_values_for_axis(self, fig: go.Figure, axis_name: str) -> list[Any]:
        axis_ref = self._axis_ref_from_name(axis_name, "xaxis")
        values: list[Any] = []
        for trace in fig.data:
            trace_axis = getattr(trace, "xaxis", None) or "x"
            if trace_axis != axis_ref:
                continue
            xs = getattr(trace, "x", None)
            if xs is None:
                continue
            try:
                values.extend([x for x in xs if x is not None])
            except Exception:
                if xs is not None:
                    values.append(xs)
        return values

    @staticmethod
    def _trace_has_explicit_color(trace: go.BaseTraceType) -> bool:
        line = getattr(trace, "line", None)
        if line is not None and getattr(line, "color", None):
            return True
        marker = getattr(trace, "marker", None)
        if marker is not None and isinstance(getattr(marker, "color", None), str):
            return True
        return False

    @staticmethod
    def _marker_is_array_colored(trace: go.BaseTraceType) -> bool:
        """True when marker.color is an array or uses a colorscale — don't override."""
        marker = getattr(trace, "marker", None)
        if marker is None:
            return False
        color = getattr(marker, "color", None)
        if isinstance(color, (list, tuple)):
            return True
        colorscale = getattr(marker, "colorscale", None)
        if colorscale is not None:
            return True
        return False

    def _should_show_legend(self, fig: go.Figure) -> bool:
        if not fig.data:
            return False

        legend_trace_types = {"pie", "funnelarea", "sunburst", "treemap", "icicle"}
        for trace in fig.data:
            if getattr(trace, "visible", None) is False:
                continue
            if getattr(trace, "showlegend", None) is False:
                continue
            if getattr(trace, "type", None) in legend_trace_types:
                return True

        count = 0
        names: set[str] = set()
        for trace in fig.data:
            if getattr(trace, "visible", None) is False:
                continue
            if getattr(trace, "showlegend", None) is False:
                continue
            count += 1
            nm = str(getattr(trace, "name", "") or "").strip()
            if nm:
                names.add(nm)

        if count <= 1:
            return False
        if len(names) <= 1 and count <= 2:
            return False
        return True

    # ------------------------------------------------------------------ #
    # Axis sanitization                                                    #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _axis_has_positive_data(data: list[Any], axis_key: str) -> bool:
        """
        Return True if any trace targeting the given y-axis has at least one
        positive finite value. Used to decide whether log scale is safe.
        """
        prefix = "yaxis"
        suffix = axis_key[len(prefix) :]
        axis_ref = f"y{suffix}" if suffix else "y"

        for trace in data:
            trace_axis = getattr(trace, "yaxis", None) or "y"
            if trace_axis != axis_ref:
                continue
            for attr in ("y", "open", "high", "low", "close"):
                vals = getattr(trace, attr, None)
                if vals is None:
                    continue
                try:
                    for v in vals:
                        if v is not None:
                            fv = float(v)
                            if math.isfinite(fv) and fv > 0:
                                return True
                except Exception:
                    pass
        return False

    def _sanitize_axes(self, fig: go.Figure) -> None:
        """
        Remove axis properties that cause Plotly crashes or render incorrectly:
        - scaleanchor / scaleratio (can prevent responsive layout)
        - Invalid ranges (NaN, identical endpoints, unparseable dates)
        - Log scale when the axis has no positive data (falls back to linear)
        """
        try:
            layout_json = fig.layout.to_plotly_json()
        except Exception:
            return

        data = list(fig.data)

        # Collect all axis keys; always include primaries even if absent from layout.
        axis_keys: list[str] = []
        for k in layout_json:
            if k.startswith("xaxis") or k.startswith("yaxis"):
                axis_keys.append(k)
        for primary in ("xaxis", "yaxis"):
            if primary not in axis_keys:
                axis_keys.append(primary)

        for key in axis_keys:
            axis_obj = getattr(fig.layout, key, None)
            if axis_obj is None:
                continue

            updates: Dict[str, Any] = {}

            # Remove scale anchors that can cause relayout crashes,
            # but preserve them for non-datetime axes (e.g. quadrant charts
            # that need square aspect ratio via scaleanchor).
            is_datetime_axis = False
            if key.startswith("xaxis"):
                x_vals = self._x_values_for_axis(fig, key)
                is_datetime_axis = bool(x_vals) and self._is_datetime_values(x_vals)
            else:
                is_datetime_axis = getattr(axis_obj, "type", None) == "date"

            if is_datetime_axis:
                if getattr(axis_obj, "scaleanchor", None) is not None:
                    updates["scaleanchor"] = None
                if getattr(axis_obj, "scaleratio", None) is not None:
                    updates["scaleratio"] = None

            axis_type = getattr(axis_obj, "type", None)
            axis_range = getattr(axis_obj, "range", None)

            # Validate explicit range; fall back to autorange if invalid.
            if axis_range is not None and len(axis_range) >= 2:
                start, end = axis_range[0], axis_range[1]
                valid = True

                if axis_type == "date":
                    try:
                        ts0 = pd.Timestamp(str(start))
                        ts1 = pd.Timestamp(str(end))
                        valid = pd.notna(ts0) and pd.notna(ts1) and ts0 != ts1
                    except Exception:
                        valid = False
                elif axis_type in ("category", "multicategory"):
                    valid = True  # label-based ranges are always valid
                else:
                    # Try numeric first, then fall back to date parsing for
                    # auto-typed axes that were given ISO-string date ranges
                    # (e.g. by a previous theme application).
                    try:
                        mn, mx = float(start), float(end)
                        valid = math.isfinite(mn) and math.isfinite(mx) and mn != mx
                    except Exception:
                        try:
                            ts0 = pd.Timestamp(str(start))
                            ts1 = pd.Timestamp(str(end))
                            valid = pd.notna(ts0) and pd.notna(ts1) and ts0 != ts1
                        except Exception:
                            valid = False

                if not valid:
                    updates["range"] = None
                    updates["autorange"] = True

            # Log-scale safety: if no positive data exists, fall back to linear.
            if axis_type == "log" and key.startswith("yaxis"):
                if not self._axis_has_positive_data(data, key):
                    updates["type"] = "linear"
                    updates["range"] = None
                    updates["autorange"] = True

            if updates:
                fig.update_layout({key: updates})

    # ------------------------------------------------------------------ #
    # Trace coloring                                                       #
    # ------------------------------------------------------------------ #

    def _color_traces(self, fig: go.Figure) -> None:
        """
        Assign palette colors to all uncolored traces.

        Priority:
          1. Trace already has an explicit color → skip (preserve author intent).
          2. Trace name matches ASSET_MAP → use its signature color.
          3. Fallback → assign next palette color by index.

        Skips trace types that manage their own color scheme (candlestick,
        heatmap, pie, etc.) and traces with array/colorscale marker coloring.
        """
        palette = self.palette.colorway
        palette_idx = 0

        for trace in fig.data:
            trace_type = getattr(trace, "type", "") or ""

            if trace_type in _SKIP_COLOR_TYPES:
                palette_idx += 1
                continue

            if self._trace_has_explicit_color(trace):
                palette_idx += 1
                continue

            if self._marker_is_array_colored(trace):
                palette_idx += 1
                continue

            # Resolve color: named asset first, then palette index.
            name = str(getattr(trace, "name", "") or "").strip()
            color = self.palette.get_asset(name) or palette[palette_idx % len(palette)]
            palette_idx += 1

            line = getattr(trace, "line", None)
            marker = getattr(trace, "marker", None)

            if trace_type in (
                "scatter",
                "scattergl",
                "scatter3d",
                "scatterpolar",
                "scattermapbox",
            ):
                mode = str(getattr(trace, "mode", "") or "lines")
                if line is not None:
                    try:
                        line.color = color
                    except Exception:
                        pass
                if marker is not None and not self._marker_is_array_colored(trace):
                    try:
                        marker.color = color
                    except Exception:
                        pass

            elif trace_type in ("bar", "histogram", "waterfall", "funnel"):
                if marker is not None and not self._marker_is_array_colored(trace):
                    try:
                        marker.color = color
                    except Exception:
                        pass

            elif trace_type in ("box", "violin"):
                if marker is not None:
                    try:
                        marker.color = color
                    except Exception:
                        pass
                if line is not None:
                    try:
                        line.color = color
                    except Exception:
                        pass

            elif trace_type == "area":
                if line is not None:
                    try:
                        line.color = color
                    except Exception:
                        pass

    # ------------------------------------------------------------------ #
    # Date axis padding                                                    #
    # ------------------------------------------------------------------ #

    def _apply_datetime_padding(self, fig: go.Figure) -> None:
        """Add symmetric breathing room on date x-axes.

        Only pads axes that are *confirmed* date axes — either explicitly
        set to ``type="date"`` by the chart code or containing trace data
        that is unambiguously datetime.  The axis type is never forced to
        ``"date"`` so that charts with non-date x-axes (scatter/quadrant,
        category labels that happen to parse as dates, etc.) are left alone.
        """
        for axis_name in self._axis_names(fig, "xaxis"):
            axis_obj = getattr(fig.layout, axis_name, None)
            axis_type = getattr(axis_obj, "type", None) if axis_obj else None

            # Skip axes whose type is explicitly non-date.
            if axis_type in ("category", "linear", "log"):
                continue

            # Skip axes that already have a finite numeric range (quadrant
            # / scatter charts typically set numeric ranges).
            axis_range = getattr(axis_obj, "range", None)
            if axis_range is not None and len(axis_range) >= 2:
                try:
                    r0, r1 = float(axis_range[0]), float(axis_range[1])
                    if math.isfinite(r0) and math.isfinite(r1):
                        continue
                except (TypeError, ValueError):
                    pass

            # For auto-detected axes (type is None / "-"), only proceed if
            # the trace x-values are clearly datetime.
            x_values = self._x_values_for_axis(fig, axis_name)
            if not x_values or not self._is_datetime_values(x_values):
                continue

            x0, x1 = self._datetime_bounds(x_values)
            if x0 is None or x1 is None or x0 == x1:
                continue

            pad = (x1 - x0) * self.padding_ratio
            if pad <= pd.Timedelta(0):
                continue

            # Never force `type: "date"` — let Plotly auto-detect axis type
            # from the data.  We only set the padded range and tickformat.
            update: Dict[str, Any] = {
                "range": [
                    x0.isoformat(),
                    (x1 + pad).isoformat(),
                ],
                "autorange": False,
                "tickformat": self.datetime_tickformat,
            }
            # Only explicitly mark the type when the chart code already
            # declared it as "date" — otherwise leave it for Plotly to infer.
            if axis_type == "date":
                update["type"] = "date"

            fig.update_layout({axis_name: update})

    # ------------------------------------------------------------------ #
    # Year-end boundary lines                                              #
    # ------------------------------------------------------------------ #

    def _add_year_boundary_lines(
        self, fig: go.Figure, is_dark: bool
    ) -> None:
        """Add subtle vertical lines at Jan 1 boundaries for datetime x-axes."""
        grid_color = (
            "rgba(148,163,184,0.12)" if is_dark else "rgba(15,23,42,0.08)"
        )
        new_shapes: list[dict] = []

        for axis_name in self._axis_names(fig, "xaxis"):
            axis_obj = getattr(fig.layout, axis_name, None)
            axis_type = getattr(axis_obj, "type", None) if axis_obj else None
            if axis_type in ("category", "linear", "log"):
                continue

            axis_range = getattr(axis_obj, "range", None)
            if axis_range is not None and len(axis_range) >= 2:
                try:
                    r0, r1 = float(axis_range[0]), float(axis_range[1])
                    if math.isfinite(r0) and math.isfinite(r1):
                        continue
                except (TypeError, ValueError):
                    pass

            x_values = self._x_values_for_axis(fig, axis_name)
            if not x_values or not self._is_datetime_values(x_values):
                continue

            x0, x1 = self._datetime_bounds(x_values)
            if x0 is None or x1 is None or x0 == x1:
                continue

            axis_ref = self._axis_ref_from_name(axis_name, "xaxis")

            start_year = x0.year + 1
            end_year = x1.year + 1
            for year in range(start_year, end_year + 1):
                jan1 = pd.Timestamp(f"{year}-01-01")
                if x0 < jan1 <= x1:
                    new_shapes.append(
                        dict(
                            type="line",
                            xref=axis_ref,
                            yref="paper",
                            x0=jan1.isoformat(),
                            x1=jan1.isoformat(),
                            y0=0,
                            y1=1,
                            line=dict(
                                color=grid_color,
                                width=0.5,
                                dash="solid",
                            ),
                            layer="below",
                            name="year_boundary",
                        )
                    )

        if new_shapes:
            existing = list(fig.layout.shapes or [])
            fig.update_layout(shapes=existing + new_shapes)

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def apply(self, fig: Any, mode: str = "light") -> go.Figure:
        """
        Apply the full theme to a Plotly figure object.
        Mutates and returns the same figure instance.
        """
        fig_obj = (
            fig if isinstance(fig, go.Figure) else go.Figure(fig, skip_invalid=True)
        )
        is_dark = str(mode).lower() == "dark"

        bg_color = self.palette.BG_DARK if is_dark else self.palette.BG_LIGHT
        text_color = "#e5e7eb" if is_dark else "#111111"
        text_secondary = "rgba(226,232,240,0.4)" if is_dark else "rgba(15,23,42,0.5)"
        title_color = text_color
        grid_color = "rgba(148,163,184,0.12)" if is_dark else "rgba(15,23,42,0.08)"
        legend_bg = "rgba(15,23,42,0.85)" if is_dark else "rgba(255,255,255,0.95)"
        legend_border = "rgba(148,163,184,0.12)" if is_dark else "rgba(15,23,42,0.08)"
        chart_border = "rgba(148,163,184,0.15)" if is_dark else "rgba(15,23,42,0.12)"
        base_font_size = 10
        title_font_size = 14

        show_legend = self._should_show_legend(fig_obj)

        # Detect if chart has non-datetime x-axes (scatter/quadrant charts)
        has_numeric_xaxis = False
        for axis_name in self._axis_names(fig_obj, "xaxis"):
            axis_obj = getattr(fig_obj.layout, axis_name, None)
            axis_type = getattr(axis_obj, "type", None) if axis_obj else None
            if axis_type in ("linear", "log"):
                has_numeric_xaxis = True
                break
            if axis_type not in ("date", "category", "multicategory"):
                x_vals = self._x_values_for_axis(fig_obj, axis_name)
                if x_vals and not self._is_datetime_values(x_vals):
                    has_numeric_xaxis = True
                    break

        # --- Core layout ---
        # NOTE: Deliberately no `template` here. Setting a Plotly built-in template
        # (plotly_dark / simple_white) serialises template defaults into the JSON,
        # which the browser then applies on top of our client-side dark/light switch
        # in chartTheme.ts — causing text/axis colours to bleed from the wrong theme.
        fig_obj.update_layout(
            autosize=True,
            width=None,
            height=None,
            paper_bgcolor=bg_color,
            plot_bgcolor=bg_color,
            font=dict(family=self.font_main, color=text_color, size=base_font_size),
            colorway=self.palette.colorway,
            margin=self.margin,
            hovermode="closest" if has_numeric_xaxis else "x unified",
            hoverdistance=20,
            spikedistance=-1,
            showlegend=show_legend,
            title=dict(
                x=self.title_x,
                y=self.title_y,
                xanchor="left",
                yanchor="top",
                font=dict(
                    size=title_font_size, color=title_color, family=self.font_main
                ),
            ),
            legend=dict(
                orientation="v",
                x=self.legend_x,
                y=self.legend_y,
                xanchor="left",
                yanchor="top",
                bgcolor=legend_bg,
                bordercolor=legend_border,
                borderwidth=1,
                font=dict(size=base_font_size, color=text_color),
                itemsizing="constant",
                tracegroupgap=self.legend_gap,
                itemwidth=40,
            ),
            hoverlabel=dict(
                bgcolor=legend_bg,
                bordercolor=legend_border,
                font=dict(size=base_font_size, color=text_color, family=self.font_mono),
            ),
        )

        # --- Axis styling ---
        spike_color = "rgba(148,163,184,0.20)" if is_dark else "rgba(15,23,42,0.15)"

        x_axis_style = dict(
            showline=True,
            linewidth=1,
            linecolor=chart_border,
            mirror=True,
            ticks="outside",
            ticklen=4,
            tickcolor=chart_border,
            tickfont=dict(size=base_font_size, color=text_secondary),
            title_font=dict(size=base_font_size, color=text_secondary),
            showgrid=False,
            zeroline=False,
            showspikes=True,
            spikecolor=spike_color,
            spikethickness=0.5,
            spikedash="dot",
            spikemode="across",
            spikesnap="cursor",
            rangeslider=dict(visible=False),
        )
        y_axis_style = dict(
            showline=True,
            linewidth=1,
            linecolor=chart_border,
            mirror=True,
            ticks="outside",
            ticklen=4,
            tickcolor=chart_border,
            tickfont=dict(size=base_font_size, color=text_secondary),
            title_font=dict(size=base_font_size, color=text_secondary),
            showgrid=True,
            gridcolor=grid_color,
            griddash="dot",
            gridwidth=1,
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor=grid_color,
            showspikes=True,
            spikecolor=spike_color,
            spikethickness=0.5,
            spikedash="dot",
            spikemode="across",
            spikesnap="cursor",
        )
        fig_obj.update_xaxes(**x_axis_style)
        fig_obj.update_yaxes(**y_axis_style)

        # --- Annotations ---
        if fig_obj.layout.annotations:
            for ann in fig_obj.layout.annotations:
                existing_font_obj = getattr(ann, "font", None)
                if hasattr(existing_font_obj, "to_plotly_json"):
                    existing_font = dict(existing_font_obj.to_plotly_json() or {})
                elif isinstance(existing_font_obj, dict):
                    existing_font = dict(existing_font_obj)
                else:
                    existing_font = {}
                existing_font["color"] = text_color
                existing_font["size"] = base_font_size
                ann.update(font=existing_font)

        # --- Trace colors, axis sanitization, year lines, date padding ---
        self._color_traces(fig_obj)
        self._sanitize_axes(fig_obj)
        self._add_year_boundary_lines(fig_obj, is_dark)
        self._apply_datetime_padding(fig_obj)

        return fig_obj

    def apply_json(self, figure: Any, mode: str = "light") -> Any:
        """
        Apply theme to a Plotly JSON-like figure and return themed JSON.
        Uses pio.to_json + json.loads to guarantee all Plotly-internal types
        (Timestamps, numpy scalars, etc.) are serialized correctly.
        Safe fallback: returns original payload if rehydration/theming fails.
        """
        if figure is None:
            return figure
        try:
            import json as _json
            import plotly.io as _pio

            fig_obj = (
                figure
                if isinstance(figure, go.Figure)
                else go.Figure(figure, skip_invalid=True)
            )
            fig_themed = self.apply(fig_obj, mode=mode)
            return _json.loads(_pio.to_json(fig_themed, engine="json"))
        except Exception:
            return figure


# Global singleton used by API routers.
chart_theme = ChartTheme()


class Theme:
    """Wrapper class for backward compatibility and singleton access."""

    def __init__(self):
        self.palette = chart_theme.palette
        self.colors = self.palette.ASSET_MAP
        self.font = chart_theme.font_main

    def apply(self, fig: Any, mode: str = "light") -> go.Figure:
        return chart_theme.apply(fig, mode=mode)

    @staticmethod
    def _trace_color(trace: go.BaseTraceType) -> str:
        if getattr(trace, "line", None) and getattr(trace.line, "color", None):
            return trace.line.color
        marker = getattr(trace, "marker", None)
        if marker and getattr(marker, "color", None):
            if isinstance(marker.color, str):
                return marker.color
        return "#e5e7eb"

    @staticmethod
    def _is_datetime_x(values: Any) -> bool:
        return ChartTheme._is_datetime_values(values)

    @staticmethod
    def _x_bounds(fig: go.Figure) -> tuple[Any, Any]:
        all_x: list[Any] = []
        for trace in fig.data:
            xs = getattr(trace, "x", None)
            if xs is None:
                continue
            try:
                all_x.extend([x for x in xs if x is not None])
            except Exception:
                if xs is not None:
                    all_x.append(xs)
        if not all_x:
            return None, None
        return min(all_x), max(all_x)

    def format_chart(self, fig: go.Figure) -> go.Figure:
        return chart_theme.apply(fig, mode="light")
