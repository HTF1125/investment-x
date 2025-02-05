from typing import Optional
import pandas as pd
import plotly.graph_objects as go
from ix.db.client import get_timeseries


class BollingerBand:

    @classmethod
    def from_meta(
        cls,
        code: str,
        window: int = 20,
        n_stds: float = 2.0,
    ) -> "BollingerBand":
        return cls(
            px_last=get_timeseries(code=code),
            window=window,
            n_stds=n_stds,
        )

    def __init__(
        self,
        px_last: pd.Series,
        window: int = 20,
        n_stds: float = 2.0,
    ) -> None:
        """
        Initialize the BollingerBand class.

        :param px: Pandas Series of prices (e.g., closing prices).
        :param window: Rolling window size for calculating the moving average and standard deviation.
        :param n_stds: Number of standard deviations for the upper and lower bands.
        """
        if px_last.empty:
            raise ValueError("The price series (px) must not be empty.")
        if not isinstance(px_last, pd.Series):
            raise TypeError("The price series (px) must be a pandas Series.")
        if not pd.api.types.is_numeric_dtype(px_last):
            raise ValueError("The price series (px) must contain numeric data.")

        self.px = px_last
        self.window = window
        self.n_stds = n_stds

        self.rolling_std = self.px.rolling(self.window).std()
        self.middle = self.px.rolling(self.window).mean()
        self.upper = self.middle + self.n_stds * self.rolling_std
        self.lower = self.middle - self.n_stds * self.rolling_std

    def get_breakouts(
        self, px: pd.Series, upper: pd.Series, lower: pd.Series
    ) -> pd.Series:
        """
        Detect when the price breaks out of the Bollinger Bands.

        A breakout occurs when:
        - The price crosses above the upper band (price > upper band and price at the previous step <= upper band).
        - The price crosses below the lower band (price < lower band and price at the previous step >= lower band).

        :return: A Pandas Series where 1 indicates an upper breakout, -1 a lower breakout, and 0 no breakout.
        """
        upper_breakout = (px > upper) & (px.shift(1) <= upper.shift(1))
        lower_breakout = (px < lower) & (px.shift(1) >= lower.shift(1))

        breakouts = pd.Series(0, index=px.index)
        breakouts[upper_breakout] = 1
        breakouts[lower_breakout] = -1

        return breakouts

    def to_dataframe(self, start: Optional[str] = None) -> pd.DataFrame:
        """
        Return the Bollinger Bands as a DataFrame.

        :return: DataFrame with columns for the price, middle, upper, and lower bands.
        """
        df = pd.DataFrame(
            {
                "Price": self.px,
                "Middle Band": self.middle,
                "Upper Band": self.upper,
                "Lower Band": self.lower,
            }
        )

        if start:
            df = df.loc[start:]

        df["Breakouts"] = self.get_breakouts(
            df["Price"], df["Upper Band"], df["Lower Band"]
        )
        return df

    def plot(
        self, title: str = "Bollinger Bands", start: Optional[str] = None
    ) -> go.Figure:
        """
        Create an interactive Plotly chart of the Bollinger Bands along with the price series.

        :param title: Title of the plot.
        :return: Plotly Figure object.
        """
        df = self.to_dataframe(start=start)

        fig = go.Figure()

        # Price and Bollinger Bands
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["Price"],
                name="Price",
                line=dict(color="black", width=1),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["Middle Band"],
                name="Middle Band",
                line=dict(color="blue", width=1),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["Upper Band"],
                name="Upper Band",
                line=dict(color="green", width=1),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["Lower Band"],
                name="Lower Band",
                line=dict(color="red", width=1),
            )
        )

        # Add fill between upper and lower bands
        fig.add_trace(
            go.Scatter(
                x=df.index.tolist() + df.index.tolist()[::-1],
                y=df["Upper Band"].tolist() + df["Lower Band"].tolist()[::-1],
                fill="toself",
                fillcolor="rgba(0,100,80,0.2)",
                line=dict(color="rgba(255,255,255,0)"),
                hoverinfo="skip",
                showlegend=False,
            )
        )

        # Breakout signals
        breakouts = df["Breakouts"]
        fig.add_trace(
            go.Scatter(
                x=breakouts[breakouts == 1].index,
                y=df.loc[breakouts == 1, "Price"],
                mode="markers",
                name="Upper Breakout",
                marker=dict(symbol="triangle-up", size=10, color="purple"),
                hoverinfo="x+y",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=breakouts[breakouts == -1].index,
                y=df.loc[breakouts == -1, "Price"],
                mode="markers",
                name="Lower Breakout",
                marker=dict(symbol="triangle-down", size=10, color="orange"),
                hoverinfo="x+y",
            )
        )

        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title="Price",
            legend=dict(
                orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
            ),
            margin=dict(t=130),  # Increased top margin
            hovermode="x unified",
        )

        fig.update_layout(
            yaxis=dict(
                autorange=True,
                fixedrange=False,
            )
        )

        # Set x-axis range to match the data
        x_min = df.index.min()
        x_max = df.index.max()
        fig.update_xaxes(range=[x_min, x_max])

        return fig
