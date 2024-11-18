from typing import Union, overload
import pandas as pd
from ix.core import to_pri_return
from ix.db import get_pxs
from ix import db
from ix import misc


logger = misc.get_logger(__name__)


class Signal:
    def __init__(self) -> None:
        self.code = self.__class__.__name__
        self.db = db.Signal.find_one(db.Signal.code == self.code).run() or db.Signal(
            code=self.code
        )

    def fit(self) -> pd.Series:
        """Override this method to define how the signal is calculated."""
        raise NotImplementedError(f"Must implement `{self.fit.__name__}` method.")

    def refresh(self) -> "Signal":
        """Refreshes the signal data by recalculating and saving to the database."""
        try:
            logger.info("Starting data refresh")
            data = self.fit().dropna().round(2)
            self.db.data = data.to_dict()
            db.Signal.save(self.db)
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
        if not self.db.data:
            self.refresh()
        states = pd.Series(self.db.data)
        states.index = pd.to_datetime(states.index)
        return states.sort_index().rename(self.code)

    def save(self) -> None:
        db.Signal.save(self.db)

    @overload
    def get_performance(
        self,
        px: pd.Series,
        periods: int,
        start: Union[str, None] = None,
    ) -> pd.Series: ...

    @overload
    def get_performance(
        self,
        px: pd.Series,
        periods: list[int],
        start: Union[str, None] = None,
    ) -> pd.DataFrame: ...

    def get_performance(
        self,
        px: pd.Series,
        periods: Union[int, list[int]] = 1,
        start: Union[str, None] = None,
    ) -> Union[pd.Series, pd.DataFrame]:
        performance = get_signal_performances(self.data, px, periods)
        return performance.loc[start:] if start else performance


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
    def fit(
        self,
        ewm_window: int = 50,  # Exponential Moving Average window
        rolling_window: int = 63,  # Rolling window size (quarterly ~252/4)
        lookback_window: int = 252,  # Lookback period for dynamic thresholds
        clip_quantile: float = 0.95,  # Dynamic threshold using quantiles
        scale_factor: float = 2.0,  # Scaling factor for normalization
    ) -> pd.Series:
        # Fetch VIX and SPX returns data
        vix = db.get_pxs(["VIX Index"]).squeeze()
        spx_returns = db.get_pxs(["SPX Index"]).pct_change().squeeze()

        if vix.empty or spx_returns.empty:
            raise ValueError("Required data is missing. Please check the database.")

        # Signal Calculation: VIX Deviation from EMA
        vix_ema = vix.ewm(span=ewm_window).mean()
        signal_raw = vix / vix_ema - 1  # Deviation from EMA

        # Incorporate SPX Returns as an additional signal
        spx_vol = spx_returns.rolling(rolling_window).std()  # Realized volatility
        combined_signal = signal_raw * spx_vol  # Interaction of VIX and realized vol

        # Rolling statistics for z-score calculation
        rolling_stats = combined_signal.rolling(window=rolling_window, min_periods=1)
        rolling_mean = rolling_stats.mean()
        rolling_std = rolling_stats.std()

        # Z-score normalization
        z_score = (combined_signal - rolling_mean) / rolling_std

        # Dynamic Clipping based on quantiles
        lower_clip = z_score.rolling(lookback_window).quantile(1 - clip_quantile)
        upper_clip = z_score.rolling(lookback_window).quantile(clip_quantile)
        z_score = z_score.clip(lower=lower_clip, upper=upper_clip)

        # Apply scaling and smooth the final signal
        smooth_signal = z_score.ewm(span=rolling_window).mean() / scale_factor

        return smooth_signal.fillna(0)


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

        # Short-term smoothing (e.g., rolling mean or EMA)
        smoothed_signal = data.rolling(window=smoothing_window, min_periods=1).mean()

        # Long-term rolling statistics
        long_term_stats = smoothed_signal.rolling(window=rolling_window, min_periods=1)
        long_term_mean = long_term_stats.mean()
        long_term_std = long_term_stats.std()

        # Z-score normalization
        z_score = (smoothed_signal - long_term_mean) / long_term_std

        # Dynamic clipping based on quantiles
        lower_clip = z_score.rolling(lookback_window, min_periods=1).quantile(
            1 - clip_quantile
        )
        upper_clip = z_score.rolling(lookback_window, min_periods=1).quantile(
            clip_quantile
        )
        clipped_signal = z_score.clip(lower=lower_clip, upper=upper_clip)

        # Apply scaling and invert the signal
        scaled_signal = clipped_signal / scale_factor

        # Ensure no NaN values and return the final signal
        return scaled_signal.fillna(0)


class JunkBondDemand(Signal):

    def fit(self) -> pd.Series:
        st = db.get_pxs("SPY").pct_change(20).squeeze()
        bd = db.get_pxs("AGG").pct_change(20).squeeze()
        safe = st - bd
        signal = safe.rolling(10).mean()
        win = 120
        roll = signal.rolling(win)
        mean = roll.mean()
        std = roll.std()
        z = (signal - mean) / std
        z = z.clip(lower=-2.0, upper=2.0) / 2.0
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
        momentum_signal = data / long_term_mean - 1  # Relative deviation from long-term mean

        # Rolling statistics for z-score normalization
        rolling_stats = momentum_signal.rolling(window=zscore_window, min_periods=1)
        rolling_mean = rolling_stats.mean()
        rolling_std = rolling_stats.std()

        # Z-score calculation
        z_score = (momentum_signal - rolling_mean) / rolling_std

        # Dynamic clipping based on rolling quantiles
        lower_clip = z_score.rolling(window=lookback_window, min_periods=1).quantile(1 - clip_quantile)
        upper_clip = z_score.rolling(window=lookback_window, min_periods=1).quantile(clip_quantile)
        clipped_signal = z_score.clip(lower=lower_clip, upper=upper_clip)

        # Smooth the signal and scale
        smoothed_signal = clipped_signal.ewm(span=zscore_window).mean() / scale_factor

        # Ensure no NaN values and return the inverted signal
        return smoothed_signal.fillna(0) * -1


# class UsLargeSmallRatio(Signal):

#     def fit(self) -> pd.Series:
#         large = db.get_pxs("SPY").squeeze()
#         small = db.get_pxs("RTY").squeeze()
#         return large.div(small).dropna()


# class GoldSilverRatio(Signal):

#     def fit(self) -> pd.Series:

#         gold = db.get_pxs("GC=F Comdty").squeeze()
#         silver = db.get_pxs("SI=F Comdty").squeeze()

#         return (gold / silver).dropna()


class EquityBreadth1(Signal):

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

    pri_return = to_pri_return(px=px, periods=periods, forward=True)
    annualized_return = (1 + pri_return) ** (1 / periods) - 1
    signal_shifted = signal.reindex(pri_return.index).ffill().shift(1)
    returns = annualized_return.mul(signal_shifted)

    if commission:
        returns -= signal_shifted.diff(periods).abs() * commission / 10_000 / periods

    return returns.add(1).cumprod().rename(periods)


def all_signals() -> list[type[Signal]]:
    """
    Returns a list of all document models for easy reference in database initialization.
    """
    return [
        UsIsmPmiManu,
        UsOecdLeading,
        EquityVolatility1,
        EquityPutCall1,
        EquityMomentum1,
        EquityBreadth1,
    ]
