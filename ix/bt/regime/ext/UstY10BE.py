import pandas as pd
from ix import db
from .. import Regime


class UstY10BE(Regime):

    TICKERS = {"USGGBE10 Index": "UstY10BE"}
    VOLATILITY_THRESHOLD = 0.15
    DIFF_PERIOD = 3
    INDEX_SHIFT_DAYS = 2

    def fit(self):
        data = db.get_ts(codes=self.TICKERS).resample("ME").last()
        data["Difference"] = data["UstY10BE"].diff(periods=self.DIFF_PERIOD)
        data["States"] = pd.NA
        increasing = data["Difference"] > self.VOLATILITY_THRESHOLD
        decreasing = data["Difference"] <= -self.VOLATILITY_THRESHOLD
        data.loc[increasing, "States"] = "Increasing"
        data.loc[decreasing, "States"] = "Decreasing"
        data["States"] = data["States"].ffill()
        data.index += pd.DateOffset(days=2)
        return data["States"].dropna()
