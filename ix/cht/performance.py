from typing import Dict, List, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from ix.db.query import Series, MultiSeries
from .style import (
    apply_academic_style,
    add_zero_line,
    get_value_label,
    get_color,
    ANTIGRAVITY_PALETTE,
)


def _create_error_fig(msg: str) -> go.Figure:
    """Helper to create error figure."""
    fig = go.Figure()
    fig.add_annotation(text=msg, showarrow=False)
    return fig


def _create_performance_bar_chart(
    tickers: Dict[str, str], title: str, period_days: int, resample_freq: str = "B"
) -> go.Figure:
    """Helper to create sorted horizontal performance bar charts."""
    try:
        df = (
            MultiSeries(**{label: Series(ticker) for label, ticker in tickers.items()})
            .resample(resample_freq)
            .ffill()
            .pct_change(period_days)
            .mul(100)
            .iloc[-50:]  # Fetch adequate history
            .copy()
        ).dropna(axis=1, how="all")

        latest_date = df.index[-1]

        # Latest snapshot
        latest = df.iloc[-1].sort_values(ascending=True)

    except Exception as e:
        # Instead of failing silently or printing, we return an error chart or re-raise
        # Ideally we log, but for now let's return an empty chart with message
        fig = go.Figure()
        fig.add_annotation(text=f"Data error: {str(e)}", showarrow=False)
        return fig

    if df.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", showarrow=False)
        return fig

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    # Color logic: Emerald for > 0, Rose for < 0
    colors = ["#10b981" if x >= 0 else "#f43f5e" for x in latest.values]

    fig.add_trace(
        go.Bar(
            x=latest.values,
            y=latest.index,
            orientation="h",
            text=[f"{v:.1f}%" for v in latest.values],
            textposition="auto",
            textfont=dict(size=14, color="white" if is_dark else "black"),
            marker=dict(color=colors),
            hovertemplate="%{y}: %{x:.2f}%<extra></extra>",
        )
    )

    apply_academic_style(fig)
    is_dark = fig.layout.paper_bgcolor in ["#0d0f12", "black", "#000000"]
    font_color = "#e2e8f0" if is_dark else "#000000"
    as_of_color = "#94a3b8" if is_dark else "#475569"

    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",
            font=dict(size=22, color=font_color, family="Outfit"),
        ),
        xaxis=dict(
            title="Return (%)",
            title_font=dict(size=16, color=font_color, family="Outfit"),
            tickfont=dict(size=14, color=font_color),
        ),
        yaxis=dict(title="", tickfont=dict(size=14, color=font_color)),
        showlegend=False,
        hovermode="closest",
        margin=dict(t=100, l=160, r=40),  # Adjusted for longer labels
    )

    as_of_str = latest_date.strftime("%B %d, %Y")

    fig.add_annotation(
        text=f"As of {as_of_str}",
        xref="paper",
        yref="paper",
        x=1.0,
        y=1.05,
        showarrow=False,
        font=dict(size=14, color=as_of_color),
        xanchor="right",
        yanchor="bottom",
    )

    if not df.empty:
        fig.add_vline(
            x=0, line_width=1, line_color=font_color, opacity=0.3, layer="below"
        )

    return fig


