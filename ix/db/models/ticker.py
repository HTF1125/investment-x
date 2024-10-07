from typing import Annotated
from datetime import date
from bunnet import Document, Indexed


class Ticker(Document):
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