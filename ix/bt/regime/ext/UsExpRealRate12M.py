import pandas as pd
from ix import db
from .. import Regime


class UsExpRealRate12M(Regime):

    TICKERS = {"FPRI12MO Index": "UsExpRealRate12M"}
    DIFF_PERIOD = 3
    THRESHOLD = 0.15

    def fit(self):
        data = db.get_ts(codes=self.TICKERS)
        data["Difference"] = data["UsExpRealRate12M"].diff(self.DIFF_PERIOD)
        upward = data["Difference"] >= self.THRESHOLD
        downward = data["Difference"] < self.THRESHOLD
        data["States"] = pd.NA  # Initialize with a default value
        data.loc[upward, "States"] = "Increasing"
        data.loc[downward, "States"] = "Decreasing"
        data["States"] = data["States"].ffill()
        data.index += pd.DateOffset(months=1, days=2)
        return data["States"].dropna()


class UsExpInflation10Y(Regime):
    TICKERS = {"USGGBE10 Index": "UsExpInflation10Y"}
    DIFF_PERIOD = 3
    THRESHOLD = 0.15

    def fit(self):
        data = db.get_ts(codes=self.TICKERS).resample("M").last()
        data["Difference"] = data["UsExpInflation10Y"].diff(self.DIFF_PERIOD)
        upward = data["Difference"] >= self.THRESHOLD
        downward = data["Difference"] < self.THRESHOLD
        data["States"] = pd.NA  # Initialize with a default value
        data.loc[upward, "States"] = "Increasing"
        data.loc[downward, "States"] = "Decreasing"
        data["States"] = data["States"].ffill()
        data.index += pd.DateOffset(days=2)
        return data["States"].dropna()