def _create_multi_performance_bar_chart(
    tickers: Dict[str, str],
    title: str,
    periods: Dict[str, int],
    resample_freq: str = "B",
) -> go.Figure:
    """Helper to create grouped horizontal performance bar charts for multiple periods."""
    try:
        ms = MultiSeries(**{label: Series(ticker) for label, ticker in tickers.items()})
        df_base = ms.resample(resample_freq).ffill().copy()

        results = {}
        for period_label, days in periods.items():
            sdf = df_base.pct_change(days).mul(100).iloc[-1]
            results[period_label] = sdf

        df_perf = pd.DataFrame(results)
        if df_perf.empty:
            return _create_error_fig("No performance data calculated")

        # Sort by the 20D period for consistent ordering
        sort_col = "20D" if "20D" in df_perf.columns else list(periods.keys())[-1]
        df_perf = df_perf.sort_values(by=sort_col, ascending=True)

        latest_date = df_base.index[-1]

    except Exception as e:
        fig = go.Figure()
        fig.add_annotation(text=f"Data error: {str(e)}", showarrow=False)
        return fig

    if df_perf.empty:
        fig = go.Figure()
        fig.add_annotation(text="No data available", showarrow=False)
        return fig

    fig = go.Figure()

    # Distinct colors for periods
    # 20D (Cyan), 5D (Orange), 1D (Emerald)
    colors = {
        "20D": get_color("Sky", 0),
        "5D": get_color("Amber", 4),
        "1D": get_color("Emerald", 3),
    }

    for period_label in periods.keys():
        perf_values = df_perf[period_label]
        # Hide 1D and 5D by default, keep 20D visible
        visibility = True if period_label == "20D" else "legendonly"

        fig.add_trace(
            go.Bar(
                x=perf_values,
                y=df_perf.index,
                name=period_label,
                orientation="h",
                text=[f"{v:.1f}%" for v in perf_values],
                textposition="auto",
                textfont=dict(size=12, color="white" if is_dark else font_color),
                marker=dict(color=colors.get(period_label, "#94a3b8")),
                visible=visibility,
                hovertemplate=f"{period_label} - %{{y}}: %{{x:.2f}}%<extra></extra>",
            )
        )

    apply_academic_style(fig)
    is_dark = fig.layout.paper_bgcolor in ["#0d0f12", "black", "#000000"]
    font_color = "#e2e8f0" if is_dark else "#000000"
    as_of_color = "#94a3b8" if is_dark else "#475569"

    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",
            font=dict(size=22, color=font_color, family="Outfit"),
        ),
        xaxis=dict(
            title="Return (%)",
            title_font=dict(size=16, color=font_color, family="Outfit"),
            tickfont=dict(size=14, color=font_color),
        ),
        yaxis=dict(title="", tickfont=dict(size=14, color=font_color)),
        barmode="group",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255,255,255,0)",
            font=dict(size=14, color=font_color),
        ),
        hovermode="closest",
        margin=dict(t=100, l=160, r=40),
    )

    as_of_str = latest_date.strftime("%B %d, %Y")
    fig.add_annotation(
        text=f"As of {as_of_str}",
        xref="paper",
        yref="paper",
        x=0.0,
        y=1.05,
        showarrow=False,
        font=dict(size=14, color=as_of_color),
        xanchor="left",
        yanchor="bottom",
    )

    fig.add_vline(x=0, line_width=1, line_color=font_color, opacity=0.3, layer="below")

    return fig


def _create_performance_heatmap(
    tickers: Dict[str, str],
    title: str,
    periods: Dict[str, int],
    resample_freq: str = "B",
) -> go.Figure:
    """Helper to create a high-density performance heatmap 'Pulse View'."""
    try:
        ms = MultiSeries(**{label: Series(ticker) for label, ticker in tickers.items()})
        df_base = ms.resample(resample_freq).ffill().copy()

        results = {}
        for period_label, days in periods.items():
            sdf = df_base.pct_change(days).mul(100).iloc[-1]
            results[period_label] = sdf

        df_perf = pd.DataFrame(results)
        sort_col = list(periods.keys())[-1]
        df_perf = df_perf.sort_values(by=sort_col, ascending=True)
        latest_date = df_base.index[-1]
        as_of_str = latest_date.strftime("%B %d, %Y")

    except Exception as e:
        return _create_error_fig(f"Data error: {str(e)}")

    if df_perf.empty:
        return _create_error_fig("No data available")

    # Layout dimensions
    x_labels = list(periods.keys())
    y_labels = df_perf.index.tolist()
    z_values = df_perf.values

    # Value formatting for annotations
    text_values = [[f"{v:.1f}%" for v in row] for row in z_values]

    fig = go.Figure(
        data=go.Heatmap(
            z=z_values,
            x=x_labels,
            y=y_labels,
            zmid=0,
            text=text_values,
            texttemplate="%{text}",
            xgap=4,
            ygap=4,
            hovertemplate="Asset: %{y}<br>Period: %{x}<br>Return: %{z:.2f}%<extra></extra>",
        )
    )

    apply_academic_style(fig)

    # Theme detection
    is_dark = fig.layout.paper_bgcolor in ["#0d0f12", "black", "#000000"]
    font_color = "#e2e8f0" if is_dark else "#000000"
    neutral_bg = "#1e293b" if is_dark else "#f8fafc"
    text_color = "white" if is_dark else "black"

    fig.update_traces(
        colorscale=[
            [0, "#f43f5e"],  # Rose (Negative)
            [0.45, "#fda4af"],  # Light Rose
            [0.5, neutral_bg],  # Adaptive Neutral
            [0.55, "#6ee7b7"],  # Light Emerald
            [1, "#10b981"],  # Emerald (Positive)
        ],
        textfont={"size": 14, "family": "Inter, sans-serif", "color": text_color},
        colorbar=dict(
            title=dict(text="Return %", font=dict(size=12, color=font_color)),
            thickness=15,
            len=0.75,
            tickfont=dict(size=12, color=font_color),
        ),
    )

    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",
            font=dict(size=24, color=font_color),
            x=0.01,
            xanchor="left",
        ),
        xaxis=dict(
            title="",
            side="top",
            tickfont=dict(size=14, color=font_color, family="Outfit"),
            showgrid=False,
        ),
        yaxis=dict(
            title="",
            autorange="reversed",
            tickfont=dict(size=12, color=font_color, family="Inter"),
            showgrid=False,
        ),
        height=500,  # Standardized with other charts
        margin=dict(t=120, b=40, l=160, r=60),
    )

    fig.add_annotation(
        text=f"<b>Performance Pulse</b> | As of {as_of_str}",
        xref="paper",
        yref="paper",
        x=0.0,
        y=1.07,
        showarrow=False,
        font=dict(size=14, color="#94a3b8"),
        xanchor="left",
        yanchor="bottom",
    )

    return fig


