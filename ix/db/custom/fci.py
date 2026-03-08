from __future__ import annotations

import pandas as pd

from ix.db.query import Series
from ix.core.transforms import StandardScalar


def fci_us() -> pd.Series:
    """US Financial Conditions Index (weekly)."""
    fci = pd.concat(
        [
            StandardScalar(-Series("DXY Index:PX_LAST", freq="W"), 4 * 6),
            StandardScalar(-Series("TRYUS10Y:PX_YTM", freq="W"), 4 * 6),
            StandardScalar(-Series("TRYUS30Y:PX_YTM", freq="W"), 4 * 6),
            StandardScalar(Series("SPX Index:PX_LAST", freq="W"), 4 * 6),
            StandardScalar(-Series("MORTGAGE30US", freq="W"), 4 * 6),
            StandardScalar(-Series("CL1 Comdty:PX_LAST", freq="W"), 4 * 6),
            StandardScalar(-Series("BAMLC0A0CM", freq="W"), 4 * 6),
        ],
        axis=1,
    ).mean(axis=1).ewm(span=4 * 12).mean()
    fci.index = pd.to_datetime(fci.index)
    fci = fci.sort_index()
    fci.name = "Financial Conditions US"
    return fci


def fci_kr() -> pd.Series:
    """Korea Financial Conditions Index (weekly)."""
    fci = pd.concat(
        [
            StandardScalar(-Series("USDKRW Curncy:PX_LAST", freq="W"), 4 * 6),
            StandardScalar(-Series("TRYKR10Y:PX_YTM", freq="W"), 4 * 6),
            StandardScalar(-Series("TRYKR30Y:PX_YTM", freq="W"), 4 * 6),
            StandardScalar(Series("KOSPI Index:PX_LAST", freq="W"), 4 * 6),
        ],
        axis=1,
    ).mean(axis=1).ewm(span=4 * 12).mean()
    fci.name = "Financial Conditions KR"
    return fci


def fci_stress() -> pd.Series:
    """Financial stress indicator from vol and credit spreads."""
    series = [
        StandardScalar(Series("VIX Index:PX_LAST"), 160),
        StandardScalar(Series("MOVE Index:PX_LAST"), 160),
        StandardScalar(Series("BAMLH0A0HYM2"), 160),
        StandardScalar(Series("BAMLC0A0CM"), 160),
    ]
    result = pd.concat(series, axis=1).ffill().mean(axis=1)
    result.name = "Financial Stress"
    return result


# Backward-compatible aliases
def FinancialConditionsIndexUS() -> pd.Series:
    return fci_us()


def financial_conditions_us() -> pd.Series:
    return fci_us()


def FinancialConditionsKR() -> pd.Series:
    return fci_kr()


def FinancialConditionsIndex1() -> pd.Series:
    return fci_stress()
