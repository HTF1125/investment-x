import numpy as np
import pandas as pd
from ix import db
from ix import misc
from typing import Union

logger = misc.get_logger(__name__)


class Regime:

    @property
    def code(self) -> str:
        return self.__class__.__name__

    def __init__(self) -> None:
        record = db.Regime.find_one(db.Regime.code == self.code).run()
        if record is None:
            record = db.Regime(code=self.code).create()
        self.record = record

    def fit(self) -> pd.Series:
        raise NotImplementedError("Subclasses must implement `fit` method.")

    def refresh(self) -> "Regime":
        """
        Refresh the data by calling fit method, validating the result, and updating the record.

        Raises:
            TypeError: If the data doesn't meet the expected format.
            Exception: For any other unexpected errors during the process.
        """
        try:
            logger.info("Starting data refresh")
            states = self.fit()
            self._validate_states(states)
            self.record.data = states.to_dict()
            self.record.save()
            logger.info(
                f"Data refresh completed successfully. Updated record with {len(states)} entries"
            )
        except TypeError as e:
            logger.error(f"Data validation failed: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during refresh: {str(e)}")
            raise
        return self

    @staticmethod
    def _validate_states(states: pd.Series) -> None:
        if not isinstance(states, pd.Series):
            raise TypeError("States is not a pandas Series")
        if not isinstance(states.index, pd.DatetimeIndex):
            raise TypeError("Index is not a DatetimeIndex")
        if (
            states.dtype != "object"
            or not states.apply(lambda x: isinstance(x, str)).all()
        ):
            raise TypeError("Not all values are strings")
        if states.empty:
            raise TypeError("States Series is empty")
        if not states.index.is_monotonic_increasing:
            raise TypeError("Index is not sorted in ascending order")

    def get_states(self) -> pd.Series:
        if self.__record__.data is None:
            self.refresh()
        states = pd.Series(self.__record__.data)
        states = states.sort_index()
        states.name = "states"
        states.index.name = "date"
        return states

    def get_state(self, date: Union[str, pd.Timestamp]) -> str:
        return self.get_states().loc[:date].iloc[-1]


class UsOecdLeading(Regime):
    THRESHOLD = 0.0
    EWM_SPAN = 3
    INDEX_SHIFT_DAYS = 2

    def fit(self) -> pd.Series:
        try:
            # Fetch data
            code = {"OEUSKLAC Index": "UsOecdLeading"}
            data = db.get_pxs(code)

            # Calculate month-over-month difference and smooth
            data["diff"] = data["UsOecdLeading"].diff()
            pmi = data["diff"].ewm(span=self.EWM_SPAN).mean()

            # Determine states
            expanding = pmi > self.THRESHOLD
            contracting = pmi < self.THRESHOLD
            uptrending = pmi.diff() > 0
            significant = pmi.diff().abs() > self.THRESHOLD

            # Assign states
            conditions = [
                (contracting & ~uptrending & significant, "Contraction"),
                (expanding & ~uptrending & significant, "Slowdown"),
                (contracting & uptrending & significant, "Recovery"),
                (expanding & uptrending & significant, "Expansion"),
            ]

            data["States"] = np.select(
                [cond for cond, _ in conditions],
                [state for _, state in conditions],
                default=pd.NA,
            )

            # Forward fill states and adjust index
            data["States"] = data["States"].ffill()
            data.index += pd.DateOffset(days=self.INDEX_SHIFT_DAYS)

            # Store results
            return data["States"].dropna()


        except Exception as e:
            logger.error(f"Error in UsOecdLeading regime fitting: {e}")
            raise

class UsPmiManu(Regime):

    def fit(self):
        tickers = {"NAPMPMI Index": "IsmUsManuPmi"}
        data = db.get_pxs(tickers)
        pmi = data["IsmUsManuPmi"].ewm(span=5).mean()
        threshhold = 0.5
        expanding = pmi > (50 + threshhold)
        contracting = pmi < (50 - threshhold)
        uptrending = pmi.sub(pmi.shift(1)) > 0
        significant = pmi.sub(pmi.shift(1)).abs() > 0.5
        data = data.dropna()
        data["States"] = pd.NA  # Initialize with a default value
        data.loc[contracting & ~uptrending & significant, "States"] = "Contraction"
        data.loc[expanding & ~uptrending & significant, "States"] = "Slowdown"
        data.loc[contracting & uptrending & significant, "States"] = "Recovery"
        data.loc[expanding & uptrending & significant, "States"] = "Expansion"
        data["States"] = data["States"].ffill()
        data.index += pd.DateOffset(days=2)
        return data["States"].dropna()


class RealRate(Regime):
    VOLATILITY_THRESHOLD = 0.15
    DIFF_PERIOD = 3
    INDEX_SHIFT_DAYS = 2
    INDEX_SHIFT_MONTHS = 1

    def fit(self) -> pd.Series:
        try:
            code: Dict[str, str] = {"FPRI12MO Index": "RealRate"}
            data = db.get_pxs(code)

            # Calculate signal
            raw_signal = data["RealRate"].diff(self.DIFF_PERIOD).dropna()

            # Determine states
            def categorize(x):
                if x < -self.VOLATILITY_THRESHOLD:
                    return "RealRateDown"
                elif x > self.VOLATILITY_THRESHOLD:
                    return "RealRateUp"
                else:
                    return pd.NA

            states = raw_signal.apply(categorize).ffill()

            # Shift index
            shifted_index = states.index + pd.DateOffset(days=self.INDEX_SHIFT_DAYS) + pd.DateOffset(months=self.INDEX_SHIFT_MONTHS)
            states.index = shifted_index

            # Drop NaN values and return
            return states.dropna()

        except Exception as e:
            logger.error(f"Error in RealRate regime fitting: {e}")
            raise

class Inflation(Regime):
    VOLATILITY_THRESHOLD = 0.15
    DIFF_PERIOD = 3
    INDEX_SHIFT_DAYS = 2

    def fit(self) -> pd.Series:
        try:
            code: Dict[str, str] = {"USGGBE10 Index": "UsCpiEx10Y"}
            data = db.get_pxs(code).resample("ME").last()

            # Calculate signal
            raw_signal = data["UsCpiEx10Y"].diff(self.DIFF_PERIOD).dropna()

            # Determine states
            def categorize(x):
                if x < -self.VOLATILITY_THRESHOLD:
                    return "InflationDown"
                elif x > self.VOLATILITY_THRESHOLD:
                    return "InflationUp"
                else:
                    return pd.NA

            states = raw_signal.apply(categorize).ffill()

            # Shift index
            shifted_index = states.index + pd.DateOffset(days=self.INDEX_SHIFT_DAYS)
            states.index = shifted_index

            # Drop NaN values and return
            return states.dropna()

        except Exception as e:
            logger.error(f"Error in Inflation regime fitting: {e}")
            raise
