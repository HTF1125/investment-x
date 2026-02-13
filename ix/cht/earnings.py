import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from ix.db.query import Series, MultiSeries
from .style import apply_academic_style, add_zero_line, get_value_label, get_color


def EarningsRevisionBreadth() -> go.Figure:
    """S&P 500 Earnings Revision Breadth"""
    try:

        def get_s(ticker):
            return Series(ticker, freq="B").ffill()

        # 1M Breadth
        up0_1m = get_s("SPX INDEX:FMA_COS_UP_EPS_FY0_1M")
        down0_1m = get_s("SPX INDEX:FMA_COS_DOWN_EPS_FY0_1M")
        up1_1m = get_s("SPX INDEX:FMA_COS_UP_EPS_FY1_1M")
        down1_1m = get_s("SPX INDEX:FMA_COS_DOWN_EPS_FY1_1M")
        net0_1m = (up0_1m - down0_1m) / (up0_1m + down0_1m)
        net1_1m = (up1_1m - down1_1m) / (up1_1m + down1_1m)
        breadth_1m = (net0_1m + net1_1m) / 2 * 100

        # 3M Breadth
        up0_3m = get_s("SPX INDEX:FMA_COS_UP_EPS_FY0_3M")
        down0_3m = get_s("SPX INDEX:FMA_COS_DOWN_EPS_FY0_3M")
        up1_3m = get_s("SPX INDEX:FMA_COS_UP_EPS_FY1_3M")
        down1_3m = get_s("SPX INDEX:FMA_COS_DOWN_EPS_FY1_3M")
        net0_3m = (up0_3m - down0_3m) / (up0_3m + down0_3m)
        net1_3m = (up1_3m - down1_3m) / (up1_3m + down1_3m)
        breadth_3m = (net0_3m + net1_3m) / 2 * 100

        # SPX YoY
        spx = get_s("SPX INDEX:PX_LAST")
        spx_yoy = spx.pct_change(52 * 5).mul(100)

        raw_df = MultiSeries(
            **{
                "S&P500 YoY (%)": spx_yoy,
                "Earnings ↑ Breadth (1M)": breadth_1m,
                "Earnings ↑ Breadth (3M)": breadth_3m,
            }
        )
        df = raw_df.rolling(50).mean().iloc[-2600:]
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # 1. Breadth (1M)
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Earnings ↑ Breadth (1M)"],
            name=get_value_label(df["Earnings ↑ Breadth (1M)"], "Breadth (1M)", ".1f"),
            mode="lines",
            line=dict(width=2.0),
            connectgaps=True,
        ),
        secondary_y=False,
    )

    # 2. Breadth (3M)
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["Earnings ↑ Breadth (3M)"],
            name=get_value_label(df["Earnings ↑ Breadth (3M)"], "Breadth (3M)", ".1f"),
            mode="lines",
            line=dict(width=2.5),
            connectgaps=True,
        ),
        secondary_y=False,
    )

    # 3. SPX YoY
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df["S&P500 YoY (%)"],
            name=get_value_label(df["S&P500 YoY (%)"], "S&P500 YoY (%)", ".1f"),
            mode="lines",
            line=dict(width=2.0),
            connectgaps=True,
        ),
        secondary_y=True,
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>S&P 500 Earnings Revision Breadth</b>"),
        yaxis=dict(title="Breadth Net % (Up - Down)"),
        yaxis2=dict(title="S&P500 YoY (%)", showgrid=False),
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        add_zero_line(fig)

    return fig


def EarningsGrowth_NTMA() -> go.Figure:
    """Earnings Growth (NTMA vs LTMA)"""
    try:
        df = MultiSeries(
            **{
                "S&P 500": (
                    Series("SPX INDEX:EPS_NTMA", freq="W-Fri")
                    / Series("SPX INDEX:EPS_LTMA", freq="W-Fri")
                    - 1
                )
                * 100,
                "NASDAQ": (
                    Series("CCMP INDEX:EPS_NTMA", freq="W-Fri").ffill()
                    / Series("CCMP INDEX:EPS_LTMA", freq="W-Fri").ffill()
                    - 1
                )
                * 100,
                "EUROSTOXX 600": (
                    Series("SXXP INDEX:EPS_NTMA", freq="W-Fri")
                    / Series("SXXP INDEX:EPS_LTMA", freq="W-Fri")
                    - 1
                )
                * 100,
            }
        ).iloc[-52 * 10 :]
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    for idx, col in enumerate(df.columns):

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df[col],
                name=get_value_label(df[col], col, ".1f"),
                mode="lines",
                line=dict(width=2.5),
                connectgaps=True,
            )
        )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>Earnings Growth (NTMA vs LTMA)</b>"),
        yaxis_title="Earnings Growth (%)",
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        add_zero_line(fig)

    return fig


