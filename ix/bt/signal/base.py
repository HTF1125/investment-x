from typing import Union
import numpy as np
import pandas as pd
from ix.core import to_log_return
from ix.db import get_ts, get_px_last
from ix import db
from ix import misc
from ix.db import Metadata
import matplotlib.pyplot as plt

logger = misc.get_logger(__name__)


class Signal:
    def __init__(self) -> None:
        code = f"{self.__class__.__name__}"
        self.metadata = (
            Metadata.find_one({"code" : code}).run()
            or Metadata(code=code).create()
        )

    def fit(self) -> pd.Series:
        """Override this method to define how the signal is calculated."""
        raise NotImplementedError(f"Must implement `{self.fit.__name__}` method.")

    def refresh(self) -> "Signal":
        """Refreshes the signal data by recalculating and saving to the database."""
        logger.info("Starting data refresh")
        data = self.fit().dropna().round(2)
        self.metadata.ts(field="PX_LAST").data = data
        return self

    @property
    def data(self) -> pd.Series:
        """Fetches the signal from the database, refreshing if not present."""
        data = self.metadata.ts(field="PX_LAST").data
        if data.empty:
            self.refresh()
        data.name = self.metadata.code
        return data

    def get_performance(
        self,
        long: str | None = None,
        short: str | None = None,
        periods: int = 1,
        commission: int = 0,
    ) -> Union[pd.Series, pd.DataFrame]:

        if not long and not short:
            raise ValueError("both long and short could not be none.")
        if long:
            l_px = get_px_last([long]).squeeze()
            l_pri_return = to_log_return(px=l_px, periods=periods, forward=True)
            l_signal_shifted = self.data.reindex(l_pri_return.index).ffill().shift(1)
            l_returns = l_pri_return.mul(l_signal_shifted)
        else:
            l_returns = 0
        if short:
            s_px = get_px_last([short]).squeeze()
            s_pri_return = to_log_return(px=s_px, periods=periods, forward=True)
            s_signal_shifted = self.data.reindex(s_pri_return.index).ffill().shift(1)
            s_returns = s_pri_return.mul(-s_signal_shifted)
        else:
            s_returns = 0

        returns = l_returns + s_returns
        if commission:
            returns -= (
                l_signal_shifted.diff(periods).abs() * commission / 10_000 / periods
            )
        assert isinstance(returns, pd.Series)
        return returns.div(periods).cumsum().rename(periods)

    def plot(
        self,
        long: str | None = None,
        short: str | None = None,
        periods: int = 1,
        commission: int = 0,
    ) -> None:
        """
        Plots the signal data and its performance with dual y-axes,
        more transparent tone, improved design, and clarity.
        """
        # Get the signal data
        signal_data = self.data

        # Get the performance data
        performance_data = self.get_performance(
            long=long, short=short, periods=periods, commission=commission
        )

        # Create a plot with dual y-axes
        fig, ax1 = plt.subplots(figsize=(12, 6))

        # Plot signal data on the left y-axis
        ax1.set_xlabel("Date", fontsize=12)
        ax1.set_ylabel("Signal Data", color="tab:blue", fontsize=12)
        ax1.plot(
            signal_data.index,
            signal_data,
            color="tab:blue",
            label="Signal Data",
            linewidth=2,
            alpha=0.9,
        )
        ax1.fill_between(
            signal_data.index, signal_data, color="tab:blue", alpha=0.2
        )  # Light fill under signal
        ax1.tick_params(axis="y", labelcolor="tab:blue")

        # Plot performance on the right y-axis
        ax2 = ax1.twinx()
        ax2.set_ylabel("Performance", color="tab:green", fontsize=12)
        ax2.plot(
            performance_data.index,
            performance_data,
            color="tab:green",
            label="Performance",
            linestyle="--",
            linewidth=2,
            alpha=0.9,
        )
        ax2.fill_between(
            performance_data.index, performance_data, color="tab:green", alpha=0.1
        )  # Light fill under performance
        ax2.tick_params(axis="y", labelcolor="tab:green")

        # Title and grid settings
        plt.title(f"{self.metadata.code} Signal and Performance", fontsize=14)
        ax1.grid(
            True, which="both", axis="both", linestyle="--", linewidth=0.5, alpha=0.7
        )  # Subtle gridlines

        # Add a legend with custom location
        ax1.legend(loc="upper left", fontsize=10)
        ax2.legend(loc="upper right", fontsize=10)

        # Layout adjustments for better spacing
        plt.tight_layout()

        # Show the plot
        plt.show()


