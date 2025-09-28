from typing import Optional
import pandas as pd
from ix import Series
import plotly.graph_objects as go
from ix.core.tech.regime import Regime1
from ix.misc.theme import theme

REGIME_STATES = ["Expansion", "Slowdown", "Contraction", "Recovery"]
REGIME_COLORS = [
    theme.colors.blue[400],  # Expansion
    theme.colors.amber[400],  # Slowdown
    theme.colors.red[400],  # Contraction
    theme.colors.emerald[400],  # Recovery
]


from ix.core.tech.ma import MACD


def OecdCliRegime() -> go.Figure:

    indicators = [
        "USA.LOLITOAA.STSA:PX_LAST",
        "TUR.LOLITOAA.STSA:PX_LAST",
        "IND.LOLITOAA.STSA:PX_LAST",
        "IDN.LOLITOAA.STSA:PX_LAST",
        "A5M.LOLITOAA.STSA:PX_LAST",
        "CHN.LOLITOAA.STSA:PX_LAST",
        "KOR.LOLITOAA.STSA:PX_LAST",
        "BRA.LOLITOAA.STSA:PX_LAST",
        "AUS.LOLITOAA.STSA:PX_LAST",
        "CAN.LOLITOAA.STSA:PX_LAST",
        "DEU.LOLITOAA.STSA:PX_LAST",
        "ESP.LOLITOAA.STSA:PX_LAST",
        "FRA.LOLITOAA.STSA:PX_LAST",
        "G4E.LOLITOAA.STSA:PX_LAST",
        "G7M.LOLITOAA.STSA:PX_LAST",
        "GBR.LOLITOAA.STSA:PX_LAST",
        "ITA.LOLITOAA.STSA:PX_LAST",
        "JPN.LOLITOAA.STSA:PX_LAST",
        "MEX.LOLITOAA.STSA:PX_LAST",
    ]

    data = (
        pd.DataFrame(
            {key: Regime1(MACD(Series(key)).histogram).regime for key in indicators}
        )
        .sort_index()
        .dropna(how="all")
    )
    data.index = pd.to_datetime(data.index)
    regimes = (
        data.apply(lambda x: x.value_counts(normalize=True) * 100, axis=1)
        .astype(float)
        .sort_index()
        .fillna(0)
    )

    fig = go.Figure()
    for i, state in enumerate(REGIME_STATES):

        series = regimes[state]
        fig.add_trace(
            go.Bar(
                x=series.index,
                y=series.values,
                name=state,
                marker_color=REGIME_COLORS[i],
                hovertemplate=f"<b>{state}</b>: %{{y:.2f}}%<extra></extra>",
            )
        )

    p = Series("ACWI US Equity:PX_LAST").resample("W").last().pct_change(52).dropna()
    fig.add_trace(
        go.Scatter(
            x=p.index,
            y=p.values,
            name="ACWI YoY",
            yaxis="y2",
            line=dict(color=theme.colors.indigo[900], width=2),
            hovertemplate="%{y:.2f}%<extra></extra>",
        )
    )

    fig.update_layout(
        {
            "title": dict(
                text="OECD CLI Regime",
                font=dict(size=16, color=theme.colors.text),
                y=0.90,
                x=0.5,
                xanchor="center",
                yanchor="bottom",
                yref="container",
            ),
            "font": dict(family=theme.fonts.base, size=12, color=theme.colors.text),
            "margin": dict(l=20, r=20, t=40, b=30),
            "hovermode": "x unified",
            "hoverlabel": dict(
                bgcolor=theme.colors.surface,
                bordercolor=theme.colors.border,
                font=dict(color=theme.colors.text, size=11),
            ),
            "legend": dict(
                x=0.5,
                y=-0.15,
                xanchor="center",
                yanchor="top",
                orientation="h",
                bgcolor="rgba(0,0,0,0)",
                bordercolor=theme.colors.border,
                borderwidth=1,
                font=dict(color=theme.colors.text, size=11),
                itemsizing="trace",
                itemwidth=30,
                yref="paper",
                traceorder="normal",
            ),
            "paper_bgcolor": theme.colors.background,
            "plot_bgcolor": theme.colors.background_subtle,
            "xaxis": dict(
                gridcolor=theme.colors.border,
                gridwidth=0.5,
                zeroline=False,
                showline=True,
                linecolor=theme.colors.border,
                tickformat="%b\n%Y",
                automargin="height",
                tickfont=dict(color=theme.colors.text_muted, size=10),
            ),
            "yaxis": dict(
                gridcolor=theme.colors.border,
                gridwidth=0.5,
                zeroline=True,
                zerolinecolor=theme.colors.text_subtle,
                zerolinewidth=1,
                tickfont=dict(color=theme.colors.text_muted, size=10),
                domain=[0, 0.9],
                title=dict(
                    text="Regime Distribution",
                    font=dict(color=theme.colors.text, size=12),
                ),
            ),
            "yaxis2": dict(
                overlaying="y",
                side="right",
                title="ACWI 52W % Change",
                tickfont=dict(color=theme.colors.text_muted, size=10),
                tickformat = ".0%",
            ),
            "uniformtext": dict(minsize=10, mode="show"),
            "autosize": True,
            "height": 500,
            "barmode": "stack",
        }
    )

    return fig


