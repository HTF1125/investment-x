import pandas as pd
import plotly.graph_objects as go
from ix.misc import theme
from ix.db.query import Offset, Cycle, Series, StandardScalar
from .base import timeseries_layout


def FinancialConditionsUS():

    fci_us = (
        pd.concat(
            [
                StandardScalar(-Series("DXY Index:PX_LAST", freq="W").ffill(), 52 * 3),
                StandardScalar(-Series("TRYUS10Y:PX_YTM", freq="W").ffill(), 52 * 3),
                StandardScalar(-Series("TRYUS30Y:PX_YTM", freq="W").ffill(), 52 * 3),
                StandardScalar(Series("SPX Index:PX_LAST", freq="W").ffill(), 52 * 3),
                StandardScalar(-Series("MORTGAGE30US", freq="W").ffill(), 52 * 3),
                StandardScalar(-Series("CL1 Comdty:PX_LAST", freq="W").ffill(), 52 * 3),
                StandardScalar(-Series("BAMLC0A0CM", freq="W").ffill(), 52 * 3),
            ],
            axis=1,
        )
        .mean(axis=1)
        .ewm(span=4 * 12)
        .mean()
    )

    fci = Offset(fci_us.resample("W").last().ffill().loc["2000":], months=6)
    cyc = Cycle(fci)
    ism = Series("ISMPMI_M:PX_LAST", freq="ME")

    latest_fci = fci.values[-1] if len(fci.values) > 0 else None
    latest_cyc = cyc.values[-1] if len(cyc.values) > 0 else None
    latest_ism = ism.values[-1] if len(ism.values) > 0 else None

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=fci.index,
            y=fci.values,
            name=(
                f"FCI 6M Lead ({latest_fci:.2%})"
                if latest_fci is not None
                else "FCI 6M Lead"
            ),
            line=dict(color=theme.colors.blue[400], width=1),
            hovertemplate="<b>FCI</b>: %{y:.2%}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=cyc.index,
            y=cyc.values,
            name=f"Cycle ({latest_cyc:.2%})" if latest_cyc is not None else "Cycle",
            line=dict(color=theme.colors.green[400], width=1, dash="dot"),
            hovertemplate="<b>Cycle</b>: %{y:.2%}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=ism.index,
            y=ism.values,
            name=f"ISM PMI ({latest_ism:.1f})" if latest_ism is not None else "ISM PMI",
            yaxis="y2",
            line=dict(color=theme.colors.red[400], width=1),
            hovertemplate="<b>ISM PMI</b>: %{y:.1f}<extra></extra>",
        )
    )

    # Apply dark theme layout
    layout = timeseries_layout.copy()
    layout.update(
        {
            "title": dict(
                text=f"Financial Conditions (United States)",
                x=0.05,
                font=dict(size=14, family="Arial Black", color="#FFFFFF"),
            ),
            "yaxis": dict(
                title=dict(text="Financial Conditions", font=dict(color="#FFFFFF")),
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=True,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
                range=[-1, 1],
            ),
            "yaxis2": dict(
                title=dict(text="ISM", font=dict(color="#FFFFFF")),
                overlaying="y",
                side="right",
                tickformat=".0f",
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=False,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
                range=[30, 70],
            ),
        }
    )
    fig.update_layout(layout)

    fig.add_hline(
        y=50,
        line_dash="dash",
        line_color=theme.colors.text_muted,
        line_width=1,
        annotation_text="Expansion/Contraction",
        annotation_position="top right",
        annotation_font_size=10,
        annotation_font_color=theme.colors.text_muted,
        yref="y2",
    )
    return fig


from ix.db.query import M2