class OecdCliUsChg1(Signal):
    def fit(self) -> pd.Series:
        """
        Generates an investment signal based on the OECD US Composite Leading Indicator.

        The signal ranges between -1 and 1:
            - 1: Strong Long (Buy)
            - -1: Strong Short (Sell)
            - 0: Neutral

        Returns:
            pd.Series: The investment signal series.
        """
        # Define constants within the fit method
        EWM_SPAN: int = 3  # Span for EWMA
        DATE_SHIFT_DAYS: int = 20  # Days to shift the signal forward
        CLIP_RANGE_INITIAL: tuple = (-2, 2)  # Initial clipping range before scaling
        SCALE_FACTOR: float = 0.5  # Factor to scale the clipped signal
        raw_data = get_px_last(codes=["^OEUSKLAC"]).squeeze().ewm(span=EWM_SPAN).mean()
        raw_data.name = "OecdCliUs"
        roc_data = raw_data.diff().dropna()
        roroc_data = roc_data.diff().dropna()
        roc_mean = roc_data.expanding().mean().shift(1)
        roc_std = roc_data.expanding().std().shift(1).replace(0, 1)
        roc_normalized = (roc_data - roc_mean) / roc_std
        roroc_mean = roroc_data.expanding().mean().shift(1)
        roroc_std = roroc_data.expanding().std().shift(1).replace(0, 1)
        roroc_normalized = (roroc_data - roroc_mean) / roroc_std
        combined_signal = roc_normalized.add(roroc_normalized, fill_value=0)
        combined_signal = combined_signal.reindex(roc_normalized.index).fillna(0)
        clipped_signal = combined_signal.clip(*CLIP_RANGE_INITIAL)
        scaled_signal = clipped_signal * SCALE_FACTOR
        normalized_signal = scaled_signal.clip(-1, 1)
        shifted_signal = normalized_signal.shift(periods=DATE_SHIFT_DAYS, freq="D")
        shifted_signal = shifted_signal.fillna(0)
        return shifted_signal


class UsIsmPmiManu(Signal):
    def fit(self) -> pd.Series:
        """Calculates the US ISM PMI Manufacturing indicator signal."""
        EWM_SPAN: int = 3  # Span for EWMA
        DATE_SHIFT_DAYS: int = 20  # Days to shift the signal forward
        CLIP_RANGE_INITIAL: tuple = (-2, 2)  # Initial clipping range before scaling
        SCALE_FACTOR: float = 0.5  # Factor to scale the clipped signal
        raw_data = get_px_last(["^NAPMPMI"]).squeeze().ewm(span=EWM_SPAN).mean()
        raw_data.name = "UsIsmPmiManu"
        roc_data = raw_data.diff().dropna()
        roroc_data = roc_data.diff().dropna()
        roc_mean = roc_data.expanding().mean().shift(1)
        roc_std = roc_data.expanding().std().shift(1).replace(0, 1)
        roc_normalized = (roc_data - roc_mean) / roc_std
        roroc_mean = roroc_data.expanding().mean().shift(1)
        roroc_std = roroc_data.expanding().std().shift(1).replace(0, 1)
        roroc_normalized = (roroc_data - roroc_mean) / roroc_std
        combined_signal = roc_normalized.add(roroc_normalized, fill_value=0)
        combined_signal = combined_signal.reindex(roc_normalized.index).fillna(0)
        clipped_signal = combined_signal.clip(*CLIP_RANGE_INITIAL)
        scaled_signal = clipped_signal * SCALE_FACTOR
        normalized_signal = scaled_signal.clip(-1, 1)
        shifted_signal = normalized_signal.shift(periods=DATE_SHIFT_DAYS, freq="D")
        shifted_signal = shifted_signal.fillna(0)
        return shifted_signal


