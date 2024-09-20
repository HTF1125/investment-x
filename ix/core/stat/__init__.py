from typing import Union
import numpy as np
import pandas as pd

from .preprocess import *



def VAR(data: pd.Series, ddof: float = 1.0) -> float:
    return float(np.var(data, ddof=ddof))


def STDEV(data: pd.Series, ddof: float = 1.0) -> float:
    return np.sqrt(VAR(data=data, ddof=ddof))


def ENTP(data: pd.Series, base: float = 2.0) -> float:
    """Entropy (ENTP)

    Introduced by Claude Shannon in 1948, entropy measures the unpredictability
    of the data, or equivalently, of its average information. A die has higher
    entropy (p=1/6) versus a coin (p=1/2).

    Sources:
        https://en.wikipedia.org/wiki/Entropy_(information_theory)
    """
    p = data / data.sum()
    entropy = (-p * np.log(p) / np.log(base)).sum()
    return entropy


def CV(data: pd.Series) -> float:
    return data.std() / data.mean()


def Winsorize(data: pd.Series, lower: float = -3.0, upper: float = 3.0) -> pd.Series:
    return data.clip(lower, upper)


def empirical_cov(
    x1: Union[np.ndarray, pd.Series],
    x2: Union[np.ndarray, pd.Series],
) -> float:
    assert len(x1) == len(x2), "x1 and x2 musth be the same length"
    n = len(x1)
    mean1, mean2 = x1.mean(), x2.mean()
    cov = float(np.sum(((x1 - mean1) * (x2 - mean2)))) / (n - 1)
    return cov
