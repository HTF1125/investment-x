import pandas as pd


class Signal:

    def __init__(self) -> None:

        pass

    @property
    def levels(self) -> pd.Series:
        msg = f"{self.__class__.__name__} has no signal value."
        raise NotImplementedError(msg)

    @property
    def states(self) -> pd.Series:
        msg = f"{self.__class__.__name__} has no states value."
        raise NotImplementedError(msg)


