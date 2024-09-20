import pandas as pd
from ix.core.tech import to_ema
from .base import Indicator


class ATR(Indicator):

    def __init__(self, window: int = 14) -> None:
        self.window = window

    def compute(self, high, low, close) -> "ATR":
        hl = high - low
        hc = (high - close.shift(1)).abs()
        lc = (low - close.shift(1)).abs()
        self.data["tr"] = pd.concat([hl, hc, lc], axis=1).max(axis=1)
        self.data["atr"] = to_ema(self.get_data("tr"), self.window)
        return self


class RSIRange(Indicator):

    def __init__(self, window: int = 14) -> None:

        self.window = window

    def compute(self, close):
        delta = close.diff()
        gain = (
            delta.where(delta > 0, 0).rolling(window=self.window, min_periods=1).mean()
        )
        loss = (
            (-delta.where(delta < 0, 0))
            .rolling(window=self.window, min_periods=1)
            .mean()
        )
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        self.data["rsi"] = rsi
        self.data["bullish"] = (rsi > 20) & (rsi.shift(1) < 20)
        self.data["bearish"] = (rsi < 80) & (rsi.shift(1) > 80)
