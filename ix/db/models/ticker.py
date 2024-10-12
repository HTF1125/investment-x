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


from pydantic import BaseModel


class KeyPerformance(BaseModel):
    code: Annotated[str, Indexed()]
    date: Annotated[date, Indexed()]
    level: float
    pct_chg_1d: float | None = None
    pct_chg_1w: float | None = None
    pct_chg_1m: float | None = None
    pct_chg_3m: float | None = None
    pct_chg_6m: float | None = None
    pct_chg_1y: float | None = None
    pct_chg_3y: float | None = None
    pct_chg_mtd: float | None = None
    pct_chg_ytd: float | None = None


class Performance(KeyPerformance, Document): ...


class PxLast(Document):
    code: Annotated[str, Indexed(unique=True)]
    data: dict[date, float] = {}
