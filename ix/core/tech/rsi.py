from typing import Optional
import pandas as pd
import plotly.graph_objects as go
from ix.db.client import get_timeseries


class RSI:

    @classmethod
    def from_meta(
        cls,
        code: str,
        window: int = 14,
        overbought: float = 70,
        oversold: float = 30,
    ) -> "RSI":
        return cls(
            px_last = get_timeseries(code=code, field="PX_LAST"),
            window=window,
            overbought=overbought,
            oversold=oversold,
        )

    def __init__(
        self,
        px_last: pd.Series,
        window: int = 14,
        overbought: float = 70,
        oversold: float = 30,
    ) -> None:
        """
        Initialize the RSI class.

        :param px: Pandas Series of prices (e.g., closing prices).
        :param window: Rolling window size for RSI calculation (default is 14).
        :param overbought: RSI value indicating overbought conditions (default is 70).
        :param oversold: RSI value indicating oversold conditions (default is 30).
        """
        if px_last.empty:
            raise ValueError("The price series (px) must not be empty.")
        if not isinstance(px_last, pd.Series):
            raise TypeError("The price series (px) must be a pandas Series.")
        if not pd.api.types.is_numeric_dtype(px_last):
            raise ValueError("The price series (px) must contain numeric data.")

        self.px = px_last
        self.window = window
        self.overbought = overbought
        self.oversold = oversold
        self.rsi = self._rsi()
        self.signals = self._calculate_signals()

    def _rsi(self) -> pd.Series:
        """
        Calculate the RSI (Relative Strength Index).

        RSI = 100 - (100 / (1 + RS)),
        where RS is the average of gains over the average of losses for the rolling window.

        :return: Pandas Series of RSI values.
        """
        delta = self.px.diff(1).astype(float)
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(self.window, min_periods=1).mean()
        avg_loss = loss.rolling(self.window, min_periods=1).mean()

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _calculate_signals(self) -> pd.Series:
        """
        Detect overbought and oversold conditions based on RSI values.
        Only considers when the RSI crosses the thresholds.

        :return: A Pandas Series where 1 indicates crossing above overbought,
                 -1 indicates crossing below oversold, and 0 indicates neither.
        """
        signals = pd.Series(0, index=self.px.index)

        # Detect crossing above overbought threshold
        signals[
            (self.rsi > self.overbought) & (self.rsi.shift(1) <= self.overbought)
        ] = 1

        # Detect crossing below oversold threshold
        signals[(self.rsi < self.oversold) & (self.rsi.shift(1) >= self.oversold)] = -1

        return signals

    def to_dataframe(self, start: Optional[str] = None) -> pd.DataFrame:
        """
        Return the RSI values and signals as a DataFrame.

        :return: DataFrame with columns for the price, RSI values, and signals.
        """
        df = pd.DataFrame({"Price": self.px, "RSI": self.rsi, "Signals": self.signals})
        if start:
            return df.loc[start:]
        return df

    def plot(
        self,
        title: str = "Relative Strength Index (RSI)",
        start: Optional[str] = None,
    ) -> go.Figure:
        """
        Create an interactive Plotly chart of the RSI along with the price series.

        :param title: Title of the plot.
        :return: Plotly Figure object.
        """
        df = self.to_dataframe(start=start)

        fig = go.Figure()

        # Price
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["Price"],
                name="Price",
                line=dict(color="black", width=1),
                yaxis="y2",
            )
        )

        # RSI
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["RSI"],
                name="RSI",
                line=dict(color="blue", width=1),
            )
        )

        # Overbought and Oversold lines
        fig.add_hline(
            y=self.overbought,
            line_dash="dash",
            line_color="red",
            name=f"Overbought ({self.overbought})",
        )
        fig.add_hline(
            y=self.oversold,
            line_dash="dash",
            line_color="green",
            name=f"Oversold ({self.oversold})",
        )

        # Signals
        fig.add_trace(
            go.Scatter(
                x=df[df["Signals"] == 1].index,
                y=df.loc[df["Signals"] == 1, "RSI"],
                mode="markers",
                name="Overbought Signal",
                marker=dict(symbol="triangle-down", size=10, color="red"),
                hoverinfo="x+y",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df[df["Signals"] == -1].index,
                y=df.loc[df["Signals"] == -1, "RSI"],
                mode="markers",
                name="Oversold Signal",
                marker=dict(symbol="triangle-up", size=10, color="green"),
                hoverinfo="x+y",
            )
        )

        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="RSI",
            yaxis2=dict(title="Price", overlaying="y", side="right"),
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            hovermode="x unified",
        )

        fig.update_yaxes(range=[0, 100])

        # Set x-axis range to match the data
        x_min = df.index.min()
        x_max = df.index.max()
        fig.update_xaxes(range=[x_min, x_max])

        return fig
