"""Technical indicators: moving averages, RSI, Bollinger Bands, MACD, regimes."""

import pandas as pd

from .bollinger import *  # noqa: F401,F403
from .rsi import *  # noqa: F401,F403
from .trend import *  # noqa: F401,F403
from .moving_average import *  # noqa: F401,F403
from .regime import *  # noqa: F401,F403


class MovingAverage:
    def __init__(self, px: pd.Series, window: int = 20) -> None:
        if px.empty:
            raise ValueError("The price series (px) must not be empty.")
        if not isinstance(px, pd.Series):
            raise TypeError("The price series (px) must be a pandas Series.")
        if not pd.api.types.is_numeric_dtype(px):
            raise ValueError("The price series (px) must contain numeric data.")

        self.px = px
        self.window = window
        self.ma = self._ma()

    def _ma(self) -> pd.Series:
        return self.px.rolling(self.window).mean()

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame({"Price": self.px, "MA": self.ma})

    def get_plot_data(self) -> dict:
        df = self.to_dataframe()
        return {
            "price": {
                "x": df.index.tolist(),
                "y": df["Price"].tolist(),
                "name": "Price",
                "type": "scatter",
                "mode": "lines",
                "line": {"color": "black"},
            },
            "ma": {
                "x": df.index.tolist(),
                "y": df["MA"].tolist(),
                "name": f"MA({self.window})",
                "type": "scatter",
                "mode": "lines",
                "line": {"color": "blue"},
            },
        }


class ExponentialMovingAverage:
    def __init__(self, px: pd.Series, window: int = 20) -> None:
        if px.empty:
            raise ValueError("The price series (px) must not be empty.")
        if not isinstance(px, pd.Series):
            raise TypeError("The price series (px) must be a pandas Series.")
        if not pd.api.types.is_numeric_dtype(px):
            raise ValueError("The price series (px) must contain numeric data.")

        self.px = px
        self.window = window
        self.ema = self._ema()

    def _ema(self) -> pd.Series:
        return self.px.ewm(span=self.window, adjust=False).mean()

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame({"Price": self.px, "EMA": self.ema})

    def get_plot_data(self) -> dict:
        df = self.to_dataframe()
        return {
            "price": {
                "x": df.index.tolist(),
                "y": df["Price"].tolist(),
                "name": "Price",
                "type": "scatter",
                "mode": "lines",
                "line": {"color": "black"},
            },
            "ema": {
                "x": df.index.tolist(),
                "y": df["EMA"].tolist(),
                "name": f"EMA({self.window})",
                "type": "scatter",
                "mode": "lines",
                "line": {"color": "orange"},
            },
        }
