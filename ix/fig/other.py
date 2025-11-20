import pandas as pd
import numpy as np
from pandas.tseries.offsets import MonthEnd
import plotly.graph_objects as go
from ix.misc import theme

from ix.db.query import (
    Series,
    StandardScalar,
    Offset,
    Cycle,
    D_MultiSeries,
    MonthEndOffset,
    M2,
    InvestorPositions,
    NumOfOECDLeadingPositiveMoM,
    NumOfPmiMfgPositiveMoM,
    NumOfPmiServicesPositiveMoM,
)
from .base import timeseries_layout


def credit_balance_deviation_from_6m_trend() -> go.Figure:

    # =GetSeries({"Consumer=Series('CRED_US:PX_LAST',freq='ME')-Series('CRED_US:PX_LAST',freq='ME').rolling(6).mean()","Business=Series('BUSLOANS',freq='ME')-Series('BUSLOANS',freq='ME').rolling(6).mean()"}, EOMONTH(AsOfDate, -60))

    fig = go.Figure()
    fig.update_layout(timeseries_layout)

    consumer = Series("CRED_US:PX_LAST", freq="ME")
    consumer_6m_trend = consumer.rolling(6).mean()
    consumer_deviation = consumer.div(consumer_6m_trend).dropna() - 1
    if not consumer_deviation.empty:
        fig.add_trace(
            go.Scatter(
                x=consumer_deviation.index,
                y=consumer_deviation.values,
                name=(f"Consumer({consumer_deviation.iloc[-1]:.2%})"),
                line=dict(color=theme.colors.blue[400], width=3),
                hovertemplate="<b>Consumer</b>: %{y:.2%}<extra></extra>",
                yaxis="y1",
            )
        )

    business = Series("BUSLOANS:PX_LAST", freq="ME")
    business_6m_trend = business.rolling(6).mean()
    business_deviation = business.div(business_6m_trend).dropna() - 1
    if not business_deviation.empty:
        fig.add_trace(
            go.Scatter(
                x=business_deviation.index,
                y=business_deviation.values,
                name=(f"Business ({business_deviation.iloc[-1]:.2%}) [R]"),
                line=dict(color=theme.colors.red[400], width=3),
                hovertemplate="<b>Business</b>: %{y:.2%}<extra></extra>",
                yaxis="y2",
            )
        )

    fig.update_layout(
        {
            "title": dict(
                text=f"Credit Balance Deviation from 6M Trend (US)",
            ),
            "yaxis": dict(
                # title=dict(text="Consumer"),
                tickformat=".0%",
            ),
            "yaxis2": dict(
                # title=dict(text="Business"),
                tickformat=".0%",
            ),
        }
    )

    return fig


def manufacturing_orders_us():
    # =GetSeries({"New Orders: Durable ex Aircraft=Series('CENANXANO').pct_change(12).mul(100)","US ISM Manufacturing=Series('ISMPMI_M:PX_LAST')"},EOMONTH(AsOfDate, -240))
    fig = go.Figure()
    fig.update_layout(timeseries_layout)

    ism = Series("ISMPMI_M:PX_LAST", freq="ME")

    if not ism.empty:
        fig.add_trace(
            go.Scatter(
                x=ism.index,
                y=ism.values,
                name=f"ISM Manufacturing ({ism.iloc[-1]:.2f}) [L]",
                line=dict(color=theme.colors.blue[400], width=3),
                hovertemplate="<b>ISM Manufacturing</b>: %{y:.2f}<extra></extra>",
            )
        )
    new_orders = Series("CENANXANO:PX_LAST").pct_change(12).mul(100)
    if not new_orders.empty:
        fig.add_trace(
            go.Scatter(
                x=new_orders.index,
                y=new_orders.values,
                name=f"New Orders: Durable ex Aircraft ({new_orders.iloc[-1]:.2f}) [R]",
                line=dict(color=theme.colors.red[400], width=3),
                hovertemplate="<b>New Orders: Durable ex Aircraft</b>: %{y:.2f}<extra></extra>",
                yaxis="y2",
            )
        )
    fig.update_layout(
        {
            "title": dict(
                text=f"Manufacturing Orders (US)",
            ),
            "yaxis": dict(
                tickformat=".0f",
                range=[30, 70],
            ),
            "yaxis2": dict(
                tickformat=".0f",
            ),
        }
    )

    return fig


def manufacturing_activity_us():

    fig = go.Figure()
    fig.update_layout(timeseries_layout)
    ism = Series("ISMPMI_M:PX_LAST", freq="ME")

    if not ism.empty:
        fig.add_trace(
            go.Scatter(
                x=ism.index,
                y=ism.values,
                name=f"ISM Manufacturing ({ism.iloc[-1]:.2f}) [L]",
                line=dict(color=theme.colors.blue[400], width=3),
                hovertemplate="<b>ISM Manufacturing</b>: %{y:.2f}<extra></extra>",
            )
        )
    dallas = Series("USSU0587918:PX_LAST", freq="ME")
    dallas = dallas.rolling(3).mean()
    if not dallas.empty:
        fig.add_trace(
            go.Scatter(
                x=dallas.index,
                y=dallas.values,
                name=f"Dallas 3MMA ({dallas.iloc[-1]:.2f}) [R]",
                line=dict(color=theme.colors.green[400], width=3),
                hovertemplate="<b>Dallas</b>: %{y:.2f}<extra></extra>",
                yaxis="y2",
            )
        )
    empire = Series("USSU0009518", freq="ME").rolling(3).mean()
    if not empire.empty:
        fig.add_trace(
            go.Scatter(
                x=empire.index,
                y=empire.values,
                name=f"Empire 3MMA ({empire.iloc[-1]:.2f}) [R]",
                line=dict(color=theme.colors.red[400], width=3),
                hovertemplate="<b>Empire</b>: %{y:.2f}<extra></extra>",
                yaxis="y2",
            )
        )

    fig.update_layout(
        {
            "title": dict(
                text=f"Manufacturing Activity (US)",
            ),
            "yaxis": dict(
                tickformat=".0f",
                range=[30, 70],
            ),
            "yaxis2": dict(
                tickformat=".0f",
            ),
        }
    )

    return fig


