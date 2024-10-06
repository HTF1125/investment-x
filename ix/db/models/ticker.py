from typing import Annotated
from datetime import date
from bunnet import Document, Indexed, Link


class Ticker(Document):
    code: Annotated[str, Indexed(unique=True)]
    name: str | None = None
    exchange: str | None = None
    market: str | None = None
    source: str = "Yahoo"
    yahoo: str | None = None
    fred: str | None = None
    bloomberg: str | None = None


class TimeseriesNew(Document):
    ticker: Link[Ticker]
    field: str
    data: dict[date, float]


class TickerNew(Document):

    code: Annotated[str, Indexed(unique=True)]
    name: str | None = None
    exchange: str | None = None
    market: str | None = None
    source: str = "YAHOO"
    bloomberg: str | None = None
    fred: str | None = None
    yahoo: str | None = None
    px_last: dict[date, float] = {}
    px_volume: dict[date, float] = {}