def GlobalLiquidityCycle():
    def _normalize_percent(s):
        s = s.astype(float)
        return s / 100.0 if s.dropna().abs().median() > 1.5 else s

    gl = Offset(M2("ME").WorldTotal.pct_change(12), months=9)
    gl = _normalize_percent(gl)
    cyc = Cycle(gl, 60)
    ism = Series("ISMPMI_M:PX_LAST", freq="ME")

    latest_gl = gl.values[-1] if len(gl.values) > 0 else None
    latest_cyc = cyc.values[-1] if len(cyc.values) > 0 else None
    latest_ism = ism.values[-1] if len(ism.values) > 0 else None

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=gl.index,
            y=gl.values,
            name=(
                f"Global Liquidity 9M Lead ({latest_gl:.2%})"
                if latest_gl is not None
                else "Global Liquidity 9M Lead"
            ),
            line=dict(color=theme.colors.blue[400], width=1),
            hovertemplate="<b>Global Liquidity YoY</b>: %{y:.2%}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=cyc.index,
            y=cyc.values,
            name=f"Cycle ({latest_cyc:.2%})" if latest_cyc is not None else "Cycle",
            line=dict(color=theme.colors.green[400], width=1, dash="dot"),
            hovertemplate="<b>Cycle</b>: %{y:.2%}<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=ism.index,
            y=ism.values,
            name=f"ISM PMI ({latest_ism:.1f})" if latest_ism is not None else "ISM PMI",
            yaxis="y2",
            line=dict(color=theme.colors.red[400], width=1),
            hovertemplate="<b>ISM PMI</b>: %{y:.1f}<extra></extra>",
        )
    )

    # Apply dark theme layout
    layout = timeseries_layout.copy()
    layout.update(
        {
            "title": dict(
                text=f"Global Liquidity Cycle (M2)",
                x=0.05,
                font=dict(size=14, family="Arial Black", color="#FFFFFF"),
            ),
            "yaxis": dict(
                title=dict(text="Global Liquidity YoY", font=dict(color="#FFFFFF")),
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=True,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
                tickformat=".0%",
            ),
            "yaxis2": dict(
                title=dict(text="ISM", font=dict(color="#FFFFFF")),
                overlaying="y",
                side="right",
                tickformat=".0f",
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=False,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
                range=[30, 70],
            ),
        }
    )
    fig.update_layout(layout)
    fig.add_hline(
        y=50,
        line_dash="dash",
        line_color=theme.colors.text_muted,
        line_width=1,
        annotation_text="Expansion/Contraction",
        annotation_position="top right",
        annotation_font_size=10,
        annotation_font_color=theme.colors.text_muted,
        yref="y2",
    )
    return fig


