import plotly.graph_objects as go


def finalize_axis_colors(fig: go.Figure) -> go.Figure:
    """
    Ensures all axis titles, ticks, and lines are black.
    Call this AFTER all layout updates to guarantee styling is applied.
    """
    for attr in dir(fig.layout):
        if attr.startswith("yaxis") or attr.startswith("xaxis"):
            axis = getattr(fig.layout, attr)
            if axis and hasattr(axis, "update"):
                # Force all colors to black
                axis.update(
                    title_font=dict(color="#000000"),
                    tickfont=dict(color="#000000"),
                    tickcolor="#000000",
                    linecolor="#000000",
                )
                # Also set directly on title.font if it exists
                if (
                    hasattr(axis, "title")
                    and axis.title
                    and hasattr(axis.title, "font")
                ):
                    try:
                        axis.title.font.color = "#000000"
                    except:
                        pass
    return fig


def apply_academic_style(fig: go.Figure) -> go.Figure:
    """
    Applies a clean, academic/Goldman Sachs-style theme to the Plotly figure.
    Features:
    - White background
    - Boxed axes (mirror=True)
    - Times New Roman / Arial fonts
    - Top-left align title and legend
    """
    # 1. Base Template
    fig.update_layout(template="simple_white")

    # 2. Fonts & Colors
    font_family = "Roboto, sans-serif"
    font_color = "#000000"

    # 3. Layout General
    fig.update_layout(
        font=dict(family=font_family, color=font_color, size=12),
        width=800,
        height=500,
        margin=dict(l=50, r=20, t=60, b=40),
        plot_bgcolor="white",
        paper_bgcolor="white",
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="white",
            font_color="black",
            bordercolor="#e2e8f0",
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
            font=dict(size=14, color=font_color, family=font_family),
        )
    )

    # 5. Legend Styling (Top-Left inside plot)
    fig.update_layout(
        legend=dict(
            y=0.99,
            x=0.01,
            xanchor="left",
            yanchor="top",
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="rgba(0,0,0,0.1)",
            borderwidth=1,
            font=dict(size=10, color=font_color),
        )
    )

    # 6. Axis Styling (The "Boxed" look)
    axis_style = dict(
        showline=True,
        linewidth=1,
        linecolor=font_color,
        mirror=True,  # Boxed effect
        ticks="outside",
        ticklen=5,
        tickcolor=font_color,
        tickfont=dict(color=font_color),
        title_font=dict(color=font_color),
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
    """Adds a simple black zero line."""
    fig.add_hline(y=0, line_width=1, line_color="black", opacity=0.3, layer="below")
    return fig


# Helper to format values in legend
def get_value_label(series, name: str, fmt: str = ".2f") -> str:
    import pandas as pd

    if series is None or series.dropna().empty:
        return name
    val = float(series.dropna().iloc[-1])
    return f"{name} ({val:{fmt}})"
