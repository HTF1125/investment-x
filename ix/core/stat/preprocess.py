# Robert Han


import pandas as pd


class BaseScaler:
    """
    Base class for scaling numerical data.
    """

    def __init__(
        self,
        mean: float | None = None,
        lower: float | None = None,
        upper: float | None = None,
    ) -> None:
        """
        Initialize the scaler.

        Parameters:
            mean (float, optional): Mean value for scaling. Defaults to None.
            lower (float, optional): Lower bound for scaling. Defaults to None.
            upper (float, optional): Upper bound for scaling. Defaults to None.
        """
        self.mean = mean
        self.lower = lower
        self.upper = upper

    def compute(self, data: pd.Series) -> pd.Series:
        """
        Compute scaling for the given data.

        Parameters:
            data (pd.Series): The input data to be scaled.

        Returns:
            pd.Series: Scaled data.
        """
        method = self.compute.__name__
        raise NotImplementedError(f"Must implement `{method}` method.")

    def latest(self, data: pd.Series) -> float:
        """
        Compute the latest scaled value for the given data.

        Parameters:
            data (pd.Series): The input data.

        Returns:
            float: Latest scaled value.
        """
        if data.empty:
            raise ValueError("Input data is empty.")

        scaled_data = self.compute(data)
        latest_value = scaled_data.iloc[-1] if not scaled_data.empty else 0

        return min(max(latest_value, self.lower or float('-inf')), self.upper or float('inf'))


class StandardScaler(BaseScaler):
    """
    StandardScaler class for standardization of data.
    """

    def compute(self, data: pd.Series) -> pd.Series:
        """
        Compute standard scaling for the given data.

        Parameters:
            data (pd.Series): The input data to be standardized.

        Returns:
            pd.Series: Standardized data.
        """
        if data.empty:
            raise ValueError("Input data is empty.")

        mean = self.mean if self.mean is not None else data.mean()
        std_dev = data.std()

        if std_dev == 0:
            raise ValueError("Standard deviation is zero.")

        return (data - mean) / std_dev


class RobustScaler(BaseScaler):
    """
    RobustScaler class for robust scaling of data.
    """

    def compute(self, data: pd.Series) -> pd.Series:
        """
        Compute robust scaling for the given data.

        Parameters:
            data (pd.Series): The input data to be scaled.

        Returns:
            pd.Series: Scaled data.
        """
        if data.empty:
            raise ValueError("Input data is empty.")

        quantile1 = data.quantile(q=0.25)
        quantile3 = data.quantile(q=0.75)
        median = self.mean if self.mean is not None else data.median()

        if quantile3 - quantile1 == 0:
            raise ValueError("Interquartile range is zero.")

        return (data - median) / (quantile3 - quantile1)


class MinMaxScaler(BaseScaler):
    """
    MinMaxScaler class for min-max scaling of data.
    """

    def compute(self, data: pd.Series) -> pd.Series:
        """
        Compute min-max scaling for the given data.

        Parameters:
            data (pd.Series): The input data to be scaled.

        Returns:
            pd.Series: Scaled data.
        """
        if data.empty:
            raise ValueError("Input data is empty.")

        minimum, maximum = data.min(), data.max()

        if minimum == maximum:
            raise ValueError("Minimum and maximum values are the same.")

        return (data - minimum) / (maximum - minimum)
