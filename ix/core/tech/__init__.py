import pandas as pd
import matplotlib.pyplot as plt


class BollingerBand:
    def __init__(self, px: pd.Series, window: int = 20, n_stds: float = 2.0) -> None:
        """
        Initialize the BollingerBand class.

        :param px: Pandas Series of prices (e.g., closing prices).
        :param window: Rolling window size for calculating the moving average and standard deviation.
        :param n_stds: Number of standard deviations for the upper and lower bands.
        """
        if px.empty:
            raise ValueError("The price series (px) must not be empty.")
        if not isinstance(px, pd.Series):
            raise TypeError("The price series (px) must be a pandas Series.")
        if not pd.api.types.is_numeric_dtype(px):
            raise ValueError("The price series (px) must contain numeric data.")

        self.px = px
        self.window = window
        self.n_stds = n_stds

        self.rolling_std = self.px.rolling(self.window).std()
        self.middle = self.px.rolling(self.window).mean()
        self.upper = self.middle + self.n_stds * self.rolling_std
        self.lower = self.middle - self.n_stds * self.rolling_std

    def to_dataframe(self) -> pd.DataFrame:
        """
        Return the Bollinger Bands as a DataFrame.

        :return: DataFrame with columns for the middle, upper, and lower bands.
        """
        return pd.DataFrame(
            {
                "Price": self.px,
                "Middle Band": self.middle,
                "Upper Band": self.upper,
                "Lower Band": self.lower,
            }
        )

    def plot(self, title: str = "Bollinger Bands", figsize: tuple = (12, 6)) -> None:
        """
        Plot the Bollinger Bands along with the price series.

        :param title: Title of the plot.
        :param figsize: Size of the plot.
        """
        df = self.to_dataframe()
        plt.figure(figsize=figsize)
        plt.plot(df["Price"], label="Px", color="black", linestyle="--")
        plt.plot(df["Middle Band"], label="Middle Band", color="blue")
        plt.plot(df["Upper Band"], label="Upper Band", color="green")
        plt.plot(df["Lower Band"], label="Lower Band", color="red")
        plt.fill_between(
            df.index, df["Upper Band"], df["Lower Band"], color="gray", alpha=0.2
        )
        plt.title(title)
        plt.xlabel("Time")
        plt.ylabel("Price")
        plt.legend()
        plt.grid()
        plt.show()

    def breakout(self) -> pd.Series:
        """
        Detect when the price breaks out of the Bollinger Bands.

        A breakout occurs when:
        - The price crosses above the upper band (price > upper band and price at the previous step <= upper band).
        - The price crosses below the lower band (price < lower band and price at the previous step >= lower band).

        :return: A Pandas Series of True/False values, where True indicates a breakout.
        """
        # Calculate upper and lower breakout conditions
        upper_breakout = (self.px > self.upper) & (
            self.px.shift(1) <= self.upper.shift(1)
        )

        return upper_breakout


class RSI:
    def __init__(self, px: pd.Series, window: int = 14) -> None:
        """
        Initialize the RSI class.

        :param px: Pandas Series of prices (e.g., closing prices).
        :param window: Rolling window size for RSI calculation (default is 14).
        """
        if px.empty:
            raise ValueError("The price series (px) must not be empty.")
        if not isinstance(px, pd.Series):
            raise TypeError("The price series (px) must be a pandas Series.")
        if not pd.api.types.is_numeric_dtype(px):
            raise ValueError("The price series (px) must contain numeric data.")

        self.px = px
        self.window = window
        self.rsi = self._rsi()

    def _rsi(self) -> pd.Series:
        """
        Calculate the RSI (Relative Strength Index).

        RSI = 100 - (100 / (1 + RS)),
        where RS is the average of gains over the average of losses for the rolling window.

        :return: Pandas Series of RSI values.
        """
        delta = self.px.diff(1)
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.rolling(self.window, min_periods=1).mean()
        avg_loss = loss.rolling(self.window, min_periods=1).mean()

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def to_dataframe(self) -> pd.DataFrame:
        """
        Return the RSI values as a DataFrame.

        :return: DataFrame with columns for the price and RSI values.
        """
        return pd.DataFrame({"Price": self.px, "RSI": self.rsi})

    def plot(
        self, title: str = "Relative Strength Index (RSI)", figsize: tuple = (12, 6)
    ) -> None:
        """
        Plot the RSI along with the price series.

        :param title: Title of the plot.
        :param figsize: Size of the plot.
        """
        df = self.to_dataframe()
        plt.figure(figsize=figsize)
        plt.plot(df["RSI"], label=f"RSI({self.window})", color="purple")
        plt.axhline(70, color="red", linestyle="--", label="Overbought (70)")
        plt.axhline(30, color="green", linestyle="--", label="Oversold (30)")
        plt.title(title)
        plt.xlabel("Time")
        plt.ylabel("RSI")
        plt.legend()
        plt.grid()
        plt.show()

    def overbought(self, threshold: float = 70) -> pd.Series:
        """
        Detect when the RSI exceeds the overbought threshold.

        :param threshold: RSI value indicating overbought conditions (default is 70).
        :return: A Pandas Series of True/False values, where True indicates overbought conditions.
        """
        return self.rsi > threshold

    def oversold(self, threshold: float = 30) -> pd.Series:
        """
        Detect when the RSI falls below the oversold threshold.

        :param threshold: RSI value indicating oversold conditions (default is 30).
        :return: A Pandas Series of True/False values, where True indicates oversold conditions.
        """
        return self.rsi < threshold


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