def SPX_EqualWeight_SectorEarningsContribution() -> go.Figure:
    """S&P 500 Equal Weight Sector Earnings Growth Contribution (%)"""
    try:
        sectors = {
            "Telecomm": "S5TELS",
            "Industrials": "S5INDU",
            "Utilities": "S5UTIL",
            "Healthcare": "S5HLTH",
            "Energy": "S5ENRS",
            "Materials": "S5MATR",
            "IT": "S5INFT",
            "Financials": "S5FINL",
            "Discretionary": "S5COND",
            "Staples": "S5CONS",
        }

        sector_series = {}
        for name, ticker in sectors.items():
            ntma = Series(f"{ticker} INDEX:EPS_NTMA", freq="W-Fri").ffill()
            ltma = Series(f"{ticker} INDEX:EPS_LTMA", freq="W-Fri").ffill()
            # Growth: (NTMA/LTMA - 1) * 100
            growth = (ntma / ltma - 1) * 100
            # Clip and divide by N (10)
            sector_series[name] = growth.clip(lower=-30, upper=30) / 10

        df = MultiSeries(**sector_series).iloc[-52 * 5 :]
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    for idx, col in enumerate(df.columns):

        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df[col],
                name=get_value_label(df[col], col, ".2f"),
            )
        )

    # Total Line
    total = df.sum(axis=1)
    fig.add_trace(
        go.Scatter(
            x=total.index,
            y=total,
            name=get_value_label(total, "Total EW Growth", ".2f"),
            mode="lines",
            line=dict(color=get_color("Neutral"), width=2, dash="dot"),
            connectgaps=True,
        )
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>S&P 500 EW Sector Earnings Contribution</b>"),
        yaxis_title="Contribution to EW Growth (%)",
        barmode="relative",
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        add_zero_line(fig)

    return fig


def SPX_EqualWeight_SectorEarningsImpulse() -> go.Figure:
    """S&P 500 Equal Weight Sector Earnings Growth Impulse (%)"""
    try:
        sectors = {
            "Telecomm": "S5TELS",
            "Industrials": "S5INDU",
            "Utilities": "S5UTIL",
            "Healthcare": "S5HLTH",
            "Energy": "S5ENRS",
            "Materials": "S5MATR",
            "IT": "S5INFT",
            "Financials": "S5FINL",
            "Discretionary": "S5COND",
            "Staples": "S5CONS",
        }

        sector_series = {}
        for name, ticker in sectors.items():
            ntma = Series(f"{ticker} INDEX:EPS_NTMA", freq="W-Fri").ffill()
            ltma = Series(f"{ticker} INDEX:EPS_LTMA", freq="W-Fri").ffill()
            growth = (ntma / ltma - 1) * 100
            impulse = growth.diff(52)
            sector_series[name] = impulse.clip(lower=-30, upper=30) / 10

        df = MultiSeries(**sector_series).iloc[-52 * 1 :]
    except Exception as e:
        raise Exception(f"Data error: {str(e)}")

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    for idx, col in enumerate(df.columns):

        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df[col],
                name=get_value_label(df[col], col, ".2f"),
                hovertemplate=f"{col}: %{{y:.2f}}%<extra></extra>",
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
            line=dict(color=get_color("Neutral"), width=2, dash="dot"),
            connectgaps=True,
            hovertemplate=f"Total Impulse: %{{y:.2f}}%<extra></extra>",
        )
    )

    apply_academic_style(fig)
    fig.update_layout(
        title=dict(text="<b>S&P 500 EW Sector Earnings Impulse</b>"),
        yaxis_title="Impulse to EW Growth (%)",
        barmode="relative",
    )

    if not df.empty:
        fig.update_xaxes(range=[df.index[0], df.index[-1]])
        add_zero_line(fig)

    return fig
