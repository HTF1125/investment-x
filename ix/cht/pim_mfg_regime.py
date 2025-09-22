from ix.cht import apply_layout
import plotly.graph_objects as go
from ix.dash.settings import theme

# use theme.chart_colors


def layout(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        paper_bgcolor=theme.bg,
        plot_bgcolor=theme.bg_light,
        font=dict(
            color=theme.text,
            family="Roboto, Helvetica Neue, Arial, sans-serif",
            size=12,
        ),
        title=dict(
            font=dict(size=14, color=theme.text),
            y=0.98,
            x=0.02,
            xanchor="left",
            yanchor="top",
        ),
        legend=dict(
            itemwidth=100,
            x=0.01,
            y=0.99,
            orientation="h",
            bgcolor="rgba(0,0,0,0)",
            bordercolor=theme.border,
            borderwidth=1,
            font=dict(
                color=theme.text,
                size=11,
            ),
            # itemclick="toggleothers",
            # itemdoubleclick="toggle",
            itemsizing="trace",
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor=theme.bg_light,
            bordercolor=theme.border,
            font=dict(color=theme.text, size=11),
        ),
        margin=dict(
            l=16,
            r=12,
            t=24,
            b=8,
        ),
        xaxis=dict(
            gridcolor=theme.border,
            gridwidth=1,
            zeroline=False,
            showline=True,
            linecolor=theme.border,
            linewidth=1,
            tickfont=dict(color=theme.text_light, size=10),
        ),
        yaxis=dict(
            gridcolor=theme.border,
            gridwidth=1,
            zeroline=True,
            zerolinecolor=theme.text_light,
            zerolinewidth=1,
        ),
        autosize=True,
    )
    return fig


def pmi_mfg_regime():
    from ix.db.query import PMI_Manufacturing_Regime
    regimes = PMI_Manufacturing_Regime().loc["2023":]

    # Create a new plotly figure and add traces from investor_positions data
    fig = go.Figure()

    # Use theme.chart_colors for bar colors
    colors = theme.chart_colors
    for i, (name, series) in enumerate(regimes.items()):
        color = colors[i % len(colors)]
        latest = series.iloc[-1]
        fig.add_trace(
            go.Bar(
                x=series.index,
                y=series.values,
                name=f"{name}: {latest:.2f}",
                marker_color=color,
            )
        )
    fig.update_layout(
        barmode="stack",
        title=dict(text=f"PMI Manufacturing Regime"),
    )

    # Apply layout and show the plotly figure
    fig = layout(fig)

    return fig


def oecd_cli_regime():
    from ix.db.query import oecd_cli_regime as regime

    regimes = regime()

    # Create a new plotly figure and add traces from investor_positions data
    fig = go.Figure(layout=dict(barmode="stack", title=dict(text=f"OECD CLI Regime")))

    # Use theme.chart_colors for bar colors
    colors = theme.chart_colors
    for i, (name, series) in enumerate(regimes.items()):
        color = colors[i % len(colors)]
        latest = series.iloc[-1]
        fig.add_trace(
            go.Bar(
                x=series.index,
                y=series.values,
                name=f"{name}: {latest:.2f}",
                marker_color=color,
            )
        )

    # Apply layout and show the plotly figure
    fig = layout(fig)

    return fig