# from ix.db.query import MonthEndOffset  # Commented out - MongoDB not in use


def conference_board_leading_index():
    """
    Returns a Plotly Figure showing the YoY % change in the US Conference Board Leading and Lagging Indexes.
    Leading: USLEI:PX_LAST, Lagging: USLGI:PX_LAST (lagged 12 months).
    """
    fig = go.Figure()
    fig.update_layout(timeseries_layout)

    # Calculate 12-month % change for Leading Index
    leading = Series("USLEI:PX_LAST").pct_change(12).dropna()
    if not leading.empty:
        fig.add_trace(
            go.Scatter(
                x=leading.index,
                y=leading.values,
                name=f"Leading YoY ({leading.iloc[-1]:.2%}) [L]",
                yaxis="y1",
                line=dict(color=theme.colors.blue[400], width=3),
                hovertemplate="<b>Leading YoY</b>: %{y:.2%}%<extra></extra>",
            )
        )

    # Calculate 12-month % change for Lagging Index, then shift forward 12 months
    coincident = Series("US.COI").pct_change(12)
    if not coincident.empty:
        fig.add_trace(
            go.Scatter(
                x=coincident.index,
                y=coincident.values,
                name=f"Coincident YoY ({coincident.iloc[-1]:.2%}) [R]",
                hovertemplate="<b>Coincident YoY</b>: %{y:.2%}%<extra></extra>",
                yaxis="y2",
                line=dict(color=theme.colors.red[400], width=3),
            )
        )

    # Update layout: set title and y-axis formatting
    fig.update_layout(
        title=dict(
            text="Conference Board Leading Index",
        ),
        yaxis=dict(
            tickformat=".0%",
        ),
        yaxis2=dict(
            tickformat=".0%",
        ),
    )

    return fig


def financial_conditions_us():

    fci_us = pd.concat(
        [
            StandardScalar(-Series("DXY Index:PX_LAST", freq="W").ffill(), 52 * 3),
            StandardScalar(-Series("TRYUS10Y:PX_YTM", freq="W").ffill(), 52 * 3),
            StandardScalar(-Series("TRYUS30Y:PX_YTM", freq="W").ffill(), 52 * 3),
            StandardScalar(Series("SPX Index:PX_LAST", freq="W").ffill(), 52 * 3),
            StandardScalar(-Series("MORTGAGE30US:PX_LAST", freq="W").ffill(), 52 * 3),
            StandardScalar(-Series("CL1 Comdty:PX_LAST", freq="W").ffill(), 52 * 3),
            StandardScalar(-Series("BAMLC0A0CM:PX_LAST", freq="W").ffill(), 52 * 3),
        ],
        axis=1,
    )
    fci_us.index = pd.to_datetime(fci_us.index)
    fci_us = fci_us.sort_index()
    fci_us = fci_us.mean(axis=1).ewm(span=4 * 12).mean()
    fci = Offset(fci_us.resample("W").last().ffill().loc["2000":], months=6)
    cyc = Cycle(fci)
    ism = Series("ISMPMI_M:PX_LAST", freq="ME")

    latest_fci = fci.values[-1] if len(fci.values) > 0 else None
    latest_cyc = cyc.values[-1] if len(cyc.values) > 0 else None
    latest_ism = ism.values[-1] if len(ism.values) > 0 else None

    fig = go.Figure()
    if not fci.empty:
        fig.add_trace(
            go.Scatter(
                x=fci.index,
                y=fci.values,
                name=f"FCI 6M Lead ({latest_fci:.2%}) [L]",
                line=dict(color=theme.colors.blue[400], width=3),
                hovertemplate="<b>FCI</b>: %{y:.2%}<extra></extra>",
            )
        )
    if not cyc.empty:
        fig.add_trace(
            go.Scatter(
                x=cyc.index,
                y=cyc.values,
                name=f"Cycle ({latest_cyc:.2%}) [L]",
                line=dict(color=theme.colors.green[400], width=3, dash="dot"),
                hovertemplate="<b>Cycle</b>: %{y:.2%}<extra></extra>",
            )
        )

    if not ism.empty:
        fig.add_trace(
            go.Scatter(
                x=ism.index,
                y=ism.values,
                name=f"ISM PMI ({latest_ism:.1f}) [R]",
                yaxis="y2",
                line=dict(color=theme.colors.red[400], width=3),
                hovertemplate="<b>ISM PMI</b>: %{y:.1f}<extra></extra>",
            )
        )

    # Apply dark theme layout
    fig.update_layout(timeseries_layout)
    fig.update_layout(
        dict(
            title=dict(
                text=f"Financial Conditions (United States)",
            ),
            yaxis=dict(
                range=[-1, 1],
                tickformat=".0%",
            ),
            yaxis2=dict(
                range=[30, 70],
                tickformat=".0f",
            ),
        )
    )

    fig.add_hline(
        y=50,
        line_dash="dash",
        line_color=theme.colors.text_muted,
        line_width=3,
        annotation_text="Expansion/Contraction",
        annotation_position="top right",
        annotation_font_size=10,
        annotation_font_color=theme.colors.text_muted,
        yref="y2",
    )
    return fig


