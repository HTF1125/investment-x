from typing import Annotated
from bunnet import Document, Indexed
from datetime import datetime

from .user import *


def all_models():
    """
    Returns a list of all document models for easy reference.
    """
    return [
        Ticker,
        Timeseries,
        EconomicCalendar,
        Strategy,
        Regime,
        User,
    ]


# Define your models
class Ticker(Document):
    code: Annotated[str, Indexed(unique=True)]
    name: str | None = None
    exchange: str | None = None
    market: str | None = None
    source: str = "Yahoo"
    yahoo: str | None = None
    fred: str | None = None
    bloomberg: str | None = None


class Timeseries(Document):
    code: Annotated[str, Indexed(unique=True)]
    field: str
    data: dict[datetime, float]


class EconomicCalendar(Document):
    date: str
    time: str
    event: str
    zone: str | None = None
    currency: str | None = None
    importance: str | None = None
    actual: str | None = None
    forecast: str | None = None
    previous: str | None = None


class Strategy(Document):
    code: Annotated[str, Indexed(unique=True)]
    data: dict | None = {}


class Regime(Document):
    code: Annotated[str, Indexed(unique=True)]
    data: dict[datetime, str] | None = {}
