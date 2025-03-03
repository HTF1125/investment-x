from typing import Optional
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from ix.db.client import get_timeseries  # your custom data loader


class RSI:

    @classmethod
    def from_meta(
        cls,
        code: str,
        window: int = 14,
        overbought: float = 70,
        oversold: float = 30,
        ma_type: str = "None",  # Options: "None", "SMA", "SMA + BBands", "EMA", "SMMA", "WMA", "VWMA"
        ma_length: int = 14,
        bb_std: float = 2.0,
        volume: Optional[pd.Series] = None,
    ) -> "RSI":
        px_last = get_timeseries(code=code, field="PX_LAST")
        if px_last.empty:
            raise ValueError(
                "get_timeseries() returned an empty series for code: " + code
            )
        return cls(
            px_last=px_last,
            window=window,
            overbought=overbought,
            oversold=oversold,
            ma_type=ma_type,
            ma_length=ma_length,
            bb_std=bb_std,
            volume=volume,
        )

    def __init__(
        self,
        px_last: pd.Series,
        window: int = 14,
        overbought: float = 70,
        oversold: float = 30,
        ma_type: str = "None",
        ma_length: int = 14,
        bb_std: float = 2.0,
        volume: Optional[pd.Series] = None,
    ) -> None:
        """
        Initialize the RSI class.

        :param px_last: Pandas Series of prices (e.g., closing prices).
        :param window: Rolling window size for RSI calculation (default is 14).
        :param overbought: RSI value indicating overbought conditions (default is 70).
        :param oversold: RSI value indicating oversold conditions (default is 30).
        :param ma_type: Type of smoothing moving average to apply to RSI. Options:
                        "None", "SMA", "SMA + BBands", "EMA", "SMMA", "WMA", "VWMA".
        :param ma_length: Window length for smoothing moving average (default is 14).
        :param bb_std: BBands standard deviation multiplier (default is 2.0).
        :param volume: Optional Pandas Series of volume data, required for VWMA.
        """
        if px_last.empty:
            raise ValueError("The price series (px_last) must not be empty.")
        if not isinstance(px_last, pd.Series):
            raise TypeError("The price series (px_last) must be a pandas Series.")
        if not pd.api.types.is_numeric_dtype(px_last):
            raise ValueError("The price series (px_last) must contain numeric data.")

        # Ensure the index is a DatetimeIndex if possible (adjust as needed)
        if not isinstance(px_last.index, pd.DatetimeIndex):
            try:
                px_last.index = pd.to_datetime(px_last.index)
            except Exception as e:
                print("Warning: Could not convert index to DatetimeIndex:", e)

        self.px = px_last.astype(float)
        self.window = window
        self.overbought = overbought
        self.oversold = oversold
        self.volume = volume

        # Calculate RSI using Wilder’s smoothing method
        self.rsi = self._rsi()
        self.signals = self._calculate_signals()

        # Smoothing MA options (similar to your Pine Script smoothing section)
        self.ma_type = ma_type
        self.ma_length = ma_length
        self.bb_std = bb_std

        self.smoothed_rsi = None
        self.bb_upper = None
        self.bb_lower = None
        if self.ma_type != "None":
            self.smoothed_rsi = self._calculate_smoothed(
                self.rsi, self.ma_length, self.ma_type
            )
            if self.ma_type == "SMA + BBands":
                # BBands based on RSI standard deviation over the same window
                rsi_std = self.rsi.rolling(window=self.ma_length, min_periods=1).std()
                self.bb_upper = self.smoothed_rsi + rsi_std * self.bb_std
                self.bb_lower = self.smoothed_rsi - rsi_std * self.bb_std

        # Divergence signals will be computed on demand
        self.divergences = None

    def _rsi(self) -> pd.Series:
        """
        Calculate the RSI (Relative Strength Index) using Wilder's smoothing.

        RSI = 100 - (100 / (1 + RS)),
        where RS is the average gain divided by the average loss over the rolling window.

        To avoid having all NaN values for the first few bars, we set min_periods=1.
        """
        delta = self.px.diff(1)
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)

        # Use min_periods=1 so that we get a value even if we don't have a full window
        avg_gain = gain.rolling(window=self.window, min_periods=1).mean()
        avg_loss = loss.rolling(window=self.window, min_periods=1).mean()

        # Apply Wilder's smoothing recursively starting from the "window" index
        avg_gain = avg_gain.copy()
        avg_loss = avg_loss.copy()
        for i in range(self.window, len(self.px)):
            avg_gain.iloc[i] = (
                avg_gain.iloc[i - 1] * (self.window - 1) + gain.iloc[i]
            ) / self.window
            avg_loss.iloc[i] = (
                avg_loss.iloc[i - 1] * (self.window - 1) + loss.iloc[i]
            ) / self.window

        # Avoid division by zero
        rs = avg_gain / avg_loss.replace(0, 1e-10)
        return 100 - (100 / (1 + rs))

    def _calculate_signals(self) -> pd.Series:
        """
        Detect overbought/oversold events based on RSI crossings.
        A signal of 1 indicates a cross above the overbought level,
        while -1 indicates a cross below the oversold level.
        """
        signals = pd.Series(0, index=self.px.index)
        signals[
            (self.rsi > self.overbought) & (self.rsi.shift(1) <= self.overbought)
        ] = 1
        signals[(self.rsi < self.oversold) & (self.rsi.shift(1) >= self.oversold)] = -1
        return signals

    def _calculate_smoothed(
        self, series: pd.Series, length: int, ma_type: str
    ) -> pd.Series:
        """
        Smooth a series using the selected moving average method.
        """
        if ma_type in ["SMA", "SMA + BBands"]:
            return series.rolling(window=length, min_periods=1).mean()
        elif ma_type == "EMA":
            return series.ewm(span=length, adjust=False).mean()
        elif ma_type in ["SMMA", "RMA"]:
            smma = series.copy()
            smma.iloc[0] = series.iloc[:length].mean()
            for i in range(1, len(series)):
                smma.iloc[i] = (
                    smma.iloc[i - 1] * (length - 1) + series.iloc[i]
                ) / length
            return smma
        elif ma_type == "WMA":
            weights = np.arange(1, length + 1)

            def weighted_mean(x):
                if len(x) < length:
                    w = weights[-len(x) :]
                else:
                    w = weights
                return np.dot(x, w) / w.sum()

            return series.rolling(window=length, min_periods=1).apply(
                weighted_mean, raw=True
            )
        elif ma_type == "VWMA":
            if self.volume is None:
                raise ValueError("Volume data is required for VWMA")
            numerator = (
                (series * self.volume).rolling(window=length, min_periods=1).sum()
            )
            denominator = self.volume.rolling(window=length, min_periods=1).sum()
            return numerator / denominator.replace(0, np.nan)
        else:
            raise ValueError(f"Unknown moving average type: {ma_type}")

    def _pivot_low(self, series: pd.Series, left: int, right: int) -> pd.Series:
        """
        Identify pivot lows in a series.
        A pivot low is a bar whose value is lower than the 'left' preceding and 'right' following values.
        """
        pivot = pd.Series(False, index=series.index)
        for i in range(left, len(series) - right):
            window = series.iloc[i - left : i + right + 1]
            if series.iloc[i] == window.min():
                pivot.iloc[i] = True
        return pivot

    def _pivot_high(self, series: pd.Series, left: int, right: int) -> pd.Series:
        """
        Identify pivot highs in a series.
        A pivot high is a bar whose value is higher than the 'left' preceding and 'right' following values.
        """
        pivot = pd.Series(False, index=series.index)
        for i in range(left, len(series) - right):
            window = series.iloc[i - left : i + right + 1]
            if series.iloc[i] == window.max():
                pivot.iloc[i] = True
        return pivot

    def detect_divergences(
        self,
        lookback_left: int = 5,
        lookback_right: int = 5,
        range_lower: int = 5,
        range_upper: int = 60,
    ) -> pd.Series:
        """
        Detect regular bullish and bearish divergences between price and RSI.

        - Bullish Divergence: RSI forms a higher low while price forms a lower low.
        - Bearish Divergence: RSI forms a lower high while price forms a higher high.

        :param lookback_left: Bars to look back for pivot detection.
        :param lookback_right: Bars to look forward for pivot detection.
        :param range_lower: Minimum number of bars between consecutive pivots.
        :param range_upper: Maximum number of bars between consecutive pivots.
        :return: A Series with divergence signals (1 for bullish, -1 for bearish, 0 otherwise).
        """
        # Identify RSI pivots
        pivot_low = self._pivot_low(self.rsi, lookback_left, lookback_right)
        pivot_high = self._pivot_high(self.rsi, lookback_left, lookback_right)

        divergence = pd.Series(0, index=self.rsi.index)

        # Look for bullish divergence (using consecutive pivot lows)
        pivot_low_indices = pivot_low[pivot_low].index
        for i in range(1, len(pivot_low_indices)):
            current_idx = pivot_low_indices[i]
            prev_idx = pivot_low_indices[i - 1]
            current_pos = self.rsi.index.get_loc(current_idx)
            prev_pos = self.rsi.index.get_loc(prev_idx)
            if range_lower <= (current_pos - prev_pos) <= range_upper:
                if (
                    self.rsi[current_idx] > self.rsi[prev_idx]
                    and self.px[current_idx] < self.px[prev_idx]
                ):
                    divergence[current_idx] = 1

        # Look for bearish divergence (using consecutive pivot highs)
        pivot_high_indices = pivot_high[pivot_high].index
        for i in range(1, len(pivot_high_indices)):
            current_idx = pivot_high_indices[i]
            prev_idx = pivot_high_indices[i - 1]
            current_pos = self.rsi.index.get_loc(current_idx)
            prev_pos = self.rsi.index.get_loc(prev_idx)
            if range_lower <= (current_pos - prev_pos) <= range_upper:
                if (
                    self.rsi[current_idx] < self.rsi[prev_idx]
                    and self.px[current_idx] > self.px[prev_idx]
                ):
                    divergence[current_idx] = -1

        self.divergences = divergence
        return divergence

    def to_dataframe(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Return a DataFrame with Price, RSI, signals and optionally smoothed RSI/BBands and divergence signals.

        :param start: (Optional) Starting index label.
        :param end: (Optional) Ending index label.
        :param include_smoothed: Include the smoothed RSI (and BBands if applicable).
        :param include_divergences: Include divergence signals.
        :return: DataFrame with the selected columns.
        """
        df = pd.DataFrame({"Price": self.px, "RSI": self.rsi, "Signals": self.signals})
        if self.smoothed_rsi is not None:
            df["Smoothed RSI"] = self.smoothed_rsi
            if self.ma_type == "SMA + BBands":
                df["BB Upper"] = self.bb_upper
                df["BB Lower"] = self.bb_lower
        if self.divergences is None:
            self.detect_divergences()
        df["Divergences"] = self.divergences

        if start:
            df = df.loc[start:]
        if end:
            df = df.loc[:end]
        return df

    def plot(self, start: Optional[str] = None, end: Optional[str] = None) -> go.Figure:
        """
        Create an interactive Plotly chart displaying:
        - Price (secondary y-axis)
        - RSI (and smoothed RSI if available)
        - BBands if using "SMA + BBands"
        - Overbought/Oversold levels (with shaded regions)
        - Divergence markers
        """
        df = self.to_dataframe(start=start, end=end)

        if df.empty:
            print(
                "Warning: The DataFrame is empty. Check your input data and filtering parameters."
            )
            return go.Figure()  # Return an empty figure

        fig = go.Figure()

        # --- RSI Zone Shading ---
        # Shade the overbought region (RSI above the overbought threshold)
        fig.add_shape(
            type="rect",
            xref="paper",  # span the entire x-axis
            yref="y",
            x0=0,
            x1=1,
            y0=self.overbought,
            y1=100,
            fillcolor="rgba(255, 0, 0, 0.1)",
            line_width=0,
            layer="below",
        )
        # Shade the oversold region (RSI below the oversold threshold)
        fig.add_shape(
            type="rect",
            xref="paper",
            yref="y",
            x0=0,
            x1=1,
            y0=0,
            y1=self.oversold,
            fillcolor="rgba(0, 255, 0, 0.1)",
            line_width=0,
            layer="below",
        )

        # --- Price Trace on Secondary Axis ---
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["Price"],
                name="Price",
                line=dict(color="grey", width=2),
                yaxis="y2",
                hovertemplate="Date: %{x|%Y-%m-%d}<br>Price: %{y:.2f}<extra></extra>",
            )
        )

        # --- RSI Trace ---
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=df["RSI"],
                name="RSI",
                line=dict(color="blue", width=2),
                hovertemplate="Date: %{x|%Y-%m-%d}<br>RSI: %{y:.2f}<extra></extra>",
            )
        )

        # --- Smoothed RSI & BBands (if available) ---
        if "Smoothed RSI" in df.columns:
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=df["Smoothed RSI"],
                    name=f"Smoothed RSI ({self.ma_type})",
                    line=dict(color="orange", width=2, dash="dot"),
                    hovertemplate="Date: %{x|%Y-%m-%d}<br>Smoothed RSI: %{y:.2f}<extra></extra>",
                )
            )
            if (
                self.ma_type == "SMA + BBands"
                and "BB Upper" in df.columns
                and "BB Lower" in df.columns
            ):
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df["BB Upper"],
                        name="BB Upper",
                        line=dict(color="green", width=1, dash="dash"),
                        hovertemplate="Date: %{x|%Y-%m-%d}<br>BB Upper: %{y:.2f}<extra></extra>",
                    )
                )
                fig.add_trace(
                    go.Scatter(
                        x=df.index,
                        y=df["BB Lower"],
                        name="BB Lower",
                        line=dict(color="green", width=1, dash="dash"),
                        fill="tonexty",
                        fillcolor="rgba(0,255,0,0.1)",
                        hovertemplate="Date: %{x|%Y-%m-%d}<br>BB Lower: %{y:.2f}<extra></extra>",
                    )
                )

        # --- Divergence Markers ---
        if "Divergences" in df.columns:
            bull_div = df[df["Divergences"] == 1]
            bear_div = df[df["Divergences"] == -1]
            fig.add_trace(
                go.Scatter(
                    x=bull_div.index,
                    y=bull_div["RSI"],
                    mode="markers",
                    name="Bullish Divergence",
                    marker=dict(symbol="triangle-up", size=12, color="green"),
                    hovertemplate="Date: %{x|%Y-%m-%d}<br>RSI: %{y:.2f}<br>Bullish Divergence<extra></extra>",
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=bear_div.index,
                    y=bear_div["RSI"],
                    mode="markers",
                    name="Bearish Divergence",
                    marker=dict(symbol="triangle-down", size=12, color="red"),
                    hovertemplate="Date: %{x|%Y-%m-%d}<br>RSI: %{y:.2f}<br>Bearish Divergence<extra></extra>",
                )
            )

        # --- Overbought and Oversold Lines ---
        fig.add_hline(
            y=self.overbought,
            line_dash="dash",
            line_color="red",
            annotation_text=f"Overbought ({self.overbought})",
            annotation_font_color="red",
            annotation_position="top left",
        )
        fig.add_hline(
            y=self.oversold,
            line_dash="dash",
            line_color="green",
            annotation_text=f"Oversold ({self.oversold})",
            annotation_font_color="green",
            annotation_position="bottom left",
        )

        # --- Layout and Aesthetics ---
        fig.update_layout(
            xaxis=dict(
                title="Date",
                showgrid=True,
                gridcolor="lightgrey",
                rangeslider=dict(visible=True),
                type="date",
            ),
            yaxis=dict(title="RSI", showgrid=True, gridcolor="lightgrey"),
            yaxis2=dict(title="Price", overlaying="y", side="right", showgrid=False),
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