def Performance_GlobalEquity() -> go.Figure:
    """Global Equity Market Performance Pulse (Heatmap)"""
    tickers = {
        "ACWI": "ACWI US EQUITY:PX_LAST",
        "US": "SPY US EQUITY:PX_LAST",
        "DM ex US": "IDEV US EQUITY:PX_LAST",
        "U.K.": "EWU US EQUITY:PX_LAST",
        "EAFE": "EFA US EQUITY:PX_LAST",
        "Europe": "FEZ US EQUITY:PX_LAST",
        "Germany": "EWG US EQUITY:PX_LAST",
        "Japan": "EWJ US EQUITY:PX_LAST",
        "Korea": "EWY US EQUITY:PX_LAST",
        "Australia": "EWA US EQUITY:PX_LAST",
        "Emerging": "VWO US EQUITY:PX_LAST",
        "China": "MCHI US EQUITY:PX_LAST",
        "India": "INDA US EQUITY:PX_LAST",
        "Brazil": "EWZ US EQUITY:PX_LAST",
        "Taiwan": "EWT US EQUITY:PX_LAST",
        "Vietnam": "VNM US EQUITY:PX_LAST",
    }
    return _create_performance_heatmap(
        tickers=tickers,
        title="Global Equity Performance Pulse",
        periods={"1D": 1, "5D": 5, "20D": 20, "60D": 60, "250D": 250},
        resample_freq="B",
    )


def Performance_UsSectors() -> go.Figure:
    """US Sector Performance Pulse (Heatmap)"""
    tickers = {
        "Tech": "XLK US EQUITY:PX_LAST",
        "Energy": "XLE US EQUITY:PX_LAST",
        "Health": "XLV US EQUITY:PX_LAST",
        "Financials": "XLF US EQUITY:PX_LAST",
        "Discretionary": "XLY US EQUITY:PX_LAST",
        "Staples": "XLP US EQUITY:PX_LAST",
        "Industrials": "XLI US EQUITY:PX_LAST",
        "Utilities": "XLU US EQUITY:PX_LAST",
        "Materials": "XLB US EQUITY:PX_LAST",
        "Real Estate": "XLRE US EQUITY:PX_LAST",
        "Comm Svcs": "XLC US EQUITY:PX_LAST",
        "S&P 500": "SPY US EQUITY:PX_LAST",
    }
    return _create_performance_heatmap(
        tickers=tickers,
        title="US Sector Performance Pulse",
        periods={"1D": 1, "5D": 5, "20D": 20, "60D": 60, "250D": 250},
        resample_freq="B",
    )


def Performance_KrSectors() -> go.Figure:
    """KR Sector Performance Pulse (Heatmap)"""
    tickers = {
        "KOSPI": "KOSPI INDEX:PX_LAST",
        "IT Service": "A046:PX_LAST",
        "Construction": "A018:PX_LAST",
        "Finance": "A021:PX_LAST",
        "Insurance": "A025:PX_LAST",
        "Securities": "A024:PX_LAST",
        "Real Estate": "A045:PX_LAST",
        "Ent & Culture": "A047:PX_LAST",
        "Transp & Storage": "A019:PX_LAST",
        "Distribution": "A016:PX_LAST",
        "Gen Services": "A026:PX_LAST",
        "Utils": "A017:PX_LAST",
        "Manufacturing": "A027:PX_LAST",
        "Metals": "A011:PX_LAST",
        "Machinery": "A012:PX_LAST",
        "Textile": "A006:PX_LAST",
        "Transp Equip": "A015:PX_LAST",
        "Food & Bev": "A005:PX_LAST",
        "Elec & Elec": "A013:PX_LAST",
        "Pharma": "A009:PX_LAST",
        "Chemicals": "A008:PX_LAST",
        "Telecom": "A020:PX_LAST",
    }
    return _create_performance_heatmap(
        tickers=tickers,
        title="KR Sector Performance Pulse",
        periods={"1D": 1, "5D": 5, "20D": 20, "60D": 60, "250D": 250},
        resample_freq="B",
    )