# from ix.db.query import M2  # Commented out - MongoDB not in use


def global_liquidity_cycle():
    def _normalize_percent(s):
        s = s.astype(float)
        return s / 100.0 if s.dropna().abs().median() > 1.5 else s

    gl = Offset(M2("ME").WorldTotal.pct_change(12), months=9)
    gl = _normalize_percent(gl)
    # Remove infinities and NaNs before cycle fitting
    gl = gl.replace([np.inf, -np.inf], np.nan).dropna()
    cyc = Cycle(gl, 60)
    ism = Series("ISMPMI_M:PX_LAST", freq="ME")

    latest_gl = gl.values[-1] if len(gl.values) > 0 else None
    latest_cyc = cyc.values[-1] if len(cyc.values) > 0 else None
    latest_ism = ism.values[-1] if len(ism.values) > 0 else None

    fig = go.Figure()
    if not gl.empty:
        fig.add_trace(
            go.Scatter(
                x=gl.index,
                y=gl.values,
                name=f"Global Liquidity 9M Lead ({latest_gl:.2%}) [L]",
                line=dict(color=theme.colors.blue[400], width=3),
                hovertemplate="<b>Global Liquidity YoY</b>: %{y:.2%}<extra></extra>",
            )
        )
    if not cyc.empty:
        fig.add_trace(
            go.Scatter(
                x=cyc.index,
                y=cyc.values,
                name=f"Cycle ({latest_cyc:.2%}) [L]",
                line=dict(color=theme.colors.green[400], width=3, dash="dot"),
                hovertemplate="<b>Cycle</b>: %{y:.2%}<extra></extra>",
            )
        )
    if not ism.empty:
        fig.add_trace(
            go.Scatter(
                x=ism.index,
                y=ism.values,
                name=f"ISM PMI ({latest_ism:.1f}) [R]",
                yaxis="y2",
                line=dict(color=theme.colors.red[400], width=3),
                hovertemplate="<b>ISM PMI</b>: %{y:.1f}<extra></extra>",
            )
        )

    # Apply dark theme layout
    fig.update_layout(timeseries_layout)
    fig.update_layout(
        dict(
            title=dict(
                text=f"Global Liquidity Cycle (M2)",
            ),
            yaxis=dict(
                range=[-0.05, 0.2],
                tickformat=".0%",
            ),
            yaxis2=dict(
                range=[30, 70],
                tickformat=".0f",
            ),
        )
    )
    fig.add_hline(
        y=50,
        line_dash="dash",
        line_color=theme.colors.text_muted,
        line_width=3,
        annotation_text="Expansion/Contraction",
        annotation_position="top right",
        annotation_font_size=10,
        annotation_font_color=theme.colors.text_muted,
        yref="y2",
    )
    return fig


def global_liquidity_growth_contributions():
    def _normalize_percent(s):
        s = s.astype(float)
        return s / 100.0 if s.dropna().abs().median() > 1.5 else s

    m2 = M2("ME")
    total = _normalize_percent(m2.WorldTotal.pct_change(12))
    contrib = {k: _normalize_percent(v) for k, v in m2.WorldContribution.items()}
    latest_total = total.iloc[-1] if len(total) > 0 else None

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=total.index,
            y=total.values,
            name=f"Total ({latest_total:.2%})" if latest_total is not None else "Total",
            mode="lines",
            line=dict(color=theme.colors.blue[400], width=3),
            hovertemplate="<b>Total</b>: %{y:.2%}<extra></extra>",
        )
    )

    for i, (name, s) in enumerate(contrib.items()):
        if s is None or len(s) == 0:
            continue
        fig.add_trace(
            go.Bar(
                x=s.index,
                y=s.values,
                name=name,
                hovertemplate=f"<b>{name}</b>: %{{y:.2%}}<extra></extra>",
            )
        )

    fig.update_layout(timeseries_layout)
    fig.update_layout(
        dict(
            title=dict(
                text="Global M2 Growth Contributions",
            ),
            yaxis=dict(
                range=[-0.05, 0.2],
                tickformat=".0%",
            ),
            yaxis2=dict(
                range=[30, 70],
                tickformat=".0f",
            ),
            barmode="relative",
        )
    )
    return fig


def global_liquidity_growth_by_central_banks():
    def _normalize_percent(s):
        s = s.astype(float)
        return s / 100.0 if s.dropna().abs().median() > 1.5 else s

    m2q = M2()
    world_df = m2q.World
    yoy = world_df.pct_change(12).apply(_normalize_percent)

    fig = go.Figure()

    for i, col in enumerate(yoy.columns):
        s = yoy[col].dropna()
        if s.empty:
            continue
        latest = s.iloc[-1]
        fig.add_trace(
            go.Scatter(
                x=s.index,
                y=s.values,
                name=f"{col} ({latest:.2%})",
                mode="lines",
                hovertemplate=f"<b>{col} YoY</b>: %{{y:.2%}}<extra></extra>",
            )
        )

    # Apply dark theme layout
    fig.update_layout(timeseries_layout)
    fig.update_layout(
        dict(
            title=dict(
                text=f"Global Liquidity Growth by Central Banks(M2)",
            ),
            yaxis=dict(
                range=[-0.2, 0.4],
                tickformat=".0%",
            ),
        )
    )
    return fig


# from ix.db.query import Series  # Commented out - MongoDB not in use
import pandas as pd
import plotly.graph_objects as go


