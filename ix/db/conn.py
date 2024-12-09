from pymongo import MongoClient, errors
from bunnet import init_bunnet
from ix.misc import Settings

from typing import Annotated, List, Dict, Optional
from datetime import date
from pydantic import BaseModel
from bunnet import Document, Indexed

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


class ResearchFile(Code, Document):
    """
    Model for storing research file metadata.
    The file content itself will be stored in GridFS.
    """

    metadata: Optional[Dict[str, str]] = {}


class IndexGroup(Code, Document):
    constituents: Dict[str, str]


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


class Ticker(TickerInfo, Document):

    @property
    def pxlast(self) -> pd.Series:
        pxlast = PxLast.find_one(PxLast.code == self.code).run()
        if not pxlast:
            pxlast = PxLast(code=self.code).create()
            return pd.Series(dtype=float)
        pxlast_data = pd.Series(data=pxlast.data)
        pxlast_data.index = pd.to_datetime(pxlast_data.index)
        pxlast_data.name = self.code
        return pxlast_data

    @pxlast.setter
    def pxlast(self, data: pd.Series) -> None:
        p = self.pxlast
        if not p.empty:
            data = data.combine_first(self.pxlast)
        pxlast = PxLast.find_one(PxLast.code == self.code).run()
        pxlast.set({"data": data.to_dict()})


class Performance(Document):
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


class PxLast(PxLastModel, Document):
    pass


class User(Document):
    password: str


from pydantic import Field


class Insight(Document):
    """
    Represents an insight with metadata, while the actual file content is stored in GridFS.
    """

    issuer: str = "XXX"
    name: str = "Unnamed"
    published_date: date = Field(default_factory=date.today)
    summary: Optional[str] = None

    def get_content(self) -> bytes:
        """
        Retrieves and concatenates all content chunks for a given insight ID.
        """
        try:
            # Retrieve all content chunks for the given insight ID and sort by index
            contents = (
                InsightContent.find_many(InsightContent.insight_id == str(self.id))
                .sort("+index")
                .run()
            )

            # Concatenate the content chunks (bytes)
            output = b"".join(content.content for content in contents)
            return output
        except Exception as e:
            raise ValueError(f"Error retrieving content: {str(e)}")

    def update_content(self, content: bytes) -> str:
        """
        Retrieves and concatenates all content chunks for a given insight ID.
        """
        try:
            # Retrieve all content chunks for the given insight ID and sort by index
            InsightContent.find_many(
                InsightContent.insight_id == str(self.id)
            ).delete().run()

            return self.save_content(content)

        except Exception as e:
            raise ValueError(f"Error retrieving content: {str(e)}")

    def save_content(self, content: bytes) -> str:
        """
        Saves the given content in chunks of 10MB.
        Each chunk is stored as a separate InsightContent document.
        """
        try:
            # Define the maximum chunk size (10MB)
            chunk_size = 10 * 1024 * 1024  # 10 MB in bytes

            # Split the content into chunks
            chunks = [
                content[i : i + chunk_size] for i in range(0, len(content), chunk_size)
            ]

            # Delete existing content for this insight
            InsightContent.find_many(
                InsightContent.insight_id == str(self.id)
            ).delete().run()

            # Save each chunk as a separate InsightContent document
            for index, chunk in enumerate(chunks):
                InsightContent(
                    insight_id=str(self.id), index=index, content=chunk
                ).create()

            return f"Content saved in {len(chunks)} chunks."
        except Exception as e:
            raise ValueError(f"Error saving content: {str(e)}")


class InsightContent(Document):
    """
    Represents a chunk of content for an Insight document.
    """

    insight_id: str  # Reference to the parent Insight
    index: int  # The order of the chunk
    content: bytes  # The chunk content


# Initialize Bunnet
def init():
    try:
        init_bunnet(
            database=database,
            document_models=[
                EconomicCalendar,
                Strategy,
                Ticker,
                Performance,
                PxLast,
                User,
                Signal,
                IndexGroup,
                ResearchFile,
                Insight,
                InsightContent,
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
