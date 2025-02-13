from typing import Optional, Union
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ix.db.client import get_timeseries
from ix.misc import get_logger

logger = get_logger(__name__)


class SqueezeMomentum:
    def __init__(
        self,
        px_close: pd.Series,
        px_high: Optional[pd.Series] = None,
        px_low: Optional[pd.Series] = None,
        bb_length: int = 20,
        bb_mult: float = 2.0,
        kc_length: int = 20,
        kc_mult: float = 1.5,
        use_true_range: bool = True,
    ) -> None:
        """
        Initialize the Squeeze Momentum indicator.

        If either `px_high` or `px_low` is not provided, they default to `px_close`.

        Parameters:
            px_close (pd.Series): Series of closing prices.
            px_high (Optional[pd.Series]): Series of high prices.
            px_low (Optional[pd.Series]): Series of low prices.
            bb_length (int): Period for Bollinger Bands.
            bb_mult (float): Multiplier for Bollinger Bands.
            kc_length (int): Period for Keltner Channels.
            kc_mult (float): Multiplier for Keltner Channels.
            use_true_range (bool): Whether to use the True Range for KC computation.
        """
        # Ensure high/low data are provided
        self.px_close = px_close.copy()
        self.px_high = (
            px_high.copy()
            if px_high is not None and not px_high.empty
            else px_close.copy()
        )
        self.px_low = (
            px_low.copy()
            if px_low is not None and not px_low.empty
            else px_close.copy()
        )

        # Combine the price series into a single DataFrame
        self.hlc = pd.concat([self.px_close, self.px_high, self.px_low], axis=1)
        self.hlc.columns = ["close", "high", "low"]

        # Store indicator parameters
        self.bb_length = bb_length
        self.bb_mult = bb_mult
        self.kc_length = kc_length
        self.kc_mult = kc_mult
        self.use_true_range = use_true_range

        # DataFrame to hold all computed values
        self.df: pd.DataFrame = pd.DataFrame()

        # Compute indicator values
        self._calculate_indicator()

    @classmethod
    def from_meta(
        cls,
        code: str,
        bb_length: int = 20,
        bb_mult: float = 2.0,
        kc_length: int = 20,
        kc_mult: float = 1.5,
        use_true_range: bool = True,
    ) -> "SqueezeMomentum":
        """
        Create a SqueezeMomentum instance using a meta-code by retrieving the price data.

        Parameters:
            code (str): The meta-code for retrieving price data.
            bb_length (int): Period for Bollinger Bands.
            bb_mult (float): Multiplier for Bollinger Bands.
            kc_length (int): Period for Keltner Channels.
            kc_mult (float): Multiplier for Keltner Channels.
            use_true_range (bool): Whether to use the True Range for KC computation.

        Returns:
            SqueezeMomentum: An instance of the SqueezeMomentum indicator.
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
            bb_length=bb_length,
            bb_mult=bb_mult,
            kc_length=kc_length,
            kc_mult=kc_mult,
            use_true_range=use_true_range,
        )

    @staticmethod
    def _linreg_last(arr: np.ndarray) -> float:
        """
        Compute the last value of a linear regression fit on the input array.

        Parameters:
            arr (np.ndarray): Array of values for regression.

        Returns:
            float: The predicted value at the last index (or NaN if any value is NaN).
        """
        n = len(arr)
        if np.isnan(arr).any():
            return np.nan
        x = np.arange(n)
        slope, intercept = np.polyfit(x, arr, 1)
        return intercept + slope * (n - 1)

    def _calculate_indicator(self) -> None:
        """
        Calculate the Squeeze Momentum indicator along with auxiliary data.
        """
        df = self.hlc.copy()
        source = df["close"]

        # --- Bollinger Bands (BB) ---
        bb_basis = source.rolling(
            window=self.bb_length, min_periods=self.bb_length
        ).mean()
        bb_std = source.rolling(window=self.bb_length, min_periods=self.bb_length).std()
        upperBB = bb_basis + (self.bb_mult * bb_std)
        lowerBB = bb_basis - (self.bb_mult * bb_std)

        # --- Keltner Channels (KC) ---
        kc_ma = source.rolling(window=self.kc_length, min_periods=self.kc_length).mean()
        if self.use_true_range:
            tr1 = df["high"] - df["low"]
            tr2 = (df["high"] - df["close"].shift(1)).abs()
            tr3 = (df["low"] - df["close"].shift(1)).abs()
            true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        else:
            true_range = df["high"] - df["low"]

        rangema = true_range.rolling(
            window=self.kc_length, min_periods=self.kc_length
        ).mean()
        upperKC = kc_ma + (self.kc_mult * rangema)
        lowerKC = kc_ma - (self.kc_mult * rangema)

        # --- Squeeze Conditions ---
        squeeze_on = (lowerBB > lowerKC) & (upperBB < upperKC)
        squeeze_off = (lowerBB < lowerKC) & (upperBB > upperKC)
        no_squeeze = ~(squeeze_on | squeeze_off)

        # --- Linear Regression for Momentum ---
        highest_high = (
            df["high"].rolling(window=self.kc_length, min_periods=self.kc_length).max()
        )
        lowest_low = (
            df["low"].rolling(window=self.kc_length, min_periods=self.kc_length).min()
        )
        sma_close = source.rolling(
            window=self.kc_length, min_periods=self.kc_length
        ).mean()

        avg1 = (highest_high + lowest_low) / 2
        avg_val = (avg1 + sma_close) / 2

        diff_series = source - avg_val

        momentum = diff_series.rolling(
            window=self.kc_length, min_periods=self.kc_length
        ).apply(self._linreg_last, raw=True)

        # --- Color Assignments for Visualization ---
        prev_momentum = momentum.shift(1)
        bar_color = np.select(
            [
                (momentum > 0) & (momentum > prev_momentum),
                (momentum > 0) & ~(momentum > prev_momentum),
                (momentum < 0) & (momentum < prev_momentum),
                (momentum < 0) & ~(momentum < prev_momentum),
            ],
            ["lime", "green", "red", "maroon"],
            default="green",
        )

        marker_color = np.where(
            no_squeeze, "blue", np.where(squeeze_on, "black", "gray")
        )

        # --- Save Computed Values ---
        df["upperBB"] = upperBB
        df["lowerBB"] = lowerBB
        df["upperKC"] = upperKC
        df["lowerKC"] = lowerKC
        df["squeeze_on"] = squeeze_on
        df["squeeze_off"] = squeeze_off
        df["no_squeeze"] = no_squeeze
        df["momentum"] = momentum
        df["bar_color"] = bar_color
        df["marker_color"] = marker_color

        self.df = df

    def to_dataframe(
        self,
        start: Optional[Union[str, pd.Timestamp]] = None,
        end: Optional[Union[str, pd.Timestamp]] = None,
    ) -> pd.DataFrame:
        """
        Return the computed indicator data as a DataFrame.

        Parameters:
            start (Optional[str or pd.Timestamp]): Starting date to filter the data.
            end (Optional[str or pd.Timestamp]): Ending date to filter the data.

        Returns:
            pd.DataFrame: DataFrame with momentum values, color assignments, squeeze conditions, and price.
        """
        cols = [
            "momentum",
            "bar_color",
            "marker_color",
            "squeeze_on",
            "squeeze_off",
            "upperBB",
            "lowerBB",
            "upperKC",
            "lowerKC",
        ]
        df = self.df[cols].copy()
        df["price"] = self.hlc["close"]
        if start:
            df = df.loc[start:]
        if end:
            df = df.loc[:end]
        return df

    def plot(
        self,
        start: Optional[Union[str, pd.Timestamp]] = None,
        end: Optional[Union[str, pd.Timestamp]] = None,
    ) -> go.Figure:
        """
        Create an interactive Plotly chart of the Squeeze Momentum indicator.

        The chart includes:
          - A bar trace for the momentum values with dynamic colors.
          - A scatter trace marking the 0-level with colors indicating the squeeze condition.
          - A line trace for price data on a secondary y-axis.

        Parameters:
            start (Optional[str or pd.Timestamp]): Starting date to filter the data.
            end (Optional[str or pd.Timestamp]): Ending date to filter the data.

        Returns:
            go.Figure: A Plotly Figure object.
        """
        df = self.to_dataframe(start=start, end=end)
        if df.empty:
            logger.warning("No data available for the selected date range.")
            return go.Figure()

        fig = go.Figure()

        # --- Price Trace (Secondary Y-Axis) ---
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["price"],
                name="Price",
                line=dict(color="grey", width=2),
                yaxis="y2",
                hovertemplate="Date: %{x|%Y-%m-%d}<br>Price: %{y:.2f}<extra></extra>",
            )
        )

        # --- Bar Trace for Squeeze Momentum ---
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["momentum"],
                marker_color=df["bar_color"],
                name="Squeeze Momentum",
                hovertemplate="Date: %{x|%Y-%m-%d}<br>Momentum: %{y:.2f}<extra></extra>",
            )
        )

        # --- Scatter Trace for 0-Level Marker ---
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=[0] * len(df),
                mode="markers",
                marker=dict(
                    symbol="x",
                    size=5,
                    color=df["marker_color"].tolist(),
                ),
                name="Squeeze Condition",
                hovertemplate="Date: %{x|%Y-%m-%d}<br>Condition Color: %{marker.color}<extra></extra>",
            )
        )

        # --- Layout Configuration ---
        fig.update_layout(
            xaxis=dict(
                title="Date",
                showgrid=True,
                gridcolor="lightgrey",
                type="date",
                range=[df.index.min(), df.index.max()],
            ),
            yaxis=dict(
                title="Squeeze Momentum",
                showgrid=True,
                gridcolor="lightgrey",
            ),
            yaxis2=dict(
                title="Price",
                overlaying="y",
                side="right",
                showgrid=False,
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
            ),
            hovermode="x unified",
            hoverlabel=dict(
                bgcolor="black",
                font=dict(color="white"),
            ),
            margin=dict(l=50, r=50, t=80, b=50),
        )

        return fig
