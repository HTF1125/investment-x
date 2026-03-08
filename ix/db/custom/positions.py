from __future__ import annotations

import pandas as pd

from ix.db.query import Series


POSITION_ASSETS = {
    "S&P500": ("CFTNCLOI%ALLS5C3512CMEOF_US", "CFTNCSOI%ALLS5C3512CMEOF_US"),
    "USD": ("CFTNCLOI%ALLJUSDNYBTOF_US", "CFTNCSOI%ALLJUSDNYBTOF_US"),
    "Gold": ("CFTNCLOI%ALLGOLDCOMOF_US", "CFTNCSOI%ALLGOLDCOMOF_US"),
    "JPY": ("CFTNCLOI%ALLYENCMEOF_US", "CFTNCSOI%ALLYENCMEOF_US"),
    "UST-10Y": ("CFTNCLOI%ALLTN10YCBOTOF_US", "CFTNCSOI%ALLTN10YCBOTOF_US"),
    "UST-Ultra": ("CFTNCLOI%ALLLUT3163CBOTOF_US", "CFTNCSOI%ALLLUT3163CBOTOF_US"),
    "Commodities": ("CFTNCLOI%ALLDJUBSERCBOTOF_US", "CFTNCSOI%ALLDJUBSERCBOTOF_US"),
}


def investor_positions_net() -> pd.DataFrame:
    """Net positioning (long - short) for each asset."""
    data = {
        name: Series(long_code) - Series(short_code)
        for name, (long_code, short_code) in POSITION_ASSETS.items()
    }
    return pd.DataFrame(data)


def investor_positions_vs_trend(weeks: int = 52) -> pd.DataFrame:
    """Net positioning vs rolling mean trend."""
    data = investor_positions_net()
    return data - data.rolling(weeks).mean()


def usd_open_interest() -> pd.Series:
    """USD open interest (long - short)."""
    return Series("CFTNCLOI%ALLJUSDNYBTOF_US") - Series("CFTNCSOI%ALLJUSDNYBTOF_US")


# Backward-compatible aliases
def USD_Open_Interest() -> pd.Series:
    return usd_open_interest()


def InvestorPositionsvsTrend(weeks: int = 52) -> pd.DataFrame:
    return investor_positions_vs_trend(weeks=weeks)