def M2GrowthContribution():
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
            line=dict(color=theme.colors.blue[400], width=1),
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
    # Apply dark theme layout
    layout = timeseries_layout.copy()
    layout.update(
        {
            "title": dict(
                text=f"Global M2 Growth Contributions",
                x=0.05,
                font=dict(size=14, family="Arial Black", color="#FFFFFF"),
            ),
            "yaxis": dict(
                title=dict(text="Global M2 YoY", font=dict(color="#FFFFFF")),
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=True,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
                tickformat=".0%",
            ),
            "yaxis2": dict(
                title=dict(text="ISM", font=dict(color="#FFFFFF")),
                overlaying="y",
                side="right",
                tickformat=".0f",
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
    fig.update_layout(barmode="relative")
    return fig


def M2Growth():
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
    layout = timeseries_layout.copy()
    layout.update(
        {
            "title": dict(
                text=f"Global M2 Growth",
                x=0.05,
                font=dict(size=14, family="Arial Black", color="#FFFFFF"),
            ),
            "yaxis": dict(
                title=dict(text="M2 YoY", font=dict(color="#FFFFFF")),
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=True,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
                tickformat=".0%",
            ),
        }
    )
    fig.update_layout(layout)

    return fig


from ix import Series
import pandas as pd
import plotly.graph_objects as go


def credit_impulse_us():
    data = pd.DataFrame(
        {
            "BACROUTP": Series("US.BACROUTP", freq="ME"),
            "FRBBCABLCCBA@US": Series("FRBBCABLCCBA@US", freq="ME"),
            "FRBBCABLCRCBA@US": Series("FRBBCABLCRCBA@US", freq="ME"),
            "GDPN": Series("US.GDPN"),
        }
    )
    data.ffill(inplace=True)
    ff = data["BACROUTP"].add(data["FRBBCABLCCBA@US"]).add(data["FRBBCABLCRCBA@US"])
    gg = data["GDPN"]
    return ff.diff().rolling(12).sum().diff(12) / gg


def credit_impulse_cn():
    data = pd.DataFrame(
        {
            "CN": Series("CNBC2252509", freq="ME"),
            "GDPN": Series("CN.GDPNNSA", freq="ME"),
        }
    )
    data.ffill(inplace=True)
    return data["CN"].rolling(12).sum().diff(12) / data["GDPN"]


def CreditImpulseUSvsCN():
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
            line=dict(color="royalblue"),
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
            line=dict(color="firebrick"),
            yaxis="y2",
            hovertemplate="China Credit Impulse: %{y:.2%}<extra></extra>",
        )
    )
    fig.update_layout(
        xaxis_title="Date",
        yaxis=dict(
            title="US Credit Impulse (YoY, % GDP)",
            tickformat=".0%",
        ),
        yaxis2=dict(
            title="China Credit Impulse (YoY, % GDP)",
            overlaying="y",
            side="right",
            tickformat=".0%",
        ),
        hovermode="x unified",
    )

    # Apply dark theme layout
    layout = timeseries_layout.copy()
    layout.update(
        {
            "title": dict(
                text=f"Credit Impulse US vs CN",
                x=0.05,
                font=dict(size=14, family="Arial Black", color="#FFFFFF"),
            ),
            "yaxis": dict(
                title=dict(text="United States", font=dict(color="#FFFFFF")),
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=True,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
                tickformat=".0%",
            ),
            "yaxis2": dict(
                title=dict(text="China", font=dict(color="#FFFFFF")),
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
        }
    )
    fig.update_layout(layout)
    return fig


from ix import InvestorPositions
import plotly.graph_objects as go


def InvestorPositionsChart():

    investor_positions = InvestorPositions()

    # Create a new plotly figure and add traces from investor_positions data
    fig = go.Figure()

    for name, series in investor_positions.items():
        fig.add_trace(
            go.Scatter(x=series.index, y=series.values, mode="lines", name=name)
        )

    # Apply dark theme layout
    layout = timeseries_layout.copy()
    layout.update(
        {
            "title": dict(
                text=f"Investor Positions",
                x=0.05,
                font=dict(size=14, family="Arial Black", color="#FFFFFF"),
            ),
            "yaxis": dict(
                title=dict(text="Open Interest", font=dict(color="#FFFFFF")),
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=True,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
                tickformat=".0f",
            ),
        }
    )
    fig.update_layout(layout)
    return fig


from ix.db import Series
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


def FedNetLiquidityVsSP500():
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
            line=dict(color=theme.colors.blue[400], width=1),
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
            yaxis="y2",
            line=dict(color=theme.colors.green[400], width=1),
            hovertemplate="<b>S&P 500 YoY</b>: %{y:.2%}<extra></extra>",
        )
    )

    # Apply dark theme layout
    layout = timeseries_layout.copy()
    layout.update(
        {
            "title": dict(
                text=f"Fed Net Liquidity vs S&P500",
                x=0.05,
                font=dict(size=14, family="Arial Black", color="#FFFFFF"),
            ),
            "yaxis": dict(
                title=dict(text="Fed Net Liquidity YoY", font=dict(color="#FFFFFF")),
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=True,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
                range=[-0.2, 0.5],
                tickformat=".0%",
            ),
            "yaxis2": dict(
                title=dict(text="S&P500 YoY", font=dict(color="#FFFFFF")),
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
        }
    )
    fig.update_layout(layout)

    # Optionally, add a band for recession periods or highlight recent data
    # (Not implemented here, but could be added for further improvement)

    # Show the figure with the new width prop
    return fig


import pandas as pd
from ix.db.query import MultiSeries


class AiCapex:

    def FE_CAPEX_NTMA(self) -> pd.DataFrame:
        return (
            MultiSeries(
                "Nvdia=NVDA,Google=GOOG,Microsoft=MSFT,Amazon=AMZN,Meta=META",
                field="FE_CAPEX_NTMA",
                freq="B",
            )
            .ffill()
            .dropna()
        )

    def FE_CAPEX_LTMA(self) -> pd.DataFrame:
        return (
            MultiSeries(
                "Nvdia=NVDA,Google=GOOG,Microsoft=MSFT,Amazon=AMZN,Meta=META",
                field="FE_CAPEX_LTMA",
                freq="B",
            )
            .ffill()
            .dropna()
        )

    def FE_CAPEX_Q(self) -> pd.DataFrame:
        return (
            MultiSeries(
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


def AiCapexQuarterlyYoY():

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
                line=dict(width=1),
                hovertemplate=f"<b>{name}</b>: %{{y:.2%}}<extra></extra>",
            )
        )
    # Apply dark theme layout
    layout = timeseries_layout.copy()
    layout.update(
        {
            "title": dict(
                text=f"Quarterly Capital Expenditure (AI)",
                x=0.05,
                font=dict(size=14, family="Arial Black", color="#FFFFFF"),
            ),
            "yaxis": dict(
                title=dict(text="Capex Quarterly YoY", font=dict(color="#FFFFFF")),
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=True,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
                tickformat=".0%",
            ),
        }
    )
    fig.update_layout(layout)
    fig.update_layout(barmode="relative")
    return fig


def AiCapexYearlylyYoY():

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
                line=dict(width=1),
                hovertemplate=f"<b>{name}</b>: %{{y:.2%}}<extra></extra>",
            )
        )
    # Apply dark theme layout
    layout = timeseries_layout.copy()
    layout.update(
        {
            "title": dict(
                text=f"Yearly Capital Expenditure (AI)",
                x=0.05,
                font=dict(size=14, family="Arial Black", color="#FFFFFF"),
            ),
            "yaxis": dict(
                title=dict(text="Capex Yearly YoY", font=dict(color="#FFFFFF")),
                gridcolor="rgba(255,255,255,0.2)",
                zeroline=False,
                showline=True,
                linecolor="rgba(255,255,255,0.4)",
                mirror=True,
                tickfont=dict(color="#FFFFFF"),
                tickformat=".0%",
            ),
        }
    )
    fig.update_layout(layout)
    fig.update_layout(barmode="relative")
    return fig
