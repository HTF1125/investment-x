from __future__ import annotations

import pandas as pd

from ix.core.transforms import daily_ffill


LOCAL_INDICES_CODES = {
    "SP500": "SPX Index:PX_LAST",
    "DJIA30": "INDU Index:PX_LAST",
    "NASDAQ": "CCMP Index:PX_LAST",
    "Russell2": "RTY Index:PX_LAST",
    "Stoxx50": "SX5E Index:PX_LAST",
    "FTSE100": "UKX Index:PX_LAST",
    "DAX": "DAX Index:PX_LAST",
    "CAC": "CAC Index:PX_LAST",
    "Nikkei225": "NKY Index:PX_LAST",
    "TOPIX": "TPX Index:PX_LAST",
    "KOSPI": "KOSPI Index:PX_LAST",
    "NIFTY": "NIFTY Index:PX_LAST",
    "HangSeng": "HSI Index:PX_LAST",
    "SSE": "SHCOMP Index:PX_LAST",
}


def local_indices_performance() -> pd.DataFrame:
    """Level, 1D, 1W, 1M, 3M, 1Y, YTD performance table."""
    from ix.db import get_timeseries

    series_list = []
    for name, ticker in LOCAL_INDICES_CODES.items():
        ts = get_timeseries(ticker).data
        ts.name = name
        series_list.append(ts)

    datas = pd.concat(series_list, axis=1)
    datas = daily_ffill(datas)

    today = datas.index[-1]
    start_year = pd.Timestamp(year=today.year, month=1, day=1)
    one_month = today - pd.DateOffset(months=1)
    three_mo = today - pd.DateOffset(months=3)
    one_year = today - pd.DateOffset(years=1)

    def pct_from(base_date):
        base = datas.asof(base_date)
        return (datas.iloc[-1] / base - 1).round(4) * 100

    output = [
        datas.iloc[-1].round(2).rename("Level"),
        pct_from(today - pd.DateOffset(days=1)).rename("1D"),
        pct_from(today - pd.DateOffset(days=7)).rename("1W"),
        pct_from(one_month).rename("1M"),
        pct_from(three_mo).rename("3M"),
        pct_from(one_year).rename("1Y"),
        pct_from(start_year).rename("YTD"),
    ]
    return pd.concat(output, axis=1)


# Backward-compatible aliases
def LocalIndices() -> pd.DataFrame:
    return local_indices_performance()
