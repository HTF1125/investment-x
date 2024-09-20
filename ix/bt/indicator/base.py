import pandas as pd


class Indicator:

    data: pd.DataFrame

    def __new__(cls, *args, **kwargs):
        instance = super().__new__(cls)
        instance.data = pd.DataFrame()  # Add empty DataFrame attribute
        return instance

    def compute(self) -> None:
        raise NotImplementedError("Must Implement `compute` method")

    def get_data(self, field: str = "adj_close") -> pd.Series:
        out = self.data[field]
        return out


    def bullish(self) -> pd.Series:
        ...


    def bearish(self) -> pd.Series:
        ...