def credit_impulse_us():
    data = pd.DataFrame(
        {
            "BACROUTP": Series("US.BACROUTP:PX_LAST", freq="ME"),
            "FRBBCABLCCBA@US": Series("FRBBCABLCCBA@US:PX_LAST", freq="ME"),
            "FRBBCABLCRCBA@US": Series("FRBBCABLCRCBA@US:PX_LAST", freq="ME"),
            "GDPN": Series("US.GDPN:PX_LAST"),
        }
    )
    data.ffill(inplace=True)
    ff = data["BACROUTP"].add(data["FRBBCABLCCBA@US"]).add(data["FRBBCABLCRCBA@US"])
    gg = data["GDPN"]
    return ff.diff().rolling(12).sum().diff(12) / gg


def credit_impulse_cn():
    data = pd.DataFrame(
        {
            "CN": Series("CNBC2252509:PX_LAST", freq="ME"),
            "GDPN": Series("CN.GDPNNSA:PX_LAST", freq="ME"),
        }
    )
    data.ffill(inplace=True)
    return data["CN"].rolling(12).sum().diff(12) / data["GDPN"]


def credit_impulse_us_vs_cn():
    ci_us = credit_impulse_us().dropna()
    ci_cn = credit_impulse_cn().dropna()

    # Get latest values for legend
    latest_us_val = ci_us.iloc[-1] if not ci_us.empty else float("nan")
    latest_cn_val = ci_cn.iloc[-1] if not ci_cn.empty else float("nan")

    us_legend = f"US Credit Impulse ({latest_us_val:.2%})"
    cn_legend = f"China Credit Impulse ({latest_cn_val:.2%})"

    fig = go.Figure()

    # US Credit Impulse on primary y-axis
    fig.add_trace(
        go.Scatter(
            x=ci_us.index,
            y=ci_us,
            mode="lines",
            name=f"US Credit Impulse ({latest_us_val:.2%})",
            line=dict(width=3, color=theme.colors.blue[400]),
            yaxis="y1",
            hovertemplate="US Credit Impulse: %{y:.2%}<extra></extra>",
        )
    )
    # China Credit Impulse on secondary y-axis
    fig.add_trace(
        go.Scatter(
            x=ci_cn.index,
            y=ci_cn,
            mode="lines",
            name=cn_legend,
            line=dict(width=3, color=theme.colors.red[400]),
            yaxis="y2",
            hovertemplate="China Credit Impulse: %{y:.2%}<extra></extra>",
        )
    )

    fig.update_layout(timeseries_layout)
    fig.update_layout(
        dict(
            title=dict(
                text="Credit Impulse US vs CN",
            ),
            yaxis=dict(
                tickformat=".0%",
            ),
            yaxis2=dict(
                tickformat=".0%",
            ),
        )
    )
    return fig


# from ix.db.query import InvestorPositions  # Commented out - MongoDB not in use
import plotly.graph_objects as go


def investor_positions():

    investor_positions = InvestorPositions().div(100)

    # Create a new plotly figure and add traces from investor_positions data
    fig = go.Figure()

    for name, series in investor_positions.items():
        fig.add_trace(
            go.Scatter(x=series.index, y=series.values, mode="lines", name=name)
        )

    fig.update_layout(timeseries_layout)
    fig.update_layout(
        dict(
            title=dict(
                text="Investor Positions",
            ),
            yaxis=dict(
                tickformat=".0%",
            ),
        )
    )
    return fig


# from ix.db import Series  # Commented out - MongoDB not in use
import plotly.graph_objects as go
import pandas as pd


def get_fed_net_liquidity_series() -> pd.Series:
    """
    Calculate the Fed Net Liquidity in trillions USD.
    Net Liquidity = Fed Assets - Treasury General Account - Reverse Repo
    All series are resampled to weekly (Wednesday) and forward-filled.
    """
    # Fetch data
    asset_mil = Series("WALCL")  # Fed assets, millions USD
    treasury_bil = Series("WTREGEN")  # Treasury General Account, billions USD
    repo_bil = Series("RRPONTSYD")  # Reverse Repo, billions USD

    # Convert to trillions
    asset = asset_mil / 1_000_000
    treasury = treasury_bil / 1_000
    repo = repo_bil / 1_000

    # Combine and resample
    df = pd.concat({"Fed Assets": asset, "TGA": treasury, "RRP": repo}, axis=1)
    weekly = df.resample("W-WED").last().ffill()

    # Calculate net liquidity
    weekly["Net Liquidity (T)"] = weekly["Fed Assets"] - weekly["TGA"] - weekly["RRP"]
    return weekly["Net Liquidity (T)"].dropna()


def fed_net_liquidity_vs_sp500():
    """
    Plot Fed Net Liquidity YoY % vs S&P 500 YoY %.
    """
    # Calculate YoY changes
    net_liquidity = get_fed_net_liquidity_series().pct_change(52).dropna()
    sp500 = Series("SPX Index:PX_LAST", freq="W").pct_change(52).dropna()

    # Get latest values for legend
    latest_liquidity = net_liquidity.iloc[-1] if not net_liquidity.empty else None
    latest_sp500 = sp500.iloc[-1] if not sp500.empty else None

    fig = go.Figure()

    # Fed Net Liquidity trace
    fig.add_trace(
        go.Scatter(
            x=net_liquidity.index,
            y=net_liquidity.values,
            name=(
                f"Fed Net Liquidity YoY ({latest_liquidity:.2%})"
                if latest_liquidity is not None
                else "Fed Net Liquidity YoY"
            ),
            line=dict(color=theme.colors.blue[400], width=3),
            hovertemplate="<b>Fed Net Liquidity YoY</b>: %{y:.2%}<extra></extra>",
        )
    )

    # S&P 500 trace
    fig.add_trace(
        go.Scatter(
            x=sp500.index,
            y=sp500.values,
            name=(
                f"S&P 500 YoY ({latest_sp500:.2%})"
                if latest_sp500 is not None
                else "S&P 500 YoY"
            ),
            yaxis="y1",
            line=dict(color=theme.colors.red[400], width=3),
            hovertemplate="<b>S&P 500 YoY</b>: %{y:.2%}<extra></extra>",
        )
    )

    fig.update_layout(timeseries_layout)
    fig.update_layout(
        dict(
            title=dict(
                text="Fed Net Liquidity vs S&P 500",
            ),
            yaxis=dict(
                tickformat=".0%",
                range=[-0.4, 0.4],
            ),
        )
    )
    return fig


