import pandas as pd
from ix import db
from .. import Regime


class UsIsmPmiManu(Regime):

    TICKERS = {"NAPMPMI Index": "UsIsmPmiManu"}
    SPLIT = 50
    THRESHOLD = 0.5

    def fit(self):
        data = db.get_pxs(codes=self.TICKERS)
        smoothed = data["UsIsmPmiManu"].ewm(span=5).mean().dropna()
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
        data.index += pd.DateOffset(days=2)
        return data["States"].dropna()
