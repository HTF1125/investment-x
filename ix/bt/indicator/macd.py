import pandas as pd
from ix.core.tech import to_ema
from ix.bt.indicator.base import Indicator


class MACD(Indicator):

    def __init__(
        self,
        short_window: int = 12,
        long_window: int = 26,
        signal_window: int = 9,
    ) -> None:
        self.short_window = short_window
        self.long_window = long_window
        self.signal_window = signal_window

    def compute(self, close):
        ema1 = to_ema(close, self.short_window)
        ema2 = to_ema(close, self.long_window)
        self.data["macd"] = ema1 - ema2
        self.data["signal"] = to_ema(self.get_data("macd"), self.signal_window)
        self.data["histogram"] = self.get_data("macd") - self.get_data("signal")
        ss = self.data["macd"] - self.data["signal"]
        self.data["bullish"] = (ss < 0) & (ss.shift(1) > 0)
        self.data["bearish"] = (ss > 0) & (ss.shift(1) < 0)

    def bullish(self) -> pd.Series:
        return self.data["bullish"]

    def bearish(self) -> pd.Series:
        return self.data["bearish"]
