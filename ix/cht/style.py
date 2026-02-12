import plotly.graph_objects as go


def finalize_axis_colors(fig: go.Figure, color: str = None) -> go.Figure:
    """
    Ensures all axis titles, ticks, and lines have a consistent color.
    If color is None, it attempts to detect based on paper_bgcolor.
    """
    if color is None:
        # Detect based on background
        bg = fig.layout.paper_bgcolor
        if (
            bg
            and isinstance(bg, str)
            and (bg.startswith("rgb(0,0,0)") or bg == "black" or bg == "#000000")
        ):
            color = "#e2e8f0"
        else:
            color = "#000000"

    for attr in dir(fig.layout):
        if attr.startswith("yaxis") or attr.startswith("xaxis"):
            axis = getattr(fig.layout, attr)
            if axis and hasattr(axis, "update"):
                axis.update(
                    title_font=dict(color=color),
                    tickfont=dict(color=color),
                    tickcolor=color,
                    linecolor=color,
                )
                if (
                    hasattr(axis, "title")
                    and axis.title
                    and hasattr(axis.title, "font")
                ):
                    try:
                        axis.title.font.color = color
                    except:
                        pass
    return fig


def apply_academic_style(fig: go.Figure, force_dark: bool = True) -> go.Figure:
    """
    Applies a clean, academic/Goldman Sachs-style theme to the Plotly figure.
    Features:
    - Adaptive background (defaults to Dark for premium look)
    - Boxed axes (mirror=True)
    - Modern Inter/Outfit fonts
    - Top-left align title and legend
    """
    # Detect background theme or use force_dark
    bg = fig.layout.paper_bgcolor
    if bg in ["#0d0f12", "black", "#000000"] or force_dark:
        is_dark = True
    else:
        is_dark = False

    # 1. Base Template
    fig.update_layout(template="plotly_dark" if is_dark else "simple_white")

    # 2. Fonts & Colors
    font_family = "Inter, sans-serif"
    header_font = "Outfit, sans-serif"
    font_color = "#f8fafc" if is_dark else "#0f172a"
    bg_color = "#0d0f12" if is_dark else "white"
    grid_line_color = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0,0,0,0.05)"
    plot_bg = "rgba(255, 255, 255, 0.01)" if is_dark else "white"

    # 3. Layout General
    fig.update_layout(
        font=dict(family=font_family, color=font_color, size=12),
        width=800,
        height=500,
        margin=dict(l=50, r=20, t=60, b=40),
        plot_bgcolor=plot_bg,
        paper_bgcolor=bg_color,
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#1e293b" if is_dark else "white",
            font_color=font_color,
            bordercolor="rgba(255,255,255,0.1)" if is_dark else "#e2e8f0",
            font=dict(family=font_family, size=12),
        ),
    )

    # 4. Title Styling
    fig.update_layout(
        title=dict(
            x=0.01,
            y=0.95,
            xanchor="left",
            yanchor="top",
            font=dict(size=14, color=font_color, family=header_font),
        )
    )

    # 5. Legend Styling (Top-Left inside plot)
    fig.update_layout(
        legend=dict(
            y=0.99,
            x=0.01,
            xanchor="left",
            yanchor="top",
            bgcolor="rgba(13, 15, 18, 0.8)" if is_dark else "rgba(255,255,255,0.8)",
            bordercolor="rgba(255,255,255,0.1)" if is_dark else "rgba(0,0,0,0.1)",
            borderwidth=1,
            font=dict(size=10, color=font_color),
        )
    )

    # 6. Axis Styling (The "Boxed" look)
    axis_style = dict(
        showline=True,
        linewidth=1,
        linecolor="rgba(255,255,255,0.2)" if is_dark else font_color,
        mirror=True,  # Boxed effect
        ticks="outside",
        ticklen=5,
        tickcolor=font_color,
        tickfont=dict(color=font_color, family=font_family),
        title_font=dict(color=font_color, family=header_font),
        showgrid=False,
        zerolinecolor=font_color,
        zerolinewidth=1,
    )

    fig.update_xaxes(**axis_style)
    fig.update_yaxes(**axis_style)

    # Ensure global font color and specific axis title color is black
    fig.update_layout(
        font_color=font_color,
        title_font_color=font_color,
        xaxis_title_font_color=font_color,
        yaxis_title_font_color=font_color,
        xaxis=dict(title_font=dict(color=font_color)),
        yaxis=dict(title_font=dict(color=font_color)),
        legend=dict(font=dict(color=font_color)),
    )

    # Iterate over all layout properties to find x/y axes and force title color
    # This handles secondary axes (yaxis2, yaxis3) which are not covered by fig.update_yaxes
    for attr in dir(fig.layout):
        if attr.startswith("yaxis") or attr.startswith("xaxis"):
            axis = getattr(fig.layout, attr)
            if axis and hasattr(axis, "update"):
                update_dict = {}
                update_dict["title_font"] = dict(color=font_color)
                update_dict["tickfont"] = dict(color=font_color)
                update_dict["tickcolor"] = font_color
                update_dict["linecolor"] = font_color

                if (
                    hasattr(axis, "title")
                    and axis.title
                    and hasattr(axis.title, "font")
                ):
                    try:
                        axis.title.font.color = font_color
                    except:
                        pass

                axis.update(**update_dict)

    return fig


def add_zero_line(fig: go.Figure) -> go.Figure:
    """Adds a zero line adaptive to the theme."""
    bg = fig.layout.paper_bgcolor
    is_dark = bg in ["#0d0f12", "black", "#000000"]
    line_color = "rgba(255,255,255,0.4)" if is_dark else "rgba(0,0,0,0.3)"
    fig.add_hline(y=0, line_width=1, line_color=line_color, layer="below")
    return fig


# Helper to format values in legend
def get_value_label(series, name: str, fmt: str = ".2f") -> str:
    import pandas as pd

    if series is None or series.dropna().empty:
        return name
    val = float(series.dropna().iloc[-1])
    return f"{name} ({val:{fmt}})"