class EquityVolatility1(Signal):
    def fit(self) -> pd.Series:
        # Fetch VIX and SPX returns data
        vix = db.get_px_last(["VIX Index"]).squeeze()
        gix = db.get_px_last(["SPX Index"]).pct_change().squeeze().rolling(20).std()

        if vix.empty or gix.empty:
            raise ValueError("Required data is missing. Please check the database.")

        # Signal Calculation: VIX Deviation from EMA
        vix_ema = vix.ewm(span=20).mean()
        gix_ema = gix.ewm(span=20).mean()
        signalv = vix / vix_ema
        signalg = gix / gix_ema

        # Incorporate SPX Returns as an additional signal
        combined_signal = signalv / signalg
        return combined_signal.clip(0.75, 1.25).sub(1).mul(4).dropna()


class EquityPutCall1(Signal):
    def fit(
        self,
        smoothing_window: int = 20,  # Window for short-term smoothing
        rolling_window: int = 200,  # Long-term rolling window
        lookback_window: int = 252,  # Lookback period for dynamic clipping
        clip_quantile: float = 0.95,  # Quantile for dynamic thresholds
        scale_factor: float = 2.0,  # Scaling factor for normalization
    ) -> pd.Series:
        # Fetch data for Put-Call Ratio
        data = get_px_last(codes=["^PCRTEQTY"]).squeeze()

        if data.empty:
            raise ValueError("Put-Call Ratio data is empty. Please check the database.")

        # Ensure data is sorted by time to prevent accidental look-ahead bias
        data = data.sort_index()

        # Short-term smoothing (e.g., rolling mean or EMA)
        smoothed_signal = data.rolling(window=smoothing_window, min_periods=1).mean()

        # Use expanding windows to avoid look-ahead bias for mean and std
        expanding_mean = smoothed_signal.expanding().mean()
        expanding_std = smoothed_signal.expanding().std()

        # Z-score normalization with only past data
        z_score = (smoothed_signal - expanding_mean) / expanding_std

        # Dynamic clipping based on quantiles (use a trailing rolling window)
        lower_clip = z_score.rolling(
            lookback_window, min_periods=1, center=False
        ).quantile(1 - clip_quantile)
        upper_clip = z_score.rolling(
            lookback_window, min_periods=1, center=False
        ).quantile(clip_quantile)
        clipped_signal = z_score.clip(lower=lower_clip, upper=upper_clip)

        # Apply scaling and invert the signal
        scaled_signal = (clipped_signal - 1) / scale_factor

        # Ensure no NaN values and return the final signal
        return scaled_signal.fillna(0)


class JunkBondDemand(Signal):
    def fit(self) -> pd.Series:
        """
        Calculate the junk bond demand signal using spread-based z-score methodology.

        Returns:
            pd.Series: A z-score-based signal, clipped and inverted.
        """
        # Configurable parameters
        lookback_spread = 20  # Lookback period for spread calculation
        rolling_mean_window = 10  # Rolling mean window for the spread
        zscore_window = 120  # Rolling window for z-score calculation
        zscore_clip = 2.0  # Clipping threshold for z-score

        # Get percentage change data
        st = get_px_last(["SPY"]).pct_change(lookback_spread).squeeze()
        bd = get_px_last(["AGG"]).pct_change(lookback_spread).squeeze()

        # Validate data
        if st.empty or bd.empty:
            raise ValueError("Price data for SPY or AGG is empty or invalid.")

        # Calculate the safety spread
        safe_spread = st - bd

        # Compute the signal as the rolling mean of the spread
        signal = safe_spread.rolling(rolling_mean_window).mean()

        # Calculate rolling statistics for z-score
        roll = signal.rolling(zscore_window)
        mean = roll.mean()
        std = roll.std()

        # Handle cases where standard deviation is zero
        std = std.replace(0, np.nan)

        # Calculate the z-score and clip it
        z = (signal - mean) / std
        z = z.clip(lower=-zscore_clip, upper=zscore_clip) / zscore_clip

        # Return the inverse of the z-score
        return z * -1


