from pymongo import MongoClient, errors
from bunnet import init_bunnet
from ix.misc import Settings

from typing import Annotated, List, Dict, Optional
from datetime import date
from pydantic import BaseModel
from bunnet import Document, Indexed
from datetime import datetime

# MongoDB client and GridFS setup
client = MongoClient(
    Settings.db_url,
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=10000,
    maxPoolSize=50,
    retryWrites=True,
)

database = client[Settings.db_name]


class Code(BaseModel):
    code: Annotated[str, Indexed(unique=True)]


class EconomicCalendar(Document):
    date: str
    time: str
    event: str
    zone: Optional[str] = None
    currency: Optional[str] = None
    importance: Optional[str] = None
    actual: Optional[str] = None
    forecast: Optional[str] = None
    previous: Optional[str] = None


class Signal(Code, Document):
    data: Optional[Dict[date, float]] = {}


class Book(BaseModel):
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


import pandas as pd


class Performance(Document):
    code: Annotated[str, Indexed()]
    date: date
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


class User(Document):
    username: Annotated[str, Indexed(unique=True)]
    password: str
    disabled: bool = False
    is_admin: bool = False

    def verify_password(self, password):
        return self.password == password

    @classmethod
    def get_user(cls, username) -> Optional["User"]:
        return cls.find_one(cls.username == username).run()

    @classmethod
    def new_user(cls, username: str, password: str) -> "User":
        return cls(username=username, password=password).create()

    @classmethod
    def exists(cls, username: str) -> bool:
        user = cls.get_user(username=username)
        if user:
            return True
        return False


from pydantic import Field


class Insight(Document):
    """
    Represents an insight with metadata, while the actual file content is stored in GridFS.
    """

    issuer: str = "Unnamed"
    name: str = "Unnamed"
    published_date: date = Field(default_factory=date.today)
    summary: Optional[str] = None

    def save_content(self, content: bytes) -> bool:
        """
        Saves the given content in chunks of 10MB.
        Each chunk is stored as a separate InsightContent document.
        """
        from .boto import Boto

        return Boto().save_pdf(pdf_content=content, filename=f"{self.id}.pdf")

    def get_content(self) -> bytes:
        """
        Saves the given content in chunks of 10MB.
        Each chunk is stored as a separate InsightContent document.
        """
        from .boto import Boto

        return Boto().get_pdf(filename=f"{self.id}.pdf")


class TacticalView(Document):
    # Define the fields for the document
    views: dict
    published_date: (
        datetime  # Declare published_date as a datetime field, no DateTimeField
    )

    # Optionally, add a pre-save hook to modify the document before saving it
    @classmethod
    def pre_save(cls, document):
        # Automatically set the published_date if not set
        if not document.published_date:
            document.published_date = datetime.now()
        return document


from .models import (
    Metadata,
    TimeSeries,
    TimePoint,
    InsightSource,
    MarketCommentary,
    Prediction,
    DataSource,
    Universe,
)


# Initialize Bunnet
def init():
    try:
        init_bunnet(
            database=database,
            document_models=[
                Metadata,
                DataSource,
                TimeSeries,
                TimePoint,
                EconomicCalendar,
                Strategy,
                Performance,
                User,
                Signal,
                Insight,
                TacticalView,
                InsightSource,
                MarketCommentary,
                Prediction,
                Universe,
            ],
        )
        print(
            f"Successfully initialized Bunnet with MongoDB database: {Settings.db_name}"
        )
    except errors.ServerSelectionTimeoutError as e:
        print(f"Error: Could not connect to MongoDB server. Timeout reached: {e}")
    except errors.ConnectionFailure as e:
        print(f"Error: Failed to connect to MongoDB: {e}")
    except Exception as e:
        print(f"Unexpected error occurred during Bunnet initialization: {e}")
