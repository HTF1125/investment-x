import pandas as pd
import plotly.graph_objects as go
from ix.dash.settings import theme
from ix.db import Offset, Cycle, Series
from ix.db import financial_conditions_us
from ix.db import M2
from .base import TimeseriesChart


class OecdCliRegime(TimeseriesChart):

    def plot(self):
        self.fig.update_layout(
            barmode="stack",
            title=dict(text=f"PMI Manufacturing Regime"),
        )
        from ix.db import oecd_cli_regime

        regimes = oecd_cli_regime()

        # Use theme.chart_colors for bar colors
        colors = theme.chart_colors
        for i, (name, series) in enumerate(regimes.items()):
            color = colors[i % len(colors)]
            self.fig.add_trace(
                go.Bar(
                    x=series.index,
                    y=series.values,
                    name=name,
                    marker_color=color,
                    hovertemplate="%{y:.2f}",
                )
            )
        return self.layout()


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


class FedNetLiquiditySp500(TimeseriesChart):

    def add_fed_net_liquidity_trace(self):
        net_liquidity = get_fed_net_liquidity_series().pct_change(52).dropna() * 100

        # Fed Net Liquidity trace
        self.fig.add_trace(
            go.Scatter(
                x=net_liquidity.index,
                y=net_liquidity.values,
                name="Fed Net Liquidity YoY",
                line=dict(color=theme.chart_colors[0], width=3),
                hovertemplate="%{y:.2f}",
            )
        )

    def add_sp500_trace(self):
        sp500 = Series("SPX Index:PX_LAST", freq="W").pct_change(52).dropna() * 100

        # S&P 500 trace
        self.fig.add_trace(
            go.Scatter(
                x=sp500.index,
                y=sp500.values,
                name=sp500.name,
                yaxis="y2",
                line=dict(color=theme.chart_colors[1], width=3),
                hovertemplate="%{y:.2f}",
            )
        )

    def plot(self):
        """
        Plot Fed Net Liquidity YoY % vs S&P 500 YoY %.
        """
        self.fig.update_layout(title="Fed Net Liquidity YoY % vs S&P 500 YoY %")
        self.add_fed_net_liquidity_trace()
        self.add_sp500_trace()
        return self.layout()


class FinancialConditionsUS(TimeseriesChart):

    def add_fci_trace(self):
        fci = Offset(financial_conditions_us(), months=6) * 100
        self.fig.add_trace(
            go.Scatter(
                x=fci.index,
                y=fci.values,
                name="FCI 6M Lead",
                line=dict(color=theme.chart_colors[0], width=3),
                hovertemplate="%{y:.2f}",
            )
        )

    def add_cycle(self):
        fci = Cycle(Offset(financial_conditions_us(), months=6), 60 * 5) * 100
        self.fig.add_trace(
            go.Scatter(
                x=fci.index,
                y=fci.values,
                name="Cycle",
                line=dict(color=theme.chart_colors[1], width=3),
                hovertemplate="%{y:.2f}",
            )
        )

    def add_ism(self):
        ism = Series("ISMPMI_M:PX_LAST", freq="ME")
        self.fig.add_trace(
            go.Scatter(
                x=ism.index,
                y=ism.values,
                name="ISM",
                line=dict(color=theme.chart_colors[2], width=3),
                hovertemplate="%{y:.2f}",
                yaxis="y2",
            )
        )

    def plot(self) -> go.Figure:
        self.fig.update_layout(title="Financial Conditions US")
        self.add_fci_trace()
        self.add_cycle()
        self.add_ism()
        return self.layout()


class GlobalM2GrowthContribution(TimeseriesChart):

    def plot(self) -> go.Figure:
        self.fig.update_layout(title="Global M2 Growth Contribution (%)")

        m2 = M2("ME")
        total = m2.WorldTotal.pct_change(12)
        contrib = {k: v for k, v in m2.WorldContribution.items()}

        total = total.mul(100)

        self.fig.add_trace(
            go.Scatter(
                x=total.index,
                y=total.values,
                name=f"Total",
                mode="lines",
                line=dict(color=theme.primary, width=3),
                hovertemplate="%{y:.2f}",
            )
        )

        palette = theme.chart_colors
        for i, (name, s) in enumerate(contrib.items()):
            if s is None or len(s) == 0:
                continue
            s = s.mul(100)
            self.fig.add_trace(
                go.Bar(
                    x=s.index,
                    y=s.values,
                    name=name,
                    marker_color=palette[i % len(palette)],
                    hovertemplate="%{y:.2f}",
                )
            )

        return self.layout()


class GlobalM2Growth(TimeseriesChart):

    def plot(self):
        self.fig.update_layout(title="Global M2 Growth Y/Y (%)")
        m2q = M2("W").World.ffill()
        yoy = m2q.pct_change(52).mul(100).dropna()
        palette = theme.chart_colors
        for i, col in enumerate(yoy.columns):
            s = yoy[col].dropna()
            if s.empty:
                continue
            self.fig.add_trace(
                go.Scatter(
                    x=s.index,
                    y=s.values,
                    name=col,
                    mode="lines",
                    line=dict(color=palette[i % len(palette)], width=2),
                    hovertemplate="%{y:.2f}",
                )
            )

        return self.layout()
