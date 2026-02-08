from __future__ import annotations

from dataclasses import dataclass, field

from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ChartTheme:
    """

    Standard premium chart theme for Investment-X.
    """

    # Core sizing / template

    width: int = 1000

    height: int = 500

    template: str = "plotly_white"

    # Typography

    font_family: str = "Inter, Roboto, Arial, sans-serif"

    font_color: str = "#000000"  # True Black

    # Grid / axis styling

    grid_color: str = "rgba(0,0,0,0.06)"

    zero_line_color: str = "rgba(0,0,0,0.25)"

    axis_line_color: str = "rgba(0,0,0,0.25)"

    # Line widths

    line_width_primary: float = 2.6

    line_width_secondary: float = 2.0

    line_width_tertiary: float = 1.8

    # Palette

    color_scheme: Dict[str, str] = field(
        default_factory=lambda: {
            "magenta": "#ff00b8",
            "blue": "#2a7fff",
            "cyan": "#00d6c6",
            "dark_blue": "#2c2f7a",
            "orange": "#f59e0b",
            "green": "#22c55e",
            "grey": "#94a3b8",
            # Aliases
            "price": "#ff00b8",
            "yoy": "#2a7fff",
            "accent": "#00d6c6",
            "cycle": "#2c2f7a",
            "neutral": "#94a3b8",
            "accent2": "#f59e0b",
            "accent3": "#22c55e",
            "negative": "#ef4444",
        }
    )

    # Preferred default order for Plotly's colorway

    colorway_keys: List[str] = field(
        default_factory=lambda: [
            "magenta",
            "blue",
            "cyan",
            "dark_blue",
            "orange",
            "green",
            "grey",
        ]
    )

    def __post_init__(self) -> None:

        # Inject grid/zero into scheme for consistency

        cs = dict(self.color_scheme)

        cs["grid"] = self.grid_color

        cs["zero"] = self.zero_line_color

        object.__setattr__(self, "color_scheme", cs)

    @property
    def colorway(self) -> List[str]:

        return [
            self.color_scheme[k] for k in self.colorway_keys if k in self.color_scheme
        ]

    def color(self, key: str, default: Optional[str] = None) -> str:

        return self.color_scheme.get(key, default or "#000000")

    def apply(self, fig: Any) -> Any:
        """

        Apply theme defaults to a Plotly figure.

        Forces colors to bypass template defaults.
        """

        # Set template to None to prevent Plotly from applying defaults that might override our colors

        fig.update_layout(template=None)

        fig.update_layout(
            width=self.width,
            height=self.height,
            font=dict(family=self.font_family, color="#000000", size=12),
            colorway=self.colorway,
            paper_bgcolor="#FFFFFF",
            plot_bgcolor="#FFFFFF",
            margin=dict(l=60, r=60, t=100, b=60),
            hovermode="x unified",
            # Legend styling
            legend=dict(
                orientation="h",
                x=0.5,
                xanchor="center",
                y=1.05,
                yanchor="top",
                borderwidth=1,
                bordercolor="rgba(0,0,0,0.15)",
                font=dict(size=11, color="#000000"),
            ),
            # General title default
            title=dict(x=0.5, xanchor="center", font=dict(size=22, color="#000000")),
            # Unified hover box
            hoverlabel=dict(
                bgcolor="#FFFFFF",
                font_size=11,
                font_family=self.font_family,
                font_color="#000000",
                bordercolor="rgba(0,0,0,0.15)",
                align="left",
                namelength=-1,
            ),
        )

        # Apply axes configuration

        axes_config = dict(
            showgrid=True,
            gridcolor=self.grid_color,
            zeroline=False,
            ticks="outside",
            ticklen=4,
            tickcolor="#000000",
            showline=True,
            linecolor="#000000",
            linewidth=1,
            mirror=False,
            tickfont=dict(color="#000000", size=11),
            title=dict(font=dict(color="#000000", size=13)),
        )

        fig.update_xaxes(**axes_config)

        fig.update_yaxes(**axes_config)

        # Fix secondary axes if they exist (only if created via make_subplots with secondary_y=True)
        # Avoids: "In order to reference traces by row and column, you must first use plotly.tools.make_subplots"
        try:
            # Check if figure has subplot structure
            if hasattr(fig, "_grid_ref") and fig._grid_ref:
                fig.update_yaxes(secondary_y=True, showgrid=False)
            elif "yaxis2" in fig.layout:
                # Fallback for manually added secondary axes
                fig.update_layout(yaxis2=dict(showgrid=False))
        except:
            pass

        # Force all existing trace text/font colors to black if they have such properties

        for trace in fig.data:

            if hasattr(trace, "textfont"):

                trace.textfont.color = "#000000"

            if hasattr(trace, "marker") and hasattr(trace.marker, "line"):

                pass  # placeholder

        return fig


# Global THEME singleton
chart_theme = ChartTheme()


# Backward compatibility for existing code that might use the old Theme class structure

# though the user asked to update it to the new style.


class Theme:

    def __init__(self):

        self.colors = chart_theme.color_scheme

        self.font = chart_theme.font_color

        self.grid = chart_theme.grid_color

    def apply(self, fig):

        return chart_theme.apply(fig)
