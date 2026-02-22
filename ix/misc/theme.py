from __future__ import annotations

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


@dataclass(frozen=True)
class ChartTheme:
    """
    Canonical chart theme used by dashboard/studio delivery.
    Includes:
    - Date axis detection with right-side breathing room
    - Automatic legend visibility decision
    - Consistent title/axis/hover readability
    """

    palette: Color = field(default_factory=Color)
    width: int = 1000
    height: int = 600
    margin: Dict[str, int] = field(default_factory=lambda: dict(t=50, l=0, r=0, b=0))
    font_main: str = "Arial, Helvetica, sans-serif"
    font_mono: str = "Inter, SF Mono, monospace"
    right_padding_ratio: float = 0.05
    datetime_tickformat: str = "%Y-%m-%d"
    title_x: float = 0.01
    title_y: float = 0.98
    legend_x: float = 0.01
    legend_y: float = 0.98
    legend_gap: int = 0

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
            parsed = pd.to_datetime(s, errors="coerce")
            return parsed.notna().mean() >= 0.8
        except Exception:
            return False

    @staticmethod
    def _datetime_bounds(values: Any) -> tuple[pd.Timestamp | None, pd.Timestamp | None]:
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
        # Always include primary axis even if not explicitly present in layout.
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
        # xaxis -> x, xaxis2 -> x2, yaxis -> y, ...
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
                # Fallback for non-iterable/scalar values.
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
        names = set()
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

    def _apply_datetime_right_padding(self, fig: go.Figure) -> None:
        """
        If an X-axis is date-like, add right-side breathing room.
        If not date-like, skip (per user requirement).
        """
        for axis_name in self._axis_names(fig, "xaxis"):
            axis_obj = getattr(fig.layout, axis_name, None)
            axis_type = getattr(axis_obj, "type", None) if axis_obj else None
            if axis_type == "category":
                continue

            x_values = self._x_values_for_axis(fig, axis_name)
            if not x_values or not self._is_datetime_values(x_values):
                continue

            x0, x1 = self._datetime_bounds(x_values)
            if x0 is None or x1 is None or x0 == x1:
                continue

            pad = (x1 - x0) * self.right_padding_ratio
            if pad <= pd.Timedelta(0):
                continue

            updates: Dict[str, Any] = {"range": [x0, x1 + pad], "tickformat": self.datetime_tickformat}

            fig.update_layout({axis_name: updates})

    def apply(self, fig: Any, mode: str = "light") -> go.Figure:
        """
        Apply theme to a Plotly figure object.
        This mutates and returns the same figure instance.
        """
        fig_obj = fig if isinstance(fig, go.Figure) else go.Figure(fig, skip_invalid=True)
        is_dark = str(mode).lower() == "dark"

        bg_color = self.palette.BG_DARK if is_dark else self.palette.BG_LIGHT
        text_color = "#e5e7eb" if is_dark else "#111111"
        title_color = "#e5e7eb" if is_dark else "#000000"
        grid_color = "rgba(148,163,184,0.22)" if is_dark else "rgba(0,0,0,0.14)"
        legend_bg = "rgba(11,14,20,0.82)" if is_dark else "rgba(255,255,255,0.92)"
        legend_border = "rgba(148,163,184,0.38)" if is_dark else "rgba(15,23,42,0.16)"
        chart_border = "rgba(255,255,255,0.95)"
        base_font_size = 10
        title_font_size = 14

        show_legend = self._should_show_legend(fig_obj)

        fig_obj.update_layout(
            template="plotly_dark" if is_dark else "simple_white",
            paper_bgcolor=bg_color,
            plot_bgcolor=bg_color,
            font=dict(family=self.font_main, color=text_color, size=base_font_size),
            colorway=self.palette.colorway,
            margin=self.margin,
            hovermode="x",
            showlegend=show_legend,
            title=dict(
                x=self.title_x,
                y=self.title_y,
                xanchor="left",
                yanchor="top",
                font=dict(size=title_font_size, color=title_color, family=self.font_main),
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

        # Axis styling: horizontal grids emphasized, boxed readability.
        x_axis_style = dict(
            showline=True,
            linewidth=1,
            linecolor=chart_border,
            mirror=True,
            ticks="outside",
            ticklen=5,
            tickcolor=text_color,
            tickfont=dict(size=base_font_size, color=text_color),
            title_font=dict(size=base_font_size, color=text_color),
            showgrid=False,
            zeroline=False,
        )
        y_axis_style = dict(
            showline=True,
            linewidth=1,
            linecolor=chart_border,
            mirror=True,
            ticks="outside",
            ticklen=5,
            tickcolor=text_color,
            tickfont=dict(size=base_font_size, color=text_color),
            title_font=dict(size=base_font_size, color=text_color),
            showgrid=True,
            gridcolor=grid_color,
            zeroline=True,
            zerolinewidth=1,
            zerolinecolor=grid_color,
        )
        fig_obj.update_xaxes(**x_axis_style)
        fig_obj.update_yaxes(**y_axis_style)

        # Ensure annotation text remains readable (subplot titles, text labels, etc).
        if fig_obj.layout.annotations:
            for ann in fig_obj.layout.annotations:
                existing_font = getattr(ann, "font", None) or {}
                ann.update(font=dict(**existing_font, color=text_color, size=base_font_size))

        # Apply signature colors where trace color is unspecified.
        for trace in fig_obj.data:
            if self._trace_has_explicit_color(trace):
                continue
            mapped_color = self.palette.get_asset(str(getattr(trace, "name", "") or ""))
            if not mapped_color:
                continue
            if hasattr(trace, "line") and trace.line is not None:
                trace.line.color = mapped_color
            if hasattr(trace, "marker") and trace.marker is not None:
                try:
                    trace.marker.color = mapped_color
                except Exception:
                    pass

        self._apply_datetime_right_padding(fig_obj)
        return fig_obj

    def apply_json(self, figure: Any, mode: str = "light") -> Any:
        """
        Apply theme to a Plotly JSON-like figure and return themed JSON.
        Safe fallback: returns original payload if rehydration/themeing fails.
        """
        if figure is None:
            return figure
        try:
            fig_obj = figure if isinstance(figure, go.Figure) else go.Figure(figure, skip_invalid=True)
            return self.apply(fig_obj, mode=mode).to_plotly_json()
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

    def apply(self, fig, mode: str = "light"):
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
        # Backward-compatible entry point.
        # Keep light as default so title/axis remain black for presentation views.
        return chart_theme.apply(fig, mode="light")
