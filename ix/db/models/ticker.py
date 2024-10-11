from typing import Annotated
from datetime import date
from bunnet import Document, Indexed, Link


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


class Performance(Document):
    ticker: Link[Ticker]
    date: Annotated[date, Indexed()]
    pct_chg_1d: float | None = None
    pct_chg_1w: float | None = None
    pct_chg_1m: float | None = None
    pct_chg_3m: float | None = None
    pct_chg_6m: float | None = None
    pct_chg_1y: float | None = None
    pct_chg_3y: float | None = None
    pct_chg_mtd: float | None = None
    pct_chg_ytd: float | None = None


class PxLast(Document):

    ticker: Link[Ticker]
    data: dict[date, float] = {}