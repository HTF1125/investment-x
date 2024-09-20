import pandas as pd


def now() -> pd.Timestamp:
    return pd.Timestamp("now")


def today() -> pd.Timestamp:
    return pd.Timestamp("today")


def lastyear() -> pd.Timestamp:
    return pd.Timestamp("today") - pd.DateOffset(years=1)


def parse(text: str) -> pd.Timestamp:
    return pd.Timestamp(text)


def onemonthlater() -> pd.Timestamp:
    return today() + pd.DateOffset(months=1)


def onemonthbefore() -> pd.Timestamp:
    return today() - pd.DateOffset(months=1)


def tomorrow() -> pd.Timestamp:
    return pd.Timestamp("today") + pd.DateOffset(days=1)