import pandas as pd

# from ix.db.query import MultiSeries  # Commented out - MongoDB not in use


class AiCapex:

    def FE_CAPEX_NTMA(self) -> pd.DataFrame:
        return (
            D_MultiSeries(
                "Nvdia=NVDA,Google=GOOG,Microsoft=MSFT,Amazon=AMZN,Meta=META",
                field="FE_CAPEX_NTMA",
                freq="B",
            )
            .ffill()
            .dropna()
        )

    def FE_CAPEX_LTMA(self) -> pd.DataFrame:
        return (
            D_MultiSeries(
                "Nvdia=NVDA,Google=GOOG,Microsoft=MSFT,Amazon=AMZN,Meta=META",
                field="FE_CAPEX_LTMA",
                freq="B",
            )
            .ffill()
            .dropna()
        )

    def FE_CAPEX_Q(self) -> pd.DataFrame:
        return (
            D_MultiSeries(
                "Nvdia=NVDA,Google=GOOG,Microsoft=MSFT,Amazon=AMZN,Meta=META",
                field="FE_CAPEX_Q",
                freq="B",
            )
            .ffill()
            .dropna()
        )

    def FE_CAPEX_QOQ(self) -> pd.DataFrame:
        return self.FE_CAPEX_Q().dropna().resample("W-Fri").last().pct_change(52)

    def FE_CAPEX_YOY(self) -> pd.DataFrame:
        return (
            self.FE_CAPEX_NTMA().dropna().resample("W-Fri").last().ffill()
            / self.FE_CAPEX_LTMA().dropna().resample("W-Fri").last().ffill()
        ) - 1

    def TOTAL_FE_CAPEX_QOQ(self) -> pd.DataFrame:
        return (
            self.FE_CAPEX_Q()
            .sum(axis=1)
            .dropna()
            .resample("W-Fri")
            .last()
            .pct_change(52)
        )

    def TOTAL_FE_CAPEX_YOY(self) -> pd.DataFrame:
        ntma = self.FE_CAPEX_NTMA().sum(axis=1).dropna().resample("W-Fri").last()
        ltma = self.FE_CAPEX_LTMA().sum(axis=1).dropna().resample("W-Fri").last()
        return (ntma / ltma - 1).dropna()


import plotly.graph_objects as go
from ix.misc import theme


def ai_capex_quarter_yoy():

    data = AiCapex().FE_CAPEX_QOQ().dropna(how="all")
    total = AiCapex().TOTAL_FE_CAPEX_QOQ().dropna(how="all")
    latest_total = total.iloc[-1] if len(total) > 0 else None

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=total.index,
            y=total.values,
            name=f"Total ({latest_total:.2%})" if latest_total is not None else "Total",
            mode="lines",
            line=dict(color=theme.colors.blue[400], width=3),
            hovertemplate="<b>Total</b>: %{y:.2%}<extra></extra>",
        )
    )

    for i, (name, s) in enumerate(data.items()):
        if s is None or len(s) == 0:
            continue
        fig.add_trace(
            go.Scatter(
                x=s.index,
                y=s.values,
                name=name,
                mode="lines",
                line=dict(width=3),
                hovertemplate=f"<b>{name}</b>: %{{y:.2%}}<extra></extra>",
            )
        )
    fig.update_layout(timeseries_layout)
    fig.update_layout(
        dict(
            title=dict(
                text=f"AI Capex Quarterly YoY",
            ),
            yaxis=dict(
                tickformat=".0%",
            ),
        )
    )
    return fig


def ai_capex_yearly_yoy():

    data = AiCapex().FE_CAPEX_YOY().dropna(how="all")
    total = AiCapex().TOTAL_FE_CAPEX_YOY().dropna(how="all")
    latest_total = total.iloc[-1] if len(total) > 0 else None

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=total.index,
            y=total.values,
            name=f"Total ({latest_total:.2%})" if latest_total is not None else "Total",
            mode="lines",
            line=dict(color=theme.colors.blue[400], width=3),
            hovertemplate="<b>Total</b>: %{y:.2%}<extra></extra>",
        )
    )

    for i, (name, s) in enumerate(data.items()):
        if s is None or len(s) == 0:
            continue
        fig.add_trace(
            go.Scatter(
                x=s.index,
                y=s.values,
                name=name,
                mode="lines",
                line=dict(width=3),
                hovertemplate=f"<b>{name}</b>: %{{y:.2%}}<extra></extra>",
            )
        )
    fig.update_layout(timeseries_layout)
    fig.update_layout(
        dict(
            title=dict(
                text=f"AI Capex Yearly YoY",
            ),
            yaxis=dict(
                tickformat=".0%",
            ),
        )
    )
    return fig


