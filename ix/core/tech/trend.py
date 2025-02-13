from typing import Optional
import pandas as pd
import plotly.graph_objects as go
from ix.db.client import get_timeseries


class WaveTrend:
    @classmethod
    def from_meta(
        cls,
        code: str,
        n1: int = 10,
        n2: int = 21,
        ob_level1: float = 60,
        ob_level2: float = 53,
        os_level1: float = -60,
        os_level2: float = -53,
    ) -> "WaveTrend":
        """
        Initialize the WaveTrend indicator using a meta-code.
        This method retrieves time series data based on the code.
        """
        px_close = get_timeseries(code=code, field="PX_LAST")
        px_high = get_timeseries(code=code, field="PX_HIGH")
        px_low = get_timeseries(code=code, field="PX_LOW")

        if px_high.empty:
            px_high = None
        if px_low.empty:
            px_low = None

        return cls(
            px_close=px_close,
            px_high=px_high,
            px_low=px_low,
            n1=n1,
            n2=n2,
            ob_level1=ob_level1,
            ob_level2=ob_level2,
            os_level1=os_level1,
            os_level2=os_level2,
        )

    def __init__(
        self,
        px_close: pd.Series,
        px_high: Optional[pd.Series] = None,
        px_low: Optional[pd.Series] = None,
        n1: int = 10,
        n2: int = 21,
        ob_level1: float = 60,
        ob_level2: float = 53,
        os_level1: float = -60,
        os_level2: float = -53,
    ) -> None:
        """
        Initialize the WaveTrend indicator.

        If either `px_high` or `px_low` is not provided, they are replaced with `px_close`.

        :param px_close: Series of close prices.
        :param px_high: Series of high prices (optional).
        :param px_low: Series of low prices (optional).
        :param n1: Channel Length.
        :param n2: Average Length.
        :param ob_level1: Overbought Level 1.
        :param ob_level2: Overbought Level 2.
        :param os_level1: Oversold Level 1.
        :param os_level2: Oversold Level 2.
        """
        # Use close prices if high or low is not provided.
        if px_high is None:
            px_high = px_close.copy()
        if px_low is None:
            px_low = px_close.copy()

        # Combine the price series into a single DataFrame.
        self.hlc = pd.concat([px_close, px_high, px_low], axis=1)
        self.hlc.columns = ["close", "high", "low"]
        self.n1 = n1
        self.n2 = n2
        self.ob_level1 = ob_level1
        self.ob_level2 = ob_level2
        self.os_level1 = os_level1
        self.os_level2 = os_level2

        self._calculate_wavetrend()

    def _calculate_wavetrend(self) -> None:
        """Calculate the WaveTrend indicators."""
        # Typical price (ap): equivalent to Pine Script's hlc3.
        self.hlc["ap"] = (self.hlc["high"] + self.hlc["low"] + self.hlc["close"]) / 3

        # Exponential moving average (ema) of the typical price.
        self.hlc["esa"] = (
            self.hlc["ap"].ewm(span=self.n1, adjust=False, min_periods=self.n1).mean()
        )

        # EMA of the absolute difference between the typical price and its EMA.
        self.hlc["d"] = (
            (self.hlc["ap"] - self.hlc["esa"])
            .abs()
            .ewm(span=self.n1, adjust=False, min_periods=self.n1)
            .mean()
        )

        # Calculate the 'ci' value.
        self.hlc["ci"] = (self.hlc["ap"] - self.hlc["esa"]) / (0.015 * self.hlc["d"])

        # Smooth the 'ci' with another EMA.
        self.hlc["tci"] = (
            self.hlc["ci"].ewm(span=self.n2, adjust=False, min_periods=self.n2).mean()
        )

        # Define the WaveTrend lines.
        self.hlc["wt1"] = self.hlc["tci"]
        self.hlc["wt2"] = self.hlc["wt1"].rolling(window=4).mean()
        self.hlc["wt_diff"] = self.hlc["wt1"] - self.hlc["wt2"]

    def to_dataframe(
        self, start: Optional[str] = None, end: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Return the WaveTrend indicators as a DataFrame.

        :param start: Optional starting date/index (as a string) to filter the data.
        :return: DataFrame containing the 'wt1', 'wt2', and 'wt_diff' columns.
        """
        df = self.hlc[["wt1", "wt2", "wt_diff"]]
        if start:
            df = df.loc[start:]
        if end:
            df = df.loc[:end]
        return df

    def plot(self, start: Optional[str] = None, end: Optional[str] = None) -> go.Figure:
        """
        Create an interactive Plotly chart of the WaveTrend indicator.

        In addition to the WT1 and WT2 lines (and a filled area between them), a bar chart
        representing WT1 - WT2 is added on a secondary y-axis (right side).

        :param title: Title of the plot.
        :param start: Optional starting date/index to filter the data.
        :return: Plotly Figure object.
        """
        df = self.to_dataframe(start=start, end=end)
        fig = go.Figure()

        # Plot the WT1 line.
        fig.add_trace(
            go.Scatter(
                x=df.index, y=df["wt1"], name="WT1", line=dict(color="green", width=2)
            )
        )

        # Plot the WT2 line.
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["wt2"],
                name="WT2",
                line=dict(color="red", width=2, dash="dash"),
            )
        )

        # Add a filled area between WT1 and WT2.
        fig.add_trace(
            go.Scatter(
                x=df.index.tolist() + df.index.tolist()[::-1],
                y=df["wt1"].tolist() + df["wt2"].tolist()[::-1],
                fill="toself",
                fillcolor="rgba(0,100,80,0.2)",
                line=dict(color="rgba(255,255,255,0)"),
                hoverinfo="skip",
                showlegend=False,
            )
        )

        # Add horizontal lines for overbought, oversold levels, and zero.
        for level in [
            self.ob_level1,
            self.ob_level2,
            self.os_level1,
            self.os_level2,
            0,
        ]:
            fig.add_hline(y=level, line_dash="dash", line_color="gray")

        # Add a bar chart trace for WT1 - WT2 (wt_diff) on a secondary y-axis.
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["wt_diff"],
                name="WT1 - WT2",
                marker_color="rgba(0,0,255,0.5)",
                opacity=0.7,
                yaxis="y2",
            )
        )

        # Update layout: primary y-axis on the left and secondary y-axis on the right.
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="WaveTrend",
            yaxis2=dict(
                title="WT1 - WT2",
                overlaying="y",
                side="right",
                showgrid=False,
            ),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5
            ),
            # margin=dict(t=130),
            hovermode="x unified",
        )

        fig.update_layout(yaxis=dict(autorange=True, fixedrange=False))

        # Ensure the x-axis covers the full data range.
        x_min = df.index.min()
        x_max = df.index.max()
        fig.update_xaxes(range=[x_min, x_max])

        return fig
