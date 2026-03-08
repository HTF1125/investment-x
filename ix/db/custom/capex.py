from __future__ import annotations

import pandas as pd


AI_CAPEX_TICKERS = "Nvdia=NVDA,Google=GOOG,Microsoft=MSFT,Amazon=AMZN,Meta=META"


def _ai_capex_multi(field: str) -> pd.DataFrame:
    from ix.db.query import Series
    codes = [c.strip() for c in AI_CAPEX_TICKERS.split(",")]
    series_list = []
    for code in codes:
        if "=" in code:
            alias, real_code = code.split("=", maxsplit=1)
            s = Series(f"{real_code}:{field}", freq="B")
            s.name = alias
        else:
            s = Series(f"{code}:{field}", freq="B")
        if not s.empty:
            series_list.append(s)
    if not series_list:
        return pd.DataFrame()
    return pd.concat(series_list, axis=1).ffill().dropna()


def ai_capex_ntma() -> pd.DataFrame:
    return _ai_capex_multi("FE_CAPEX_NTMA")


def ai_capex_ltma() -> pd.DataFrame:
    return _ai_capex_multi("FE_CAPEX_LTMA")


def ai_capex_q() -> pd.DataFrame:
    return _ai_capex_multi("FE_CAPEX_Q")


def ai_capex_qoq() -> pd.DataFrame:
    return (
        ai_capex_q().dropna().resample("W-Fri").last().pct_change(52).mul(100)
    )


def ai_capex_total_qoq() -> pd.DataFrame:
    return (
        ai_capex_q()
        .sum(axis=1)
        .dropna()
        .resample("W-Fri")
        .last()
        .pct_change(52)
        .mul(100)
    )


def ai_capex_total_yoy() -> pd.DataFrame:
    ntma = ai_capex_ntma().sum(axis=1).dropna().resample("W-Fri").last()
    ltma = ai_capex_ltma().sum(axis=1).dropna().resample("W-Fri").last()
    data = (ntma / ltma - 1).mul(100)
    data.name = "YoY"
    return data
