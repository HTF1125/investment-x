from typing import Dict, Any
import numpy as np
import pandas as pd
from ix import db
from ix.core import to_log_return
from ix.misc import get_logger



logger = get_logger(__name__)


class Regime:

    def load(self):
        try:
            regime = db.Regime.find_one({"code": self.__str__()}).run()
            if regime is not None:
                return regime.data
            return {}
        except:
            return {}

    def dump(self):
        try:
            regime = db.Regime.find_one({"code": self.__str__()}).run()
            if regime is None:
                db.Regime(code=self.__str__(), data=self.data).create()
            else:
                regime.set({"data": self.data})
        except Exception as e:
            msg = "Failed to dump regime to database"
            msg += f"(code = {self.__str__()})"
            msg += "\nMessage : {e}"
            logger.error(msg)

        return self

    def __init__(self) -> None:
        self.data = self.load()

    def __str__(self) -> str:
        return self.__class__.__name__

    def fit(self) -> "Regime":
        raise NotImplementedError("...")

    def get_states(self):
        states = pd.Series(self.data)
        states = states.sort_index()
        states.name = "state"
        states.index.name = "date"
        return states

    def get_state(self, date) -> str:
        state = self.get_states().loc[:date].iloc[-1]
        return state


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
        self.data = data["States"].dropna().to_dict()
        return self


class RealRate(Regime):
    VOLATILITY_THRESHOLD = 0.15
    DIFF_PERIOD = 3
    INDEX_SHIFT_DAYS = 2
    INDEX_SHIFT_MONTHS = 1

    def fit(self) -> "RealRate":
        try:

            code = {"FPRI12MO Index": "RealRate"}
            data = db.get_pxs(code)

            # Calculate signal
            raw_signal = data["RealRate"].diff(self.DIFF_PERIOD).dropna()

            # Determine states
            bins = [
                -float("inf"),
                -self.VOLATILITY_THRESHOLD,
                self.VOLATILITY_THRESHOLD,
                float("inf"),
            ]
            data["States"] = pd.cut(
                raw_signal,
                bins=bins,
                labels=["RealRateDown", None, "RealRateUp"],
            )

            # Forward fill to maintain state continuity
            data["States"] = data["States"].ffill()

            # Shift index
            data.index += pd.DateOffset(days=self.INDEX_SHIFT_DAYS) + pd.DateOffset(
                months=self.INDEX_SHIFT_MONTHS
            )

            # Store results
            self.data = data["States"].dropna().to_dict()

            logger.info("RealRate regime fitting completed successfully")
            return self

        except Exception as e:
            logger.error(f"Error in RealRate regime fitting: {e}")
            raise


class Inflation(Regime):
    VOLATILITY_THRESHOLD = 0.15
    DIFF_PERIOD = 3
    INDEX_SHIFT_DAYS = 2

    def fit(self) -> "Inflation":
        try:
            code = {"USGGBE10 Index": "UsCpiEx10Y"}
            data = db.get_pxs(code).resample("ME").last()

            # Calculate signal
            raw_signal = data["UsCpiEx10Y"].diff(self.DIFF_PERIOD).dropna()

            # Determine states
            bins = [
                -float("inf"),
                -self.VOLATILITY_THRESHOLD,
                self.VOLATILITY_THRESHOLD,
                float("inf"),
            ]
            data["States"] = pd.cut(
                raw_signal,
                bins=bins,
                labels=["InflationDown", None, "InflationUp"],
            )

            # Forward fill to maintain state continuity
            data["States"] = data["States"].ffill()

            # Shift index
            data.index += pd.DateOffset(days=self.INDEX_SHIFT_DAYS)

            # Store results
            self.data = data["States"].dropna().to_dict()

            logger.info("Inflation regime fitting completed successfully")
            return self

        except Exception as e:
            logger.error(f"Error in Inflation regime fitting: {e}")
            raise


class RealRateInflation(Regime):
    def fit(self):
        try:
            # Get states from RealRate and Inflation regimes
            regime1 = RealRate().fit().get_states()
            regime2 = Inflation().fit().get_states()

            # Combine states
            data = pd.concat([regime1, regime2], axis=1)
            data = data.dropna()

            # Join states into a single string
            data = data.apply(lambda row: "_".join(row.dropna().astype(str)), axis=1)

            # Store results
            self.data = data.to_dict()

            logger.info("RealRateInflation regime fitting completed successfully")
            return self
        except Exception as e:
            logger.error(f"Error in RealRateInflation regime fitting: {e}")
            raise


class RealRateInflationUsPmiManu(Regime):
    def fit(self):
        try:
            # Get states from RealRate and Inflation regimes
            regime1 = UsPmiManu().fit().get_states()
            regime2 = RealRateInflation().fit().get_states()

            # Combine states
            data = pd.concat([regime1, regime2], axis=1)
            data = data.dropna()

            # Join states into a single string
            data = data.apply(lambda row: "_".join(row.dropna().astype(str)), axis=1)

            # Store results
            self.data = data.to_dict()

            logger.info("RealRateInflation regime fitting completed successfully")
            return self
        except Exception as e:
            logger.error(f"Error in RealRateInflation regime fitting: {e}")
            raise


class UsOecdLeading(Regime):
    THRESHOLD = 0.0
    EWM_SPAN = 3
    INDEX_SHIFT_DAYS = 2

    def fit(self) -> "UsOecdLeading":
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
                (expanding & uptrending & significant, "Expansion")
            ]

            data["States"] = np.select([cond for cond, _ in conditions],
                                       [state for _, state in conditions],
                                       default=pd.NA)

            # Forward fill states and adjust index
            data["States"] = data["States"].ffill()
            data.index += pd.DateOffset(days=self.INDEX_SHIFT_DAYS)

            # Store results
            self.data = data["States"].dropna().to_dict()

            logger.info("UsOecdLeading regime fitting completed successfully")
            return self

        except Exception as e:
            logger.error(f"Error in UsOecdLeading regime fitting: {e}")
            raise
