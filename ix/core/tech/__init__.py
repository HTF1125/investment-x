import pandas as pd
from .bollingerband import *
from .rsi import *
from .trend import *
from .ma import *
from .regime import *


class MovingAverage:
    def __init__(self, px: pd.Series, window: int = 20) -> None:
        """
        Initialize the MovingAverage class.

        :param px: Pandas Series of prices (e.g., closing prices).
        :param window: Rolling window size for calculating the moving average.
        """
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
        """
        Calculate the moving average.

        :return: Pandas Series of moving average values.
        """
        return self.px.rolling(self.window).mean()

    def to_dataframe(self) -> pd.DataFrame:
        """
        Return the moving average as a DataFrame.

        :return: DataFrame with columns for the price and moving average values.
        """
        return pd.DataFrame({"Price": self.px, "MA": self.ma})

    def get_plot_data(self) -> dict:
        """
        Get data for plotting the moving average along with the price series.
        Returns data that can be used with plotly or other plotting libraries.

        :return: Dictionary containing plot data.
        """
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
    def __init__(
        self,
        px: pd.Series,
        window: int = 20,
    ) -> None:
        """
        Initialize the ExponentialMovingAverage class.

        :param px: Pandas Series of prices (e.g., closing prices).
        :param window: Window size for calculating the exponential moving average.
        """
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
        """
        Calculate the exponential moving average.

        :return: Pandas Series of exponential moving average values.
        """
        return self.px.ewm(span=self.window, adjust=False).mean()

    def to_dataframe(self) -> pd.DataFrame:
        """
        Return the exponential moving average as a DataFrame.

        :return: DataFrame with columns for the price and EMA values.
        """
        return pd.DataFrame({"Price": self.px, "EMA": self.ema})

    def get_plot_data(self) -> dict:
        """
        Get data for plotting the exponential moving average along with the price series.
        Returns data that can be used with plotly or other plotting libraries.

        :return: Dictionary containing plot data.
        """
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
