from typing import Union, overload
import numpy as np
import pandas as pd
from ix.core import to_log_return
from ix.db import get_pxs
from ix import db
from ix import misc


logger = misc.get_logger(__name__)


class Signal:
    def __init__(self) -> None:
        self.code = f"Signal.{self.__class__.__name__}"
        self.db = db.Ticker.find_one(db.Ticker.code == self.code).run() or db.Ticker(
            code=self.code,
            exchange="Signal",
            source="XXX",
        ).create()
        self.pxlast = db.PxLast.find_one(
            db.PxLast.code == self.code
        ).run() or db.PxLast(
            code=self.code,
        ).create()

    def fit(self) -> pd.Series:
        """Override this method to define how the signal is calculated."""
        raise NotImplementedError(f"Must implement `{self.fit.__name__}` method.")

    def refresh(self) -> "Signal":
        """Refreshes the signal data by recalculating and saving to the database."""
        try:
            logger.info("Starting data refresh")
            data = self.fit().dropna().round(2)
            self.pxlast.data = data.to_dict()
            db.PxLast.save(self.pxlast)
        except TypeError as e:
            logger.error(f"Data validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during refresh: {e}")
            raise
        return self

    @property
    def data(self) -> pd.Series:
        """Fetches the signal from the database, refreshing if not present."""
        if not self.pxlast.data:
            self.refresh()
        states = pd.Series(self.pxlast.data)
        states.index = pd.to_datetime(states.index)
        return states.sort_index().rename(self.code)

    def save(self) -> None:
        db.PxLast.save(self.pxlast)

    def get_performance(
        self,
        long: str,
        short: str | None = None,
        periods: int = 1,
        start: Union[str, None] = None,
        commission: int = 0,
    ) -> Union[pd.Series, pd.DataFrame]:

        l_px = get_pxs(long).squeeze()
        l_pri_return = to_log_return(px=l_px, periods=periods, forward=True)
        l_signal_shifted = self.data.reindex(l_pri_return.index).ffill().shift(1)
        l_returns = l_pri_return.mul(l_signal_shifted)
        if short:
            s_px = get_pxs(short).squeeze()
            s_pri_return = to_log_return(px=s_px, periods=periods, forward=True)
            s_signal_shifted = self.data.reindex(s_pri_return.index).ffill().shift(1)
            s_returns = l_pri_return.mul(-s_signal_shifted)
            l_returns = l_returns - s_returns
        if commission:
            l_returns -= (
                l_signal_shifted.diff(periods).abs() * commission / 10_000 / periods
            )
        return l_returns.div(periods).cumsum().rename(periods)


class UsOecdLeading(Signal):
    def fit(self) -> pd.Series:
        """Calculates the US OECD Leading indicator signal."""
        TICKERS = {"OEUSKLAC Index": "UsOecdLeading"}
        EWM_SPAN = 3
        data = get_pxs(codes=TICKERS).diff().ewm(span=EWM_SPAN).mean().squeeze()
        adjusted_data = data + data.diff()
        adjusted_data.index += pd.DateOffset(days=20)
        return adjusted_data.clip(-0.25, 0.25) * 4


class UsIsmPmiManu(Signal):
    def fit(self) -> pd.Series:
        """Calculates the US ISM PMI Manufacturing indicator signal."""
        TICKERS = {"NAPMPMI Index": "UsIsmPmiManu"}
        EWM_SPAN = 3
        data = get_pxs(codes=TICKERS).sub(50).ewm(span=EWM_SPAN).mean().squeeze()
        adjusted_data = data + data.diff() * 0.2
        adjusted_data.index += pd.DateOffset(days=5)
        return adjusted_data.clip(-10, 10) / 10


class EquityVolatility1(Signal):
    def fit(self) -> pd.Series:
        # Fetch VIX and SPX returns data
        vix = db.get_pxs(["VIX Index"]).squeeze()
        spx_returns = db.get_pxs(["SPX Index"]).pct_change().squeeze()

        if vix.empty or spx_returns.empty:
            raise ValueError("Required data is missing. Please check the database.")

        # Signal Calculation: VIX Deviation from EMA
        vix_ema = vix.ewm(span=50).mean()
        signal_raw = vix / vix_ema - 1  # Deviation from EMA

        # Incorporate SPX Returns as an additional signal
        spx_vol = spx_returns.rolling(60).std()  # Realized volatility
        combined_signal = signal_raw * spx_vol  # Interaction of VIX and realized vol

        # Rolling statistics for z-score calculation
        rolling_stats = combined_signal.rolling(window=60, min_periods=1)
        rolling_mean = rolling_stats.mean()
        rolling_std = rolling_stats.std()

        # Z-score normalization
        z_score = (combined_signal - rolling_mean) / rolling_std

        # Dynamic Clipping based on quantiles
        lower_clip = z_score.rolling(252).quantile(1 - 0.95)
        upper_clip = z_score.rolling(252).quantile(0.95)
        z_score = z_score.clip(lower=lower_clip, upper=upper_clip) / 2

        # Apply scaling and smooth the final signal
        smooth_signal = z_score.ewm(span=60).mean()

        return smooth_signal.dropna()


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
        data = db.get_pxs(codes=["PCRTEQTY Index"]).squeeze()

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
        st = db.get_pxs("SPY").pct_change(lookback_spread).squeeze()
        bd = db.get_pxs("AGG").pct_change(lookback_spread).squeeze()

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
        data = db.get_pxs("SPY").squeeze()

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
        large = db.get_pxs("SPY").squeeze()
        small = db.get_pxs("IWM").squeeze()

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
        signal = db.get_pxs("SUM INX Index").squeeze()
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
        UsOecdLeading,
        EquityBreadth1,
        EquityVolatility1,
        EquityPutCall1,
        EquityMomentum1,
    ]