def us_cesi_and_dollar():

    fig = go.Figure()
    fig.update_layout(timeseries_layout)
    cesi = Series("USFXCESIUSD:PX_LAST", freq="W-Fri")
    dxy = Series("DXY Index:PX_LAST", freq="W-Fri")
    if not cesi.empty:
        fig.add_trace(
            go.Scatter(
                x=cesi.index,
                y=cesi.values,
                name=f"CESI(US) ({cesi.iloc[-1]:.2f}) [L]",
                line=dict(color=theme.colors.blue[400], width=3),
                hovertemplate="<b>CESI(US)</b>: %{y:.2f}<extra></extra>",
            )
        )

    dxy_deviation = Offset(dxy.rolling(52).mean() - dxy, days=70)
    if not dxy_deviation.empty:
        fig.add_trace(
            go.Scatter(
                x=dxy_deviation.index,
                y=dxy_deviation.values,
                name=f"DXY deviation from Trend (70D Lead) ({dxy_deviation.iloc[-1]:.2f}) [R]",
                line=dict(color=theme.colors.red[400], width=3),
                hovertemplate="<b>DXY deviation from Trend (70D Lead)</b>: %{y:.2f}<extra></extra>",
                yaxis="y2",
            )
        )
    fig.update_layout(
        {
            "title": dict(
                text=f"Dollar & Economic Surprises",
            ),
            "yaxis": dict(
                tickformat=".0f",
                range=[-100, 100],
            ),
            "yaxis2": dict(
                tickformat=".1f",
                range=[-10, 10],
            ),
        }
    )
    return fig


def us_cesi_and_ust10y():

    fig = go.Figure()
    fig.update_layout(timeseries_layout)
    cesi = Series("USFXCESIUSD:PX_LAST", freq="W-Fri")
    ust10y = Series("TRYUS10Y:PX_YTM", freq="W-Fri")
    if not cesi.empty:
        fig.add_trace(
            go.Scatter(
                x=cesi.index,
                y=cesi.values,
                name=f"CESI(US) ({cesi.iloc[-1]:.2f}) [L]",
                line=dict(color=theme.colors.blue[400], width=3),
                hovertemplate="<b>CESI(US)</b>: %{y:.2f}<extra></extra>",
            )
        )

    ust10y_deviation = Offset(ust10y.rolling(52).mean() - ust10y, days=70)
    if not ust10y_deviation.empty:
        fig.add_trace(
            go.Scatter(
                x=ust10y_deviation.index,
                y=ust10y_deviation.values,
                name=f"UST10Y deviation from Trend (70D Lead) ({ust10y_deviation.iloc[-1]:.2f}) [R]",
                line=dict(color=theme.colors.red[400], width=3),
                hovertemplate="<b>UST10Y deviation from Trend (70D Lead)</b>: %{y:.2f}<extra></extra>",
                yaxis="y2",
            )
        )
    fig.update_layout(
        {
            "title": dict(
                text=f"UST10Y & Economic Surprises",
            ),
            "yaxis": dict(
                tickformat=".0f",
                range=[-100, 100],
            ),
            "yaxis2": dict(
                tickformat=".2f",
                range=[-1, 1],
            ),
        }
    )
    return fig


def manufacturing_activity_us_and_dollar() -> go.Figure:

    # =GetSeries({"Dallas Fed Business Activity=Series('USSU0587918:PX_LAST')","Dollar deviation from LT Trend (4M Lead)=MonthEndOffset(Series('DXY Index:PX_LAST', freq='ME')-MovingAverage(Series('DXY Index:PX_LAST',freq='ME'), 24), 3)"}, EOMONTH(AsOfDate,-240))
    fig = go.Figure()
    fig.update_layout(timeseries_layout)
    dallas = Series("USSU0587918:PX_LAST", freq="ME")
    dallas = dallas.rolling(3).mean()
    if not dallas.empty:
        fig.add_trace(
            go.Scatter(
                x=dallas.index,
                y=dallas.values,
                name=f"Dallas 3MMA ({dallas.iloc[-1]:.2f}) [R]",
                line=dict(color=theme.colors.blue[400], width=3),
                hovertemplate="<b>Dallas</b>: %{y:.2f}<extra></extra>",
                yaxis="y1",
            )
        )
    dxy_deviation = MonthEndOffset(
        Series("DXY Index:PX_LAST", freq="ME").rolling(24).mean()
        - Series("DXY Index:PX_LAST", freq="ME"),
        3,
    )
    if not dxy_deviation.empty:
        fig.add_trace(
            go.Scatter(
                x=dxy_deviation.index,
                y=dxy_deviation.values,
                name=f"DXY deviation from LT Trend (4M Lead) ({dxy_deviation.iloc[-1]:.2f}) [R]",
                line=dict(color=theme.colors.red[400], width=3),
                hovertemplate="<b>DXY deviation from LT Trend (4M Lead)</b>: %{y:.2f}<extra></extra>",
                yaxis="y2",
            )
        )
    fig.update_layout(
        {
            "title": dict(
                text=f"Manufacturing Activity (US)",
            ),
            "yaxis": dict(
                tickformat=".0f",
            ),
            "yaxis2": dict(
                tickformat=".0f",
                range=[-10, 10],
            ),
        }
    )
    return fig


# from ix.db.query import NumOfOECDLeadingPositiveMoM  # Commented out - MongoDB not in use


