import pandas as pd
from pandas.tseries.offsets import BDay


def today() -> pd.Timestamp:
    return pd.Timestamp("today")


def yesterday() -> pd.Timestamp:
    return today() - pd.DateOffset(days=1)


def last_business_day() -> pd.Timestamp:
    current_date = today()
    last_bday = current_date - BDay(1)

    # If the last business day is in the current month, return it
    if last_bday.month == current_date.month:
        return last_bday

    # Otherwise, get the last business day of the previous month
    last_day_prev_month = current_date.replace(day=1) - pd.DateOffset(days=1)
    return last_day_prev_month - BDay(0)


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
