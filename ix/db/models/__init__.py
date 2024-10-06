from typing import Annotated
from bunnet import Document, Indexed
from datetime import datetime

from .ticker import Ticker, TimeseriesNew, TickerNew
from .strategy import Strategy
from .regime import Regime
from .economic_calendar import EconomicCalendar
from .user import *


def all_models():
    """
    Returns a list of all document models for easy reference.
    """
    return [
        Ticker,
        TickerNew,
        Timeseries,
        TimeseriesNew,
        EconomicCalendar,
        Strategy,
        Regime,
        User,
    ]

    bloomberg: str | None = None


class Timeseries(Document):
    code: Annotated[str, Indexed(unique=True)]
    field: str
    data: dict[datetime, float]
