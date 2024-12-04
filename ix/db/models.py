from typing import Annotated, List, Dict, Optional
from datetime import date
from pydantic import BaseModel
from bunnet import Document, Indexed
import pandas as pd


class Code(BaseModel):
    code: Annotated[str, Indexed(unique=True)]


class ResearchFile(Code, Document):

    content: bytes


class IndexGroup(Code, Document):
    constituents: Dict[str, str]


class EconomicCalendar(Document):
    """
    Represents an entry in an economic calendar, with fields for event details.
    """

    date: str
    time: str
    event: str
    zone: Optional[str] = None
    currency: Optional[str] = None
    importance: Optional[str] = None
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None


class InsightKeyInfo(BaseModel):
    """
    Key information about an insight, used to provide quick reference data.
    """

    date: Annotated[date, Indexed()]
    title: str
    tags: List[str] = []


class Insight(Document):
    """
    Represents a detailed insight with metadata like date, title, and tags.
    """

    date: Annotated[date, Indexed()]
    title: str
    tags: List[str] = []
    content: str


class Regime(Document):
    """
    Represents a regime with historical data, identified by a unique code.
    """

    code: Annotated[str, Indexed(unique=True)]
    data: Optional[Dict[date, str]] = {}


class Signal(Code, Document):

    data: Optional[Dict[date, float]] = {}


class Book(BaseModel):
    """
    A data structure representing various lists related to strategy books.
    """

    d: List[str] = []
    v: List[float] = []
    l: List[float] = []
    b: List[float] = []
    s: List[Dict[str, float]] = []
    c: List[Dict[str, float]] = []
    w: List[Dict[str, float]] = []
    a: List[Dict[str, float]] = []


class StrategyKeyInfo(BaseModel):
    code: Annotated[str, Indexed(unique=True)]
    frequency: str = "ME"
    last_updated: Optional[str] = None
    ann_return: Optional[float] = None
    ann_volatility: Optional[float] = None
    nav_history: Optional[List[float]] = None


class Strategy(StrategyKeyInfo, Document):
    """
    Represents a strategy with related book data and performance metrics.
    """

    book: Book = Book()


class TickerInfo(BaseModel):
    code: Annotated[str, Indexed(unique=True)]
    name: Optional[str] = None
    exchange: Optional[str] = None
    market: Optional[str] = None
    source: str = "YAHOO"
    bloomberg: Optional[str] = None
    fred: Optional[str] = None
    yahoo: Optional[str] = None
    remark: Optional[str] = None


class Ticker(TickerInfo, Document):

    def px_last(self, exists: bool = False) -> pd.Series:
        pxlast = PxLast.find_one({"code": self.code}).run()
        if pxlast is not None:
            return pd.Series(data=pxlast.data, name=pxlast.code)
        raise ValueError(f"pxlast fot '{self.code}' is not available.")


class Performance(Document):
    """
    Stores performance metrics for a given ticker, including daily, weekly, and monthly changes.
    """

    code: Annotated[str, Indexed()]
    date: Annotated[date, Indexed()]
    level: float
    pct_chg_1d: Optional[float] = None
    pct_chg_1w: Optional[float] = None
    pct_chg_1m: Optional[float] = None
    pct_chg_3m: Optional[float] = None
    pct_chg_6m: Optional[float] = None
    pct_chg_1y: Optional[float] = None
    pct_chg_3y: Optional[float] = None
    pct_chg_mtd: Optional[float] = None
    pct_chg_ytd: Optional[float] = None


class PxLastModel(BaseModel):
    code: Annotated[str, Indexed(unique=True)]
    data: Dict[date, float] = {}


class PxLast(PxLastModel, Document): ...


class User(Document):
    """
    Represents a user in the system with minimal authentication data.
    """

    password: str
    # Optionally, add fields like `email` if needed with appropriate validation
    # email: EmailStr


def all_models():
    """
    Returns a list of all document models for easy reference in database initialization.
    """
    return [
        EconomicCalendar,
        Insight,
        Regime,
        Strategy,
        Ticker,
        Performance,
        PxLast,
        User,
        Signal,
        IndexGroup,
        ResearchFile,
    ]
