from __future__ import annotations

from dataclasses import dataclass, field

from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Color:
    """Centralized color management for the Investment-X design system."""

    # Neon Palette
    CYAN: str = "#00D2FF"
    MAGENTA: str = "#FF69B4"
    PURPLE: str = "#A020F0"
    EMERALD: str = "#00FF66"
    AMBER: str = "#FFB84D"
    ROSE: str = "#ef4444"
    SKY: str = "#3b82f6"
    SLATE: str = "#94a3b8"

    # Theme Specifics
    BG_DARK: str = "#0B0E14"
    BG_LIGHT: str = "#FFFFFF"
    LEGEND_DARK: str = "#3c3c3c"

    # Asset Mapping (Signature colors for specific tickers/names)
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
        """Returns the primary neon sequence for multi-series charts."""
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
        """Retrieves a specific color for a known asset name."""
        return self.ASSET_MAP.get(name.lower())


@dataclass(frozen=True)
class ChartTheme:
    """
    Advanced premium chart theme for Investment-X.
    Implements a high-contrast 'Neon Research' aesthetic.
    """

    # Design System
    palette: Color = field(default_factory=Color)

    # Sizing & Layout
    width: int = 1000
    height: int = 600
    margin: Dict[str, int] = field(default_factory=lambda: dict(t=80, l=40, r=40, b=60))

    # Typography
    font_main: str = "Arial, Helvetica, sans-serif"
    font_mono: str = "Inter, SF Mono, monospace"

    def apply(self, fig: Any, mode: str = "light") -> Any:
        """
        Apply the theme to a Plotly figure.

        Args:
            fig: The Plotly figure object.
            mode: 'light' or 'dark' (Defaulting to light to match user reference image).
        """
        is_dark = mode == "dark"
        bg_color = self.palette.BG_DARK if is_dark else self.palette.BG_LIGHT
        text_color = "#FFFFFF" if is_dark else "#000000"
        grid_color = "rgba(255,255,255,0.1)" if is_dark else "rgba(0,0,0,0.4)"
        legend_bg = "rgba(40, 44, 52, 0.9)" if not is_dark else "rgba(11, 14, 20, 0.8)"

        # 1. Base Layout
        fig.update_layout(
            template=None,
            paper_bgcolor=bg_color,
            plot_bgcolor=bg_color,
            font=dict(family=self.font_main, color=text_color, size=12),
            colorway=self.palette.colorway,
            margin=self.margin,
            hovermode="x unified",
            # Advanced Multi-tier Title
            title=dict(
                x=0.02,
                y=0.98,
                xanchor="left",
                yanchor="top",
                font=dict(size=14, color=text_color, family=self.font_main),
            ),
            # 'Picture' Style Legend: Top-Left, Dark Box, Rounded
            legend=dict(
                orientation="v",
                x=0.03,
                y=0.97,
                xanchor="left",
                yanchor="top",
                bgcolor=self.palette.LEGEND_DARK,
                bordercolor="rgba(255,255,255,0.1)",
                borderwidth=1,
                font=dict(size=10, color="#FFFFFF"),
                itemsizing="constant",
            ),
            # Hover Box
            hoverlabel=dict(
                bgcolor=legend_bg,
                font=dict(size=12, color="#FFFFFF", family=self.font_mono),
                bordercolor="rgba(255,255,255,0.2)",
            ),
        )

        # 2. Axis Configuration (Minimalist Horizontal focus)
        axis_config = dict(
            showline=True,
            linecolor=text_color,
            linewidth=1.2,
            gridcolor=grid_color,
            gridwidth=1,
            zeroline=False,
            ticks="outside",
            ticklen=6,
            tickcolor=text_color,
            tickfont=dict(size=11, color=text_color),
            title=dict(font=dict(size=13, color=text_color)),
        )

        # Apply to all X axes
        fig.update_xaxes(
            **axis_config,
            showgrid=False,
            showline=True,
        )

        # Apply to all Y axes (The Pulse: Horizontal lines only)
        fig.update_yaxes(
            **axis_config,
            showgrid=True,
            showline=False,  # Standard minimalist: hide the vertical spine
            tickprefix="",
            ticksuffix="   ",
        )

        # Specialized handling for secondary Y-axes (often used in dual-pane charts)
        try:
            for i in range(2, 11):
                attr = f"yaxis{i}"
                if attr in fig.layout:
                    fig.update_layout(
                        {attr: {**axis_config, "showline": False, "showgrid": False}}
                    )
        except:
            pass

        # 3. Trace Styling (Neon Mapping & Smoothness)
        for trace in fig.data:
            trace_name = str(trace.name or "")

            # Map name to color using palette mapping
            mapped_color = self.palette.get_asset(trace_name)
            if mapped_color:
                if hasattr(trace, "line"):
                    trace.line.color = mapped_color
                    trace.line.width = 2.8  # Slightly thicker for neon effect
                elif hasattr(trace, "marker"):
                    trace.marker.color = mapped_color

            # Aesthetic Smoothing
            if hasattr(trace, "line") and trace.type == "scatter":
                trace.line.shape = "spline"
                trace.line.smoothing = 1.3

        return fig


# Global THEME singleton
chart_theme = ChartTheme()


class Theme:
    """Wrapper class for backward compatibility and singleton access."""

    def __init__(self):
        self.palette = chart_theme.palette
        self.colors = self.palette.ASSET_MAP
        self.font = chart_theme.font_main

    def apply(self, fig):
        return chart_theme.apply(fig)