def oecd_diffusion_index() -> go.Figure:
    fig = go.Figure()
    fig.update_layout(timeseries_layout)
    # Ensure pandas Series and clean values to avoid NumPy concat issues
    _raw_cli = NumOfOECDLeadingPositiveMoM()
    _cli = _raw_cli if isinstance(_raw_cli, pd.Series) else pd.Series(_raw_cli)
    _cli = pd.to_numeric(_cli, errors="coerce").dropna()
    oecd_cli_diffusion = MonthEndOffset(_cli, 1)
    if not oecd_cli_diffusion.empty:
        fig.add_trace(
            go.Scatter(
                x=oecd_cli_diffusion.index,
                y=oecd_cli_diffusion.values,
                name=f"OECD CLI MoM Diffusion ({oecd_cli_diffusion.iloc[-1]:.2f}) [L]",
                line=dict(color=theme.colors.blue[400], width=3),
                hovertemplate="<b>OECD CLI MoM Diffusion</b>: %{y:.2f}<extra></extra>",
            )
        )
    msci_world = (
        Series("990100:FG_TOTAL_RET_IDX", freq="W").ffill().pct_change(52)
    ).dropna()
    if not msci_world.empty:
        fig.add_trace(
            go.Scatter(
                x=msci_world.index,
                y=msci_world.values,
                name=f"MSCI World YoY({msci_world.iloc[-1]:.2%}) [R]",
                line=dict(color=theme.colors.red[400], width=3),
                hovertemplate="<b>MSCI World YoY</b>: %{y:.2%}<extra></extra>",
                yaxis="y2",
            )
        )
    fig.update_layout(
        {
            "title": dict(
                text=f"OECD CLI MoM Diffusion & MSCI World",
            ),
            "yaxis": dict(
                tickformat=".0f",
                range=[0, 100],
            ),
            "yaxis2": dict(
                tickformat=".0%",
                range=[-0.3, 0.5],
            ),
        }
    )
    return fig


# from ix.db.query import NumOfPmiMfgPositiveMoM  # Commented out - MongoDB not in use


def pmi_manufacturing_diffusion_index() -> go.Figure:
    fig = go.Figure()
    fig.update_layout(timeseries_layout)
    oecd_cli_diffusion = NumOfPmiMfgPositiveMoM().rolling(3).mean()
    if not oecd_cli_diffusion.empty:
        fig.add_trace(
            go.Scatter(
                x=oecd_cli_diffusion.index,
                y=oecd_cli_diffusion.values,
                name=f"OECD CLI MoM Diffusion ({oecd_cli_diffusion.iloc[-1]:.2f}) [L]",
                line=dict(color=theme.colors.blue[400], width=3),
                hovertemplate="<b>OECD CLI MoM Diffusion</b>: %{y:.2f}<extra></extra>",
            )
        )
    msci_world = (
        Series("990100:FG_TOTAL_RET_IDX", freq="W").ffill().pct_change(52)
    ).dropna()
    if not msci_world.empty:
        fig.add_trace(
            go.Scatter(
                x=msci_world.index,
                y=msci_world.values,
                name=f"MSCI World ({msci_world.iloc[-1]:.2%}) [R]",
                line=dict(color=theme.colors.red[400], width=3),
                hovertemplate="<b>MSCI World YoY</b>: %{y:.2%}<extra></extra>",
                yaxis="y2",
            )
        )
    fig.update_layout(
        {
            "title": dict(
                text=f"PMI ManufacturingMoM Diffusion & MSCI World",
            ),
            "yaxis": dict(
                tickformat=".0f",
                range=[0, 100],
            ),
            "yaxis2": dict(
                tickformat=".0%",
                range=[-0.3, 0.5],
            ),
        }
    )
    return fig


# from ix.db.query import NumOfPmiServicesPositiveMoM  # Commented out - MongoDB not in use


def pmi_services_diffusion_index() -> go.Figure:
    fig = go.Figure()
    fig.update_layout(timeseries_layout)
    oecd_cli_diffusion = NumOfPmiServicesPositiveMoM().ffill().rolling(3).mean()
    if not oecd_cli_diffusion.empty:
        fig.add_trace(
            go.Scatter(
                x=oecd_cli_diffusion.index,
                y=oecd_cli_diffusion.values,
                name=f"OECD CLI MoM Diffusion ({oecd_cli_diffusion.iloc[-1]:.2f}) [L]",
                line=dict(color=theme.colors.blue[400], width=3),
                hovertemplate="<b>OECD CLI MoM Diffusion</b>: %{y:.2f}<extra></extra>",
            )
        )
    msci_world = (
        Series("990100:FG_TOTAL_RET_IDX", freq="W").ffill().pct_change(52)
    ).dropna()
    if not msci_world.empty:
        fig.add_trace(
            go.Scatter(
                x=msci_world.index,
                y=msci_world.values,
                name=f"MSCI World YoY({msci_world.iloc[-1]:.2%}) [R]",
                line=dict(color=theme.colors.red[400], width=3),
                hovertemplate="<b>MSCI World YoY</b>: %{y:.2%}<extra></extra>",
                yaxis="y2",
            )
        )
    fig.update_layout(
        {
            "title": dict(
                text=f"PMI Services MoM Diffusion & MSCI World",
            ),
            "yaxis": dict(
                tickformat=".0f",
                range=[0, 100],
            ),
            "yaxis2": dict(
                tickformat=".0%",
                range=[-0.3, 0.5],
            ),
        }
    )
    return fig


import pandas as pd
from pandas.tseries.offsets import MonthEnd
import plotly.graph_objects as go
from ix.misc import theme

# from ix.db.query import Offset, Cycle, Series, StandardScalar  # Commented out - MongoDB not in use
from ix.fig.base import timeseries_layout