class EquityMomentum1(Signal):
    def fit(
        self,
        rolling_mean_window: int = 125,  # Window for long-term rolling mean
        zscore_window: int = 120,  # Window for rolling mean/std in z-score
        lookback_window: int = 252,  # Lookback period for dynamic thresholds
        clip_quantile: float = 0.95,  # Quantile for dynamic thresholds
        scale_factor: float = 2.0,  # Scaling factor for normalization
    ) -> pd.Series:
        # Fetch SPY price data
        data = get_px_last(["SPY"]).squeeze()

        if data.empty:
            raise ValueError("SPY price data is empty. Please check the database.")

        # Calculate long-term momentum signal
        long_term_mean = data.rolling(window=rolling_mean_window, min_periods=1).mean()
        momentum_signal = (
            data / long_term_mean - 1
        )  # Relative deviation from long-term mean

        # Rolling statistics for z-score normalization
        rolling_stats = momentum_signal.rolling(window=zscore_window, min_periods=1)
        rolling_mean = rolling_stats.mean()
        rolling_std = rolling_stats.std()

        # Z-score calculation
        z_score = (momentum_signal - rolling_mean) / rolling_std

        # Dynamic clipping based on rolling quantiles
        lower_clip = z_score.rolling(window=lookback_window, min_periods=1).quantile(
            1 - clip_quantile
        )
        upper_clip = z_score.rolling(window=lookback_window, min_periods=1).quantile(
            clip_quantile
        )
        clipped_signal = z_score.clip(lower=lower_clip, upper=upper_clip)

        # Smooth the signal and scale
        smoothed_signal = clipped_signal.ewm(span=zscore_window).mean() / scale_factor

        # Ensure no NaN values and return the inverted signal
        return smoothed_signal.fillna(0) * -1


class UsLargeSmallRatio(Signal):

    def fit(self) -> pd.Series:
        """
        Calculate the z-score of the ratio of US large-cap (SPY) to global small-cap (ACWI).

        Returns:
            pd.Series: A z-score-based signal for the SPY/ACWI ratio, clipped and normalized.
        """
        # Configurable parameters
        rolling_mean_window = 10  # Rolling mean window for the ratio
        zscore_window = 120  # Rolling window for z-score calculation
        zscore_clip = 2.0  # Clipping threshold for z-score

        # Fetch price series for large-cap (SPY) and small-cap (ACWI)
        large = get_px_last(["SPY"]).squeeze()
        small = get_px_last(["IWM"]).squeeze()

        # Validate data
        if large.empty or small.empty:
            raise ValueError("Price data for SPY or ACWI is empty or invalid.")

        # Calculate the ratio
        ratio = large.div(small)

        # Compute the signal as the rolling mean of the ratio
        signal = ratio.rolling(rolling_mean_window).mean()

        # Calculate rolling statistics for z-score
        roll = signal.rolling(zscore_window)
        mean = roll.mean()
        std = roll.std()

        # Handle cases where standard deviation is zero
        std = std.replace(0, np.nan)

        # Calculate the z-score and clip it
        z = (signal - mean) / std
        z = z.clip(lower=-zscore_clip, upper=zscore_clip) / zscore_clip

        # Return the z-score
        return z


class EquityBreadth1(Signal):

    assets = {"SUM INX Index": "SP500MarketBreadth"}
    lookback_window: int = 120

    def fit(self) -> pd.Series:
        signal = get_px_last(["^SUM_INX"]).squeeze()
        roll = signal.rolling(120)
        mean = roll.mean()
        std = roll.std()
        z = (signal - mean) / std
        z = z.clip(lower=-2.0, upper=2.0) / 2.0
        return z * (-1)


def get_signal_performances(
    signal: pd.Series,
    px: pd.Series,
    periods: Union[int, list[int]] = 1,
    commission: int = 0,
) -> Union[pd.Series, pd.DataFrame]:
    """
    Calculate the performance of the signal over given periods.

    Args:
        signal (pd.Series): Signal values.
        px (pd.Series): Price data for the assets.
        periods (int | list[int]): Look-back periods for performance calculation.
        commission (int): Commission percentage in basis points.

    Returns:
        pd.Series | pd.DataFrame: Performance for each period.
    """
    if isinstance(periods, list):
        return pd.concat(
            [
                get_signal_performances(signal, px, period, commission)
                for period in periods
            ],
            axis=1,
        )

    pri_return = to_log_return(px=px, periods=periods, forward=True)
    signal_shifted = signal.reindex(pri_return.index).ffill().shift(1)
    returns = pri_return.mul(signal_shifted)

    if commission:
        returns -= signal_shifted.diff(periods).abs() * commission / 10_000 / periods
    return returns.cumsum().rename(periods)


def all_signals() -> list[type[Signal]]:
    """
    Returns a list of all document models for easy reference in database initialization.
    """
    return [
        UsIsmPmiManu,
        OecdCliUsChg1,
        EquityBreadth1,
        EquityVolatility1,
        EquityPutCall1,
        EquityMomentum1,
    ]
