from typing import Dict, List, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from ix.db.query import Series, MultiSeries
from .style import apply_academic_style, add_zero_line, get_value_label


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

    # Color logic: Green for > 0, Red for < 0
    colors = ["#22c55e" if x >= 0 else "#ef4444" for x in latest.values]

    fig.add_trace(
        go.Bar(
            x=latest.values,
            y=latest.index,
            orientation="h",
            text=[f"{v:.2f}%" for v in latest.values],
            textposition="auto",
            marker=dict(color=colors),
            hovertemplate="<b>%{y}</b>: %{x:.2f}%<extra></extra>",
        )
    )

    apply_academic_style(fig)

    fig.update_layout(
        title=dict(text=f"<b>{title}</b>"),
        xaxis=dict(title="Return (%)"),
        yaxis=dict(title=""),
        showlegend=False,
        hovermode="closest",  # Override x unified for bar charts
    )

    as_of_str = latest_date.strftime("%B %d, %Y")

    fig.add_annotation(
        text=f"As of {as_of_str}",
        xref="paper",
        yref="paper",
        x=1.0,
        y=1.05,
        showarrow=False,
        font=dict(size=12, color="black"),
        xanchor="right",
        yanchor="bottom",
    )

    if not df.empty:
        fig.add_vline(x=0, line_width=1, line_color="black", opacity=0.3, layer="below")

    return fig


def Performance_GlobalEquity_1W() -> go.Figure:
    """Global Equity Market Weekly Performance (5 Days)"""
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
    return _create_performance_bar_chart(
        tickers=tickers,
        title="Global Equity Performance (Weekly % Change)",
        period_days=5,
        resample_freq="B",
    )


def Performance_GlobalEquity_1M() -> go.Figure:
    """Global Equity Market Monthly Performance (20 Days)"""
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
    return _create_performance_bar_chart(
        tickers=tickers,
        title="Global Equity Performance (Monthly % Change)",
        period_days=20,
        resample_freq="B",
    )


def Performance_USSectors_1W() -> go.Figure:
    """US Sector Weekly Performance (5 Days)"""
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
        "SPY": "SPY US EQUITY:PX_LAST",
    }
    return _create_performance_bar_chart(
        tickers=tickers,
        title="US Sector Performance (Weekly % Change)",
        period_days=5,
        resample_freq="B",
    )


def Performance_USSectors_1M() -> go.Figure:
    """US Sector Monthly Performance (20 Days)"""
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
        "SPY": "SPY US EQUITY:PX_LAST",
    }
    return _create_performance_bar_chart(
        tickers=tickers,
        title="US Sector Performance (Monthly % Change)",
        period_days=20,
        resample_freq="B",
    )