def eps_yoy_growth() -> go.Figure:

    # =GetSeries({"T12M QoQ Ann.=Series('SPX Index:EPS_LTMA').pct_change(20*3)*100*4","N12M QoQ Ann.=Series('SPX Index:EPS_NTMA').pct_change(20*3)*100*4"}, EDATE(AsOfDate,-24))

    fig = go.Figure()
    fig.update_layout(timeseries_layout)

    spx_ltma = Series("SPX Index:EPS_LTMA", freq="B")
    spx_ntma = Series("SPX Index:EPS_NTMA", freq="B")
    spx_eps_yoy = spx_ntma.div(spx_ltma).sub(1)

    if not spx_eps_yoy.empty:
        fig.add_trace(
            go.Scatter(
                x=spx_eps_yoy.index,
                y=spx_eps_yoy.values,
                name=(f"S&P500 ({spx_eps_yoy.iloc[-1]:.2%})"),
                line=dict(color=theme.colors.blue[400], width=3),
                hovertemplate="<b>S&P500</b>: %{y:.2%}<extra></extra>",
                yaxis="y1",
            )
        )
    # =GetSeries({"T12M QoQ Ann.=Series('SXXP Index:EPS_LTMA').pct_change(20*3)*100*4","N12M QoQ Ann.=Series('SXXP Index:EPS_NTMA').pct_change(20*3)*100*4"}, EDATE(AsOfDate,-24))

    eurostoxx_ltma = Series("SXXP Index:EPS_LTMA", freq="B")
    eurostoxx_ntma = Series("SXXP Index:EPS_NTMA", freq="B")
    eurostoxx_eps_yoy = eurostoxx_ntma.div(eurostoxx_ltma).sub(1)

    if not eurostoxx_eps_yoy.empty:
        fig.add_trace(
            go.Scatter(
                x=eurostoxx_eps_yoy.index,
                y=eurostoxx_eps_yoy.values,
                name=(f"Europe ({eurostoxx_eps_yoy.iloc[-1]:.2%})"),
                line=dict(color=theme.colors.red[400], width=3),
                hovertemplate="<b>Europe</b>: %{y:.2%}<extra></extra>",
                yaxis="y1",
            )
        )
    eurostoxx_ltma = Series("KOSPI Index:EPS_LTMA", freq="B")
    eurostoxx_ntma = Series("KOSPI Index:EPS_NTMA", freq="B")
    eurostoxx_eps_yoy = eurostoxx_ntma.div(eurostoxx_ltma).sub(1)

    if not eurostoxx_eps_yoy.empty:
        fig.add_trace(
            go.Scatter(
                x=eurostoxx_eps_yoy.index,
                y=eurostoxx_eps_yoy.values,
                name=(f"Korea ({eurostoxx_eps_yoy.iloc[-1]:.2%})"),
                line=dict(color=theme.colors.green[400], width=3),
                hovertemplate="<b>Korea</b>: %{y:.2%}<extra></extra>",
                yaxis="y2",
            )
        )

        # FC0000JP
    eurostoxx_ltma = Series("FC0000JP:EPS_LTMA", freq="B")
    eurostoxx_ntma = Series("FC0000JP:EPS_NTMA", freq="B")
    eurostoxx_eps_yoy = eurostoxx_ntma.div(eurostoxx_ltma).sub(1)

    if not eurostoxx_eps_yoy.empty:
        fig.add_trace(
            go.Scatter(
                x=eurostoxx_eps_yoy.index,
                y=eurostoxx_eps_yoy.values,
                name=(f"Japan ({eurostoxx_eps_yoy.iloc[-1]:.2%})"),
                line=dict(color=theme.colors.cyan[400], width=3),
                hovertemplate="<b>Japan</b>: %{y:.2%}<extra></extra>",
                yaxis="y2",
            )
        )
    fig.update_layout(
        {
            "title": dict(
                text=f"Forward EPS YoY Growth",
            ),
            "yaxis": dict(
                tickformat=".0%",
                range=[-0.1, 0.3],
            ),
            "yaxis2": dict(
                tickformat=".0%",
                range=[-0.2, 0.6],
            ),
        }
    )

    return fig


def large_bank_credit_lending_conditions() -> go.Figure:

    # =GetSeries({"Loans & Leases in Bank Credit YoY=Series('FRBBCABLBA@US',freq='W-Fri').ffill().pct_change(52).mul(100).dropna()","SLOOS, C&I Standards Large & Medium Firms (12M Lead)=MonthEndOffset(Series('USSU0486263',freq='ME').ffill(),12)"},EOMONTH(AsOfDate,-240))

    fig = go.Figure()
    fig.update_layout(timeseries_layout)

    consumer = (
        Series("FRBBCABLBA@US:PX_LAST", freq="W-Fri")
        .ffill()
        .pct_change(52)
        .mul(100)
        .dropna()
    )
    if not consumer.empty:
        fig.add_trace(
            go.Scatter(
                x=consumer.index,
                y=consumer.values,
                name=(f"Loans & Leases in Bank Credit YoY({consumer.iloc[-1]:.2f})"),
                line=dict(color=theme.colors.blue[400], width=3),
                hovertemplate="<b>Loans & Leases in Bank Credit YoY</b>: %{y:.2f}<extra></extra>",
                yaxis="y1",
            )
        )

    business = MonthEndOffset(Series("USSU0486263:PX_LAST", freq="ME").ffill(), 12)
    if not business.empty:
        fig.add_trace(
            go.Scatter(
                x=business.index,
                y=business.values,
                name=(f"Loans Standards ({business.iloc[-1]:.2f}) [R]"),
                line=dict(color=theme.colors.red[400], width=3),
                hovertemplate="<b>Loans Standards</b>: %{y:.2f}<extra></extra>",
                yaxis="y2",
            )
        )

    fig.update_layout(
        {
            "title": dict(
                text=f"Credit Lending Conditions (US)",
            ),
            "yaxis": dict(
                # title=dict(text="Consumer"),
                tickformat=".0f",
            ),
            "yaxis2": dict(
                # title=dict(text="Business"),
                tickformat=".0f",
                autorange="reversed",
            ),
        }
    )

    return fig
