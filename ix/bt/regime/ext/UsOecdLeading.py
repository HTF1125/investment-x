import pandas as pd
from ix import db
from .. import Regime


class UsOecdLeading(Regime):

    TICKERS = {"OEUSKLAC Index": "UsOecdLeading"}
    EWM_SPAN = 3
    SPLIT = 0
    THRESHOLD = 0

    def fit(self):
        data = db.get_ts(codes=self.TICKERS)
        data["Difference"] = data["UsOecdLeading"].diff()
        smoothed = data["Difference"].ewm(span=self.EWM_SPAN).mean()
        expanding = smoothed > (self.SPLIT + self.THRESHOLD)
        contracting = smoothed < (self.SPLIT - self.THRESHOLD)
        uptrending = smoothed.sub(smoothed.shift(1)) > 0
        significant = smoothed.sub(smoothed.shift(1)).abs() > self.THRESHOLD
        data["States"] = pd.NA  # Initialize with a default value
        data.loc[contracting & ~uptrending & significant, "States"] = "Contraction"
        data.loc[expanding & ~uptrending & significant, "States"] = "Slowdown"
        data.loc[contracting & uptrending & significant, "States"] = "Recovery"
        data.loc[expanding & uptrending & significant, "States"] = "Expansion"
        data["States"] = data["States"].ffill()
        data.index += pd.DateOffset(days=20)
        return data["States"].dropna()
