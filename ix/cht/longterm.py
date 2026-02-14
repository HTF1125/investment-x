import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from ix.db.query import Series, MultiSeries, Cycle
from ix.cht.style import apply_academic_style, add_zero_line, get_value_label


def _create_long_term_cycle_chart(
    ticker: str, title: str, cycle_weeks: int
) -> go.Figure:
    """Helper to create long term cycle charts"""
    try:
        px = Series(ticker).resample("W-Fri").ffill()
        yoy_10yma = px.pct_change(52).rolling(52 * 10).mean().mul(100)
        cycle = Cycle(yoy_10yma.iloc[-cycle_weeks:])

        data = MultiSeries(**{"PX": px, "YoY 10YMA (%)": yoy_10yma, "Cycle": cycle})
        data = data.dropna(how="all").ffill()
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. PX (Left)
    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data["PX"],
            name=f"PX ({px.iloc[-1]:,.2f})",
            legendgroup="PX",
            mode="lines",
            connectgaps=True,
            line_shape="spline",
            line=dict(width=2.6),
            hovertemplate="PX: %{y:,.2f}<extra></extra>",
        ),
        secondary_y=False,
    )

    # 2. YoY 10YMA (Right)
    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data["YoY 10YMA (%)"],
            name=f"YoY 10YMA ({yoy_10yma.iloc[-1]:.2f}%)",
            legendgroup="YoY 10YMA (%)",
            mode="lines",
            connectgaps=True,
            line_shape="spline",
            line=dict(width=2.2),
            hovertemplate="YoY 10YMA: %{y:.2f}%<extra></extra>",
        ),
        secondary_y=True,
    )

    # 3. Cycle (Right)
    fig.add_trace(
        go.Scatter(
            x=data.index,
            y=data["Cycle"],
            name=f"Cycle ({cycle.iloc[-1]:.2f})",
            legendgroup="Cycle",
            mode="lines",
            connectgaps=True,
            line_shape="spline",
            line=dict(width=2.4, dash="dot"),
            hovertemplate="Cycle: %{y:.2f}<extra></extra>",
        ),
        secondary_y=True,
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text=f"<b>{title}</b>"),
        yaxis=dict(title="PX (log)", type="log", tickformat=",.0f"),
        yaxis2=dict(title="YoY 10YMA (%) / Cycle", showgrid=False),
    )

    return fig


def LongTermCycles_Kospi() -> go.Figure:
    return _create_long_term_cycle_chart(
        "KOSPI INDEX:PX_LAST", "Long Term Cycles - Kospi", 52 * 20
    )


def LongTermCycles_SPX() -> go.Figure:
    return _create_long_term_cycle_chart(
        "SPX INDEX:PX_LAST", "Long Term Cycles - SPX", 52 * 60
    )


def LongTermCycles_GOLD() -> go.Figure:
    return _create_long_term_cycle_chart(
        "GOLD CURNCY:PX_LAST", "Long Term Cycles - GOLD", 52 * 20
    )


def LongTermCycles_SILVER() -> go.Figure:
    return _create_long_term_cycle_chart(
        "SLVR CURNCY:PX_LAST", "Long Term Cycles - SILVER", 52 * 20
    )


def LongTermCycles_CRUDE() -> go.Figure:
    return _create_long_term_cycle_chart(
        "WTI:PX_LAST", "Long Term Cycles - CRUDE", 52 * 20
    )


def LongTermCycles_DXY() -> go.Figure:
    return _create_long_term_cycle_chart(
        "DXY INDEX:PX_LAST", "Long Term Cycles - DXY", 52 * 20
    )


def LongTermCycles_NKY() -> go.Figure:
    return _create_long_term_cycle_chart(
        "NKY INDEX:PX_LAST", "Long Term Cycles - NIKKEI225", 52 * 20
    )


def LongTermCycles_CCMP() -> go.Figure:
    return _create_long_term_cycle_chart(
        "CCMP INDEX:PX_LAST", "Long Term Cycles - CCMP", 52 * 20
    )


def LongTermCycles_DAX() -> go.Figure:
    return _create_long_term_cycle_chart(
        "DAX INDEX:PX_LAST", "Long Term Cycles - DAX", 52 * 20
    )


def LongTermCycles_SHCOMP() -> go.Figure:
    return _create_long_term_cycle_chart(
        "SHCOMP INDEX:PX_LAST", "Long Term Cycles - SHCOMP", 52 * 20
    )
