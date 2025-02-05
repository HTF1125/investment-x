import pandas as pd
import matplotlib.pyplot as plt
from .bollingerband import BollingerBand
from .rsi import RSI

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


class MACD:
    def __init__(
        self,
        px: pd.Series,
        short_window: int = 12,
        long_window: int = 26,
        signal_window: int = 9,
    ) -> None:
        """
        Initialize the MACD class.

        :param px: Pandas Series of prices (e.g., closing prices).
        :param short_window: Window size for the short EMA (default is 12).
        :param long_window: Window size for the long EMA (default is 26).
        :param signal_window: Window size for the signal line EMA (default is 9).
        """
        if px.empty:
            raise ValueError("The price series (px) must not be empty.")
        if not isinstance(px, pd.Series):
            raise TypeError("The price series (px) must be a pandas Series.")
        if not pd.api.types.is_numeric_dtype(px):
            raise ValueError("The price series (px) must contain numeric data.")

        self.px = px
        self.short_window = short_window
        self.long_window = long_window
        self.signal_window = signal_window
        self.macd_line = self._macd_line()
        self.signal_line = self._signal_line()

    def _macd_line(self) -> pd.Series:
        """
        Calculate the MACD line (short EMA - long EMA).

        :return: Pandas Series of MACD line values.
        """
        short_ema = self.px.ewm(span=self.short_window, adjust=False).mean()
        long_ema = self.px.ewm(span=self.long_window, adjust=False).mean()
        return short_ema - long_ema

    def _signal_line(self) -> pd.Series:
        """
        Calculate the signal line (EMA of MACD line).

        :return: Pandas Series of signal line values.
        """
        return self.macd_line.ewm(span=self.signal_window, adjust=False).mean()

    def to_dataframe(self) -> pd.DataFrame:
        """
        Return the MACD line and signal line as a DataFrame.

        :return: DataFrame with columns for MACD line and signal line.
        """
        return pd.DataFrame(
            {"MACD Line": self.macd_line, "Signal Line": self.signal_line}
        )

    def plot(self, title: str = "MACD", figsize: tuple = (12, 6)) -> None:
        """
        Plot the MACD line and signal line.

        :param title: Title of the plot.
        :param figsize: Size of the plot.
        """
        df = self.to_dataframe()
        plt.figure(figsize=figsize)
        plt.plot(df["MACD Line"], label="MACD Line", color="blue")
        plt.plot(df["Signal Line"], label="Signal Line", color="red")
        plt.axhline(0, color="black", linestyle="--", linewidth=0.5)
        plt.title(title)
        plt.xlabel("Time")
        plt.ylabel("Value")
        plt.legend()
        plt.grid()
        plt.show()


class StochasticOscillator:
    def __init__(self, px: pd.Series, window: int = 14) -> None:
        """
        Initialize the Stochastic Oscillator class.

        :param px: Pandas Series of prices (e.g., closing prices).
        :param window: Window size for calculating the stochastic oscillator.
        """
        if px.empty:
            raise ValueError("The price series (px) must not be empty.")
        if not isinstance(px, pd.Series):
            raise TypeError("The price series (px) must be a pandas Series.")
        if not pd.api.types.is_numeric_dtype(px):
            raise ValueError("The price series (px) must contain numeric data.")

        self.px = px
        self.window = window
        self.k_line = self._k_line()

    def _k_line(self) -> pd.Series:
        """
        Calculate the %K line.

        :return: Pandas Series of %K values.
        """
        lowest_low = self.px.rolling(self.window).min()
        highest_high = self.px.rolling(self.window).max()
        return 100 * (self.px - lowest_low) / (highest_high - lowest_low)

    def to_dataframe(self) -> pd.DataFrame:
        """
        Return the stochastic oscillator %K line as a DataFrame.

        :return: DataFrame with columns for the price and %K line.
        """
        return pd.DataFrame({"Price": self.px, "%K Line": self.k_line})

    def plot(
        self, title: str = "Stochastic Oscillator", figsize: tuple = (12, 6)
    ) -> None:
        """
        Plot the stochastic oscillator %K line.

        :param title: Title of the plot.
        :param figsize: Size of the plot.
        """
        df = self.to_dataframe()
        plt.figure(figsize=figsize)
        plt.plot(df["%K Line"], label="%K Line", color="green")
        plt.axhline(80, color="red", linestyle="--", label="Overbought (80)")
        plt.axhline(20, color="blue", linestyle="--", label="Oversold (20)")
        plt.title(title)
        plt.xlabel("Time")
        plt.ylabel("Value")
        plt.legend()
        plt.grid()
        plt.show()
