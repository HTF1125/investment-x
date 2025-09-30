from typing import Optional
import pandas as pd
from ix import Series
import plotly.graph_objects as go
from ix.core.tech.regime import Regime1
from ix.misc.theme import theme
from .base import timeseries_layout

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

    # Apply dark theme layout
    layout = timeseries_layout.copy()
    layout.update(
        {
            "title": dict(
                text="OECD CLI Regime",
                x=0.05,
                font=dict(size=14, family="Arial Black", color="#FFFFFF"),
            ),
            "yaxis": dict(
                title=dict(text="Regime Distribution", font=dict(color="#FFFFFF")),
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=True,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
            ),
            "yaxis2": dict(
                title=dict(text="ACWI 52W % Change", font=dict(color="#FFFFFF")),
                overlaying="y",
                side="right",
                tickformat=".0%",
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=False,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
            ),
            "barmode": "stack",
        }
    )
    fig.update_layout(layout)

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

    # Apply dark theme layout
    layout = timeseries_layout.copy()
    layout.update(
        {
            "title": dict(
                text="PMI Manufacturing Regime",
                x=0.05,
                font=dict(size=14, family="Arial Black", color="#FFFFFF"),
            ),
            "yaxis": dict(
                title=dict(text="Regime Distribution", font=dict(color="#FFFFFF")),
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=True,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
            ),
            "yaxis2": dict(
                title=dict(text="ACWI 52W % Change", font=dict(color="#FFFFFF")),
                overlaying="y",
                side="right",
                tickformat=".0%",
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=False,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
            ),
            "barmode": "stack",
        }
    )
    fig.update_layout(layout)

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

    # Apply dark theme layout
    layout = timeseries_layout.copy()
    layout.update(
        {
            "title": dict(
                text="PMI Services Regime",
                x=0.05,
                font=dict(size=14, family="Arial Black", color="#FFFFFF"),
            ),
            "yaxis": dict(
                title=dict(text="Regime Distribution", font=dict(color="#FFFFFF")),
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=True,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
            ),
            "yaxis2": dict(
                title=dict(text="ACWI 52W % Change", font=dict(color="#FFFFFF")),
                overlaying="y",
                side="right",
                tickformat=".0%",
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=False,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
            ),
            "barmode": "stack",
        }
    )
    fig.update_layout(layout)

    return fig
