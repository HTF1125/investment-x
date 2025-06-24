import pandas as pd
import matplotlib.pyplot as plt
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

    def plot(self, title: str = "Moving Average", figsize: tuple = (12, 6)) -> None:
        """
        Plot the moving average along with the price series.

        :param title: Title of the plot.
        :param figsize: Size of the plot.
        """
        df = self.to_dataframe()
        plt.figure(figsize=figsize)
        plt.plot(df["Price"], label="Price", color="black")
        plt.plot(df["MA"], label=f"MA({self.window})", color="blue")
        plt.title(title)
        plt.xlabel("Time")
        plt.ylabel("Price")
        plt.legend()
        plt.grid()
        plt.show()


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

    def plot(
        self, title: str = "Exponential Moving Average", figsize: tuple = (12, 6)
    ) -> None:
        """
        Plot the exponential moving average along with the price series.

        :param title: Title of the plot.
        :param figsize: Size of the plot.
        """
        df = self.to_dataframe()
        plt.figure(figsize=figsize)
        plt.plot(df["Price"], label="Price", color="black")
        plt.plot(df["EMA"], label=f"EMA({self.window})", color="orange")
        plt.title(title)
        plt.xlabel("Time")
        plt.ylabel("Price")
        plt.legend()
        plt.grid()
        plt.show()
