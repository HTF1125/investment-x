from typing import overload
import pandas as pd

from ix.core import StandardScaler, to_pri_return


class Signal:

    normalize_window: int = 200

    def __init__(self) -> None:
        self.signal = self.compute()
        self.signal.name = f"Signal {self.__class__.__name__}"

    def compute(self) -> pd.Series:
        raise NotImplementedError(f"Must Implement `{self.compute.__name__}` method.")

    def normalize(self) -> pd.Series:
        data = self.compute()
        normalized = (
            data.rolling(self.normalize_window)
            .apply(StandardScaler(lower=-3, upper=3).latest)
            .divide(2)
        )
        return normalized

    @overload
    def get_performance(
        self,
        px: pd.Series,
        periods: int,
        start: str | None = None,
    ) -> pd.Series: ...

    @overload
    def get_performance(
        self,
        px: pd.Series,
        periods: list[int],
        start: str | None = None,
    ) -> pd.DataFrame: ...

    def get_performance(
        self,
        px: pd.Series,
        periods: int | list[int] = 1,
        start: str | None = None,
    ) -> pd.Series | pd.DataFrame:
        performance = get_signal_performances(
            signal=self.signal, px=px, periods=periods
        )
        if start is not None:
            return performance.loc[start:]
        return performance


def get_signal_performances(
    signal: pd.Series,
    px: pd.Series,
    periods: int | list[int] = 1,
    commission: int = 0,
) -> pd.Series | pd.DataFrame:
    if isinstance(periods, list):
        performances = []
        for period in periods:
            performance = get_signal_performances(signal=signal, px=px, periods=period)
            performances.append(performance)
        return pd.concat(performances, axis=1)

    pri_return = to_pri_return(px=px, periods=periods, forward=True)
    pri_return = (1 + pri_return) ** (1 / periods) - 1
    w = signal.reindex(pri_return.index).ffill().shift(1)
    r = pri_return.mul(w)
    if commission:
        r -= w.diff(periods).div(periods).abs() * commission / 10_000
    p = r.add(1).cumprod()
    p.name = periods
    return p
