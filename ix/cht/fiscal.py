import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from ix.db.query import Series, MultiSeries, Offset
from .style import apply_academic_style, add_zero_line, get_value_label


def USFederalDeficitYieldCurve() -> go.Figure:
    """US Federal Deficit vs Yield Curve"""
    try:
        deficit_series = (
            -Series("TRSMTSSURTOTFTD:PX_LAST", scale=1)
            .rolling(12)
            .mean()
            .mul(2)
            .div(
                Series("US.GDPN:PX_LAST", freq="ME", scale=10)
                .fillna(0)
                .rolling(12)
                .sum()
            )
            .mul(100)
            .resample("W-Fri")
            .last()
            .ffill()
        )

        yield_spread = Offset(
            (
                Series("TRYUS30Y:PX_YTM", freq="W-Fri")
                - Series("TRYUS10Y:PX_YTM", freq="W-Fri")
            ),
            days=7 * 26,
        ).mul(100)

        df = MultiSeries(
            **{
                "Deficit/GDP (%)": deficit_series,
                "30-10Y (bp)": yield_spread,
            }
        ).iloc[-500:]
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Deficit (Left)
    col_deficit = "Deficit/GDP (%)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col_deficit],
            name=get_value_label(df[col_deficit], "Deficit/GDP (%)", ".1f"),
            mode="lines",
            line=dict(width=3),
            hovertemplate="<b>Deficit/GDP (%)</b>: %{y:.2f}%<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=False,
    )

    # 2. Yield Spread (Right)
    col_spread = "30-10Y (bp)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col_spread],
            name=get_value_label(df[col_spread], "30-10Y Spread (bp, Lead 6M)", ".0f"),
            mode="lines",
            line=dict(width=3),
            hovertemplate="<b>30-10Y Spread</b>: %{y:.2f}bp<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=True,
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>Fiscal Deficit (GDP %) vs Yield Curve</b>"),
        yaxis=dict(title="Deficit / GDP (%)"),
        yaxis2=dict(title="Yield Spread (bp)", showgrid=False),
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        add_zero_line(fig)

    return fig


def UsGovNetOutlays_InterestPayments() -> go.Figure:
    """US Federal Net Interest Payments"""
    try:
        df = MultiSeries(
            **{
                "Net Interest ($Bn)": Series("USGV1032246:PX_LAST")
                .rolling(12)
                .sum()
                .div(1000),
                "YoY (%)": Series("USGV1032246:PX_LAST")
                .rolling(12)
                .sum()
                .pct_change(12)
                .mul(100),
            }
        ).iloc[-12 * 10 :]
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Trace 1: Net Interest (Left)
    col1 = "Net Interest ($Bn)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col1],
            name=get_value_label(df[col1], col1, ".1f"),
            line=dict(width=2.5),
            hovertemplate=f"<b>{col1}</b>: %{{y:.2f}}B<extra></extra>",
            connectgaps=True,
            fillcolor="rgba(255, 0, 184, 0.1)",
        ),
        secondary_y=False,
    )

    # Trace 2: YoY (Right)
    col2 = "YoY (%)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col2],
            name=get_value_label(df[col2], col2, ".1f"),
            line=dict(width=2.5),
            hovertemplate=f"<b>{col2}</b>: %{{y:.2f}}%<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=True,
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>US Federal Net Interest Payments</b>"),
        yaxis=dict(title="Net Interest (12M Sum, $Bn)"),
        yaxis2=dict(title="YoY Change (%)", showgrid=False),
    )

    if not df.empty:
        # Manually calculate padded end date instead of undefined pad_days
        end_date = df.index[-1] + pd.Timedelta(days=200)
        fig.update_xaxes(range=[df.index[0], end_date])
        add_zero_line(fig)

    return fig


def UsGovNetOutlays_NationalDefense() -> go.Figure:
    """US Federal National Defense"""
    try:
        df = MultiSeries(
            **{
                "National Defense ($Bn)": Series("USGV0941992:PX_LAST")
                .rolling(12)
                .sum()
                .div(1000),
                "YoY (%)": Series("USGV0941992:PX_LAST")
                .rolling(12)
                .sum()
                .pct_change(12)
                .mul(100),
            }
        ).iloc[-12 * 10 :]
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Trace 1: National Defense (Left)
    col1 = "National Defense ($Bn)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col1],
            name=get_value_label(df[col1], col1, ".1f"),
            line=dict(width=2.5),
            hovertemplate=f"<b>{col1}</b>: %{{y:.2f}}B<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=False,
    )

    # Trace 2: YoY (Right)
    col2 = "YoY (%)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col2],
            name=get_value_label(df[col2], col2, ".1f"),
            line=dict(width=2.5),
            hovertemplate=f"<b>{col2}</b>: %{{y:.2f}}%<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=True,
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>US Federal National Defense</b>"),
        yaxis=dict(title="National Defense (12M Sum, $Bn)"),
        yaxis2=dict(title="YoY Change (%)", showgrid=False),
    )

    if not df.empty:
        end_date = df.index[-1] + pd.Timedelta(days=200)
        fig.update_xaxes(range=[df.index[0], end_date])
        add_zero_line(fig)

    return fig


def UsGovNetOutlays_SocialCredit() -> go.Figure:
    """US Gov Outlays: Social & Credit"""
    try:
        df = (
            MultiSeries(
                **{
                    "Income Security": Series("USGV1032241:PX_LAST"),
                    "Commerce & Housing Credit": Series("USGV1032236:PX_LAST"),
                }
            )
            .div(1000)
            .rolling(12)
            .sum()
            .iloc[-12 * 10 :]
        )
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    for idx, col in enumerate(df.columns):

        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df[col],
                name=get_value_label(df[col], col, ".1f"),
                hovertemplate=f"<b>{col}</b>: %{{y:.2f}}B<extra></extra>",
            )
        )

    # Total Line
    total = df.sum(axis=1)
    fig.add_trace(
        go.Scatter(
            x=total.index,
            y=total,
            name=get_value_label(total, "Total Outlays", ".1f"),
            mode="lines",
            line=dict(color="black", width=2, dash="dot"),
            hovertemplate="<b>Total Outlays</b>: %{y:.2f}B<extra></extra>",
            connectgaps=True,
        )
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>US Gov Outlays: Social & Credit</b>"),
        yaxis=dict(title="Outlays (12M Sum, $Bn)"),
        barmode="relative",
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        add_zero_line(fig)

    return fig
