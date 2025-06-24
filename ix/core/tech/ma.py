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
        """
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
        self.hlc = pd.DataFrame(
            {"close": self.px_close, "high": self.px_high, "low": self.px_low}
        )

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
        """
        px_close = get_timeseries(code=f"{code}:PX_LAST").data
        px_high = get_timeseries(code=f"{code}:PX_HIGH").data
        px_low = get_timeseries(code=f"{code}:PX_LOW").data

        # Handle missing high/low data
        px_high = px_high if not px_high.empty else None
        px_low = px_low if not px_low.empty else None

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
        """
        if np.isnan(arr).any():
            return np.nan
        x = np.arange(len(arr))
        slope, intercept = np.polyfit(x, arr, 1)
        return intercept + slope * (len(arr) - 1)

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
                hovertemplate="Date: %{x|%Y-%m-%d} Price: %{y:.2f}",
            )
        )

        # --- Bar Trace for Squeeze Momentum ---
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["momentum"],
                marker_color=df["bar_color"],
                name="Squeeze Momentum",
                hovertemplate="Date: %{x|%Y-%m-%d} Momentum: %{y:.2f}",
            )
        )

        # --- Scatter Trace for 0-Level Marker ---
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=[0] * len(df),
                mode="markers",
                marker=dict(symbol="x", size=5, color=df["marker_color"].tolist()),
                name="Squeeze Condition",
                hovertemplate="Date: %{x|%Y-%m-%d} Condition Color: %{marker.color}",
            )
        )

        # --- Layout Configuration ---
        fig.update_layout(
            title={
                "text": "Squeeze Momentum Indicator",
                "x": 0.05,
                "y": 0.95,
                "xanchor": "left",
                "yanchor": "top",
                "font": {"size": 18, "color": "#ffffff"},
            },
            xaxis=dict(
                title="Date",
                showgrid=True,
                gridcolor="lightgrey",
                type="date",
                range=[df.index.min(), df.index.max()],
            ),
            yaxis=dict(title="Squeeze Momentum", showgrid=True, gridcolor="lightgrey"),
            yaxis2=dict(title="Price", overlaying="y", side="right", showgrid=False),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font={"color": "#ffffff"},
            ),
            hovermode="x unified",
            hoverlabel=dict(bgcolor="black", font=dict(color="white")),
            margin=dict(l=50, r=50, t=80, b=50),
            template="plotly_dark",
        )

        return fig



class MACD:
    """
    Moving Average Convergence Divergence (MACD) indicator with Plotly visualisation.
    """

    def __init__(
        self,
        px: pd.Series,
        fast_span: int = 12,
        slow_span: int = 26,
        signal_span: int = 9,
    ) -> None:
        self.px = px.copy()
        self.fast_span = fast_span
        self.slow_span = slow_span
        self.signal_span = signal_span
        self._store: dict = {}
        self.df: pd.DataFrame = pd.DataFrame()
        self._calculate_indicator()

    @classmethod
    def from_meta(
        cls,
        code: str,
        fast_span: int = 12,
        slow_span: int = 26,
        signal_span: int = 9,
    ) -> "MACD":
        px = get_timeseries(code=code).data
        return cls(
            px=px, fast_span=fast_span, slow_span=slow_span, signal_span=signal_span
        )

    # --------------------------- cached properties ------------------------- #
    @property
    def macd_line(self) -> pd.Series:
        if "macd_line" not in self._store:
            ema_fast = self.px.ewm(span=self.fast_span, adjust=False).mean()
            ema_slow = self.px.ewm(span=self.slow_span, adjust=False).mean()
            self._store["macd_line"] = ema_fast - ema_slow
        return self._store["macd_line"]

    @property
    def signal_line(self) -> pd.Series:
        if "signal_line" not in self._store:
            self._store["signal_line"] = self.macd_line.ewm(
                span=self.signal_span, adjust=False
            ).mean()
        return self._store["signal_line"]

    @property
    def histogram(self) -> pd.Series:
        if "histogram" not in self._store:
            self._store["histogram"] = self.macd_line - self.signal_line
        return self._store["histogram"]

    # ----------------------------- core compute ---------------------------- #
    def _calculate_indicator(self) -> None:
        self.df = pd.DataFrame(
            {
                "px": self.px,
                "macd": self.macd_line,
                "signal": self.signal_line,
                "hist": self.histogram,
            }
        )

    # ---------------------------- public helpers --------------------------- #
    def to_dataframe(
        self,
        start: Optional[Union[str, pd.Timestamp]] = None,
        end: Optional[Union[str, pd.Timestamp]] = None,
    ) -> pd.DataFrame:
        df = self.df.copy()
        if start is not None:
            df = df.loc[start:]
        if end is not None:
            df = df.loc[:end]
        return df

    def plot(
        self,
        start: Optional[Union[str, pd.Timestamp]] = None,
        end: Optional[Union[str, pd.Timestamp]] = None,
    ) -> go.Figure:
        df = self.to_dataframe(start=start, end=end)
        if df.empty:
            logger.warning("No data available for the selected date range.")
            return go.Figure()

        hist_color = np.where(
            df["hist"] >= 0,
            np.where(df["hist"].diff() >= 0, "lime", "green"),
            np.where(df["hist"].diff() <= 0, "maroon", "red"),
        )

        fig = go.Figure()

        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["px"],
                name="Price",
                line=dict(color="grey", width=2),
                yaxis="y2",
                hovertemplate="Date: %{x|%Y-%m-%d}<br>Price: %{y:.2f}",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["macd"],
                name="MACD",
                line=dict(color="cyan", width=1.5),
                hovertemplate="MACD: %{y:.4f}",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["signal"],
                name="Signal",
                line=dict(color="orange", width=1.0, dash="dash"),
                hovertemplate="Signal: %{y:.4f}",
            )
        )
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df["hist"],
                name="Histogram",
                marker_color=hist_color,
                hovertemplate="Hist: %{y:.4f}",
            )
        )

        fig.update_layout(
            title=dict(
                text="MACD Indicator",
                x=0.05,
                y=0.95,
                xanchor="left",
                yanchor="top",
                font=dict(size=18, color="#ffffff"),
            ),
            xaxis=dict(
                title="Date",
                showgrid=True,
                gridcolor="lightgrey",
                type="date",
                range=[df.index.min(), df.index.max()],
            ),
            yaxis=dict(title="MACD / Histogram", showgrid=True, gridcolor="lightgrey"),
            yaxis2=dict(title="Price", overlaying="y", side="right", showgrid=False),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                font=dict(color="#ffffff"),
            ),
            hovermode="x unified",
            hoverlabel=dict(bgcolor="black", font=dict(color="white")),
            margin=dict(l=50, r=50, t=80, b=50),
            template="plotly_dark",
        )
        return fig