def PmiMfgRegime() -> go.Figure:

    indicators = [
        "NTCPMIMFGSA_WLD:PX_LAST",
        "NTCPMIMFGMESA_US:PX_LAST",
        "ISMPMI_M:PX_LAST",
        "NTCPMIMFGSA_CA:PX_LAST",
        "NTCPMIMFGSA_EUZ:PX_LAST",
        "NTCPMIMFGSA_DE:PX_LAST",
        "NTCPMIMFGSA_FR:PX_LAST",
        "NTCPMIMFGSA_IT:PX_LAST",
        "NTCPMIMFGSA_ES:PX_LAST",
        "NTCPMIMFGSA_GB:PX_LAST",
        "NTCPMIMFGSA_JP:PX_LAST",
        "NTCPMIMFGSA_KR",
        "NTCPMIMFGSA_IN:PX_LAST",
        "NTCPMIMFGNSA_CN:PX_LAST",
    ]

    data = (
        pd.DataFrame(
            {key: Regime1(MACD(Series(key)).histogram).regime for key in indicators}
        )
        .sort_index()
        .dropna(how="all")
    )
    data.index = pd.to_datetime(data.index)
    regimes = (
        data.apply(lambda x: x.value_counts(normalize=True) * 100, axis=1)
        .astype(float)
        .sort_index()
        .fillna(0)
    )

    fig = go.Figure()
    for i, state in enumerate(REGIME_STATES):

        series = regimes[state]
        fig.add_trace(
            go.Bar(
                x=series.index,
                y=series.values,
                name=state,
                marker_color=REGIME_COLORS[i],
                hovertemplate=f"<b>{state}</b>: %{{y:.2f}}%<extra></extra>",
            )
        )

    p = Series("ACWI US Equity:PX_LAST").resample("W").last().pct_change(52).dropna()
    fig.add_trace(
        go.Scatter(
            x=p.index,
            y=p.values,
            name="ACWI YoY",
            yaxis="y2",
            line=dict(color=theme.colors.indigo[900], width=2),
            hovertemplate="%{y:.2f}%<extra></extra>",
        )
    )

    fig.update_layout(
        {
            "title": dict(
                text="PMI Manufacturing Regime",
                font=dict(size=16, color=theme.colors.text),
                y=0.90,
                x=0.5,
                xanchor="center",
                yanchor="bottom",
                yref="container",
            ),
            "font": dict(family=theme.fonts.base, size=12, color=theme.colors.text),
            "margin": dict(l=20, r=20, t=40, b=30),
            "hovermode": "x unified",
            "hoverlabel": dict(
                bgcolor=theme.colors.surface,
                bordercolor=theme.colors.border,
                font=dict(color=theme.colors.text, size=11),
            ),
            "legend": dict(
                x=0.5,
                y=-0.15,
                xanchor="center",
                yanchor="top",
                orientation="h",
                bgcolor="rgba(0,0,0,0)",
                bordercolor=theme.colors.border,
                borderwidth=1,
                font=dict(color=theme.colors.text, size=11),
                itemsizing="trace",
                itemwidth=30,
                yref="paper",
                traceorder="normal",
            ),
            "paper_bgcolor": theme.colors.background,
            "plot_bgcolor": theme.colors.background_subtle,
            "xaxis": dict(
                gridcolor=theme.colors.border,
                gridwidth=0.5,
                zeroline=False,
                showline=True,
                linecolor=theme.colors.border,
                tickformat="%b\n%Y",
                automargin="height",
                tickfont=dict(color=theme.colors.text_muted, size=10),
            ),
            "yaxis": dict(
                gridcolor=theme.colors.border,
                gridwidth=0.5,
                zeroline=True,
                zerolinecolor=theme.colors.text_subtle,
                zerolinewidth=1,
                tickfont=dict(color=theme.colors.text_muted, size=10),
                domain=[0, 0.9],
                title=dict(
                    text="Regime Distribution",
                    font=dict(color=theme.colors.text, size=12),
                ),
            ),
            "yaxis2": dict(
                overlaying="y",
                side="right",
                title="ACWI 52W % Change",
                tickfont=dict(color=theme.colors.text_muted, size=10),
                tickformat = ".0%",
            ),
            "uniformtext": dict(minsize=10, mode="show"),
            "autosize": True,
            "height": 500,
            "barmode": "stack",
        }
    )

    return fig


