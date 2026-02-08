import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from ix.db.query import Series, MultiSeries, Offset
from .style import apply_academic_style, add_zero_line, get_value_label


def US_CreditImpulse() -> go.Figure:
    """US Credit Impulse"""
    try:
        df = (
            MultiSeries(
                **{
                    "Bank Loans": Series("FRBBCABLBA@US:PX_LAST", scale=1)
                    .resample("W-Fri")
                    .last()
                    .ffill(),
                    "Commercial Paper": Series("USBC0311522:PX_LAST", scale=1)
                    .resample("W-Fri")
                    .last()
                    .ffill(),
                    "IG Corp": Series("MLC0AB:FACE_VAL", scale=1)
                    .resample("W-Fri")
                    .last()
                    .ffill(),
                    "HY Corp": Series("MLH0A0:FACE_VAL", scale=1)
                    .resample("W-Fri")
                    .last()
                    .ffill(),
                }
            )
            .ffill()
            .div(10**9)
            .diff(52)
            .diff(52)
            .iloc[-52 * 5 :]
        )
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    for idx, col in enumerate(df.columns):

        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df[col],
                name=get_value_label(df[col], col, ".2f"),
                hovertemplate=f"<b>{col}</b>: %{{y:.2f}}B<extra></extra>",
            )
        )

    # Total Line
    total = df.sum(axis=1)
    fig.add_trace(
        go.Scatter(
            x=total.index,
            y=total,
            name=get_value_label(total, "Total Impulse", ".2f"),
            mode="lines",
            line=dict(color="black", width=2, dash="dot"),
            hovertemplate="<b>Total Impulse</b>: %{y:.2f}B<extra></extra>",
            connectgaps=True,
        )
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>US Credit Impulse</b>"),
        yaxis_title="Impulse (Bn USD)",
        barmode="relative",
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        add_zero_line(fig)

    return fig


def US_CreditImpulseToGDP() -> go.Figure:
    """US Credit Impulse (% GDP)"""
    try:
        raw_impulse = (
            MultiSeries(
                **{
                    "Bank Loans": Series("FRBBCABLBA@US:PX_LAST", scale=1)
                    .resample("W-Fri")
                    .last()
                    .ffill(),
                    "Commercial Paper": Series("USBC0311522:PX_LAST", scale=1)
                    .resample("W-Fri")
                    .last()
                    .ffill(),
                    "IG Corp": Series("MLC0AB:FACE_VAL", scale=1)
                    .resample("W-Fri")
                    .last()
                    .ffill(),
                    "HY Corp": Series("MLH0A0:FACE_VAL", scale=1)
                    .resample("W-Fri")
                    .last()
                    .ffill(),
                }
            )
            .ffill()
            .div(10**9)
            .diff(52)
            .diff(52)
        )

        gdp = Series("US.GDPN:PX_LAST", freq="W-Fri", scale=10**9).ffill()
        gdp = gdp.reindex(raw_impulse.index).ffill()

        df = raw_impulse.div(gdp, axis=0).mul(100).iloc[-52 * 5 :]
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    # Bars
    for idx, col in enumerate(df.columns):

        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df[col],
                name=get_value_label(df[col], col, ".2f"),
                hovertemplate=f"<b>{col}</b>: %{{y:.2f}}%<extra></extra>",
            )
        )

    # Total Line
    total = df.sum(axis=1)
    fig.add_trace(
        go.Scatter(
            x=total.index,
            y=total,
            name=get_value_label(total, "Total Impulse", ".2f"),
            mode="lines",
            line=dict(color="black", width=2, dash="dot"),
            hovertemplate="<b>Total Impulse</b>: %{y:.2f}%<extra></extra>",
            connectgaps=True,
        )
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>US Credit Impulse (% GDP)</b>"),
        yaxis_title="Impulse (% GDP)",
        barmode="relative",
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        add_zero_line(fig)

    return fig


def BankCreditOutlook() -> go.Figure:
    """Bank Credit Outlook"""
    try:
        credit_yoy = Series("FRBBCABLBAYOY@US:PX_LAST").resample("W-Fri").ffill()
        standards = Series("USSU0486263:PX_LAST").resample("W-Fri").ffill()
        # Shift 12 months forward
        standards_lead = Offset(standards, days=52 * 7)

        df = MultiSeries(
            **{
                "Bank Credit YoY (%)": credit_yoy,
                "Bank Lending Standards (12M Lead)": standards_lead,
            }
        ).iloc[-52 * 10 :]
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Credit YoY (Left)
    col1 = "Bank Credit YoY (%)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col1],
            name=get_value_label(df[col1], col1, ".2f"),
            mode="lines",
            line=dict(width=2.5),
            hovertemplate=f"<b>{col1}</b>: %{{y:.2f}}%<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=False,
    )

    # 2. Lending Standards (Right)
    col2 = "Bank Lending Standards (12M Lead)"
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df[col2],
            name=get_value_label(df[col2], col2, ".2f"),
            mode="lines",
            line=dict(width=2.5),
            hovertemplate=f"<b>{col2}</b>: %{{y:.2f}}<extra></extra>",
            connectgaps=True,
        ),
        secondary_y=True,
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>Bank Credit Outlook</b>"),
        yaxis=dict(title="Credit Growth (%)"),
        yaxis2=dict(
            title="Standards (Net % Tightening)",
            autorange="reversed",
            showgrid=False,
        ),
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        add_zero_line(fig)

    return fig
