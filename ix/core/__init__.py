""" """

from .tech import *
from .perf import *
from .stat import *

from .bt import *


def to_quantiles(
    x: pd.Series,
    quantiles: int = 5,
    zero_aware: int = 0,
) -> pd.Series:
    if len(x.dropna()) < quantiles:
        return pd.Series(data=None)
    try:
        if zero_aware:
            objs = [
                to_quantiles(x[x >= 0], quantiles=quantiles // 2) + quantiles // 2,
                to_quantiles(x[x < 0], quantiles=quantiles // 2),
            ]
            return pd.concat(objs=objs).sort_index()
        return pd.qcut(x=x, q=quantiles, labels=False) + 1
    except ValueError:
        return pd.Series(data=None)


def sum_to_one(x: pd.Series) -> pd.Series:
    return x / x.sum()


def demeaned(x: pd.Series) -> pd.Series:
    return x - x.mean()


def rebase(x: pd.Series) -> pd.Series:
    return x / x.dropna().iloc[0]


def performance_by_state(
    states: pd.Series,
    pxs: pd.DataFrame,
    demeaned: bool = False,
) -> pd.DataFrame:
    log_return = pxs.apply(to_log_return, axis=0, periods=1, forward=True)
    if demeaned:
        log_return = log_return - log_return.mean(axis=0)
    com = pd.concat([states, log_return], axis=1)
    com["States"] = com["States"].ffill().dropna()
    return com.groupby(by=["States"]).mean() * 252


from ix.misc import ContributionToGrowth