def PmiSrvRegime() -> go.Figure:

    indicators = [
        "NTCPMISVCBUSACTSA_WLD:PX_LAST",
        "NTCPMISVCBUSACTMESA_US:PX_LAST",
        "ISMNMI_NM:PX_LAST",
        "NTCPMISVCBUSACTSA_EUZ:PX_LAST",
        "NTCPMISVCBUSACTSA_DE:PX_LAST",
        "NTCPMISVCBUSACTSA_FR:PX_LAST",
        "NTCPMISVCBUSACTSA_IT:PX_LAST",
        "'NTCPMISVCBUSACTSA_ES",
        "NTCPMISVCBUSACTSA_GB:PX_LAST",
        "NTCPMISVCPSISA_AU",
        "NTCPMISVCBUSACTSA_JP:PX_LAST",
        "NTCPMISVCBUSACTSA_CN:PX_LAST",
        "NTCPMISVCBUSACTSA_IN",
        "NTCPMISVCBUSACTSA_BR:PX_LAST",
    ]

    data = (
        pd.DataFrame(
            {key: Regime1(MACD(Series(key)).histogram).regime for key in indicators}
        )
        .sort_index()
        .dropna(how="all")
    )
    data.index = pd.to_datetime(data.index)
    regimes = (
        data.apply(lambda x: x.value_counts(normalize=True) * 100, axis=1)
        .astype(float)
        .sort_index()
        .fillna(0)
    )

    fig = go.Figure()
    for i, state in enumerate(REGIME_STATES):

        series = regimes[state]
        fig.add_trace(
            go.Bar(
                x=series.index,
                y=series.values,
                name=state,
                marker_color=REGIME_COLORS[i],
                hovertemplate=f"<b>{state}</b>: %{{y:.2f}}%<extra></extra>",
            )
        )

    p = Series("ACWI US Equity:PX_LAST").resample("W").last().pct_change(52).dropna()
    fig.add_trace(
        go.Scatter(
            x=p.index,
            y=p.values,
            name="ACWI YoY",
            yaxis="y2",
            line=dict(color=theme.colors.indigo[900], width=2),
            hovertemplate="%{y:.2f}%<extra></extra>",
        )
    )

    fig.update_layout(
        {
            "title": dict(
                text="PMI Manufacturing Regime",
                font=dict(size=16, color=theme.colors.text),
                y=0.90,
                x=0.5,
                xanchor="center",
                yanchor="bottom",
                yref="container",
            ),
            "font": dict(family=theme.fonts.base, size=12, color=theme.colors.text),
            "margin": dict(l=20, r=20, t=40, b=30),
            "hovermode": "x unified",
            "hoverlabel": dict(
                bgcolor=theme.colors.surface,
                bordercolor=theme.colors.border,
                font=dict(color=theme.colors.text, size=11),
            ),
            "legend": dict(
                x=0.5,
                y=-0.15,
                xanchor="center",
                yanchor="top",
                orientation="h",
                bgcolor="rgba(0,0,0,0)",
                bordercolor=theme.colors.border,
                borderwidth=1,
                font=dict(color=theme.colors.text, size=11),
                itemsizing="trace",
                itemwidth=30,
                yref="paper",
                traceorder="normal",
            ),
            "paper_bgcolor": theme.colors.background,
            "plot_bgcolor": theme.colors.background_subtle,
            "xaxis": dict(
                gridcolor=theme.colors.border,
                gridwidth=0.5,
                zeroline=False,
                showline=True,
                linecolor=theme.colors.border,
                tickformat="%b\n%Y",
                automargin="height",
                tickfont=dict(color=theme.colors.text_muted, size=10),
            ),
            "yaxis": dict(
                gridcolor=theme.colors.border,
                gridwidth=0.5,
                zeroline=True,
                zerolinecolor=theme.colors.text_subtle,
                zerolinewidth=1,
                tickfont=dict(color=theme.colors.text_muted, size=10),
                domain=[0, 0.9],
                title=dict(
                    text="Regime Distribution",
                    font=dict(color=theme.colors.text, size=12),
                ),
            ),
            "yaxis2": dict(
                overlaying="y",
                side="right",
                title="ACWI 52W % Change",
                tickfont=dict(color=theme.colors.text_muted, size=10),
                tickformat = ".0%",
            ),
            "uniformtext": dict(minsize=10, mode="show"),
            "autosize": True,
            "height": 500,
            "barmode": "stack",
        }
    )

    return fig
