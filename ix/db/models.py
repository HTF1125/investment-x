from typing import Annotated, Dict, Optional, Union, List
from bunnet import Document, Indexed
from datetime import date, datetime
import pandas as pd
from ix.misc import get_logger
from ix.misc import relative_timestamp
from pydantic import BaseModel, Field
import os

logger = get_logger(__name__)


class TimeseriesData(Document):
    key: Annotated[str, Indexed(unique=True)]
    i_data: Dict[date | str, str | int | float] = {}


class Timeseries(Document):
    code: Annotated[str, Indexed(unique=True)]
    name: Optional[str] = None
    provider: Optional[str] = None
    asset_class: Optional[str] = None
    category: Optional[str] = None
    start: Optional[date] = None
    end: Optional[date] = None
    num_data: Optional[int] = None
    source: Optional[str] = None
    frequency: Optional[str] = None
    source_ticker: Optional[str] = None
    source_field: Optional[str] = None
    unit: Optional[str] = None
    currency: Optional[str] = None
    country: Optional[str] = None

    @property
    def timeseries_data(self) -> TimeseriesData:
        tsd = TimeseriesData.find_one({"key": str(self.id)}).run()
        if tsd is None:
            tsd = TimeseriesData(key=str(self.id)).create()
        return tsd

    @property
    def data(self) -> pd.Series:
        data = pd.Series(data=self.timeseries_data.i_data)
        try:
            data.index = pd.to_datetime(data.index)
        except:
            valid_dates = pd.to_datetime(data.index, errors="coerce")
            data = data[valid_dates.notna()]
            data.index = pd.to_datetime(data.index)
            self.set({"i_data": data.to_dict()})
        data = data.map(lambda x: pd.to_numeric(x, errors="coerce")).dropna()
        data.name = self.code
        return data.sort_index()

    @data.setter
    def data(self, data: Union[pd.Series, Dict[Union[date, str], float]]) -> None:
        if isinstance(data, dict):
            data = pd.Series(data)

        # Normalize index and values
        data.index = pd.to_datetime(data.index, errors="coerce")
        data = pd.to_numeric(data, errors="coerce")
        data = data.dropna()
        data = data[~data.index.isna()]

        i_data = self.timeseries_data.i_data.copy()
        i_data.update(data.to_dict())
        if i_data:
            self.set(
                {
                    "start": data.index[0],
                    "end": data.index[-1],
                    "num_data": len(data),
                }
            )
            self.timeseries_data.set({"i_data": i_data})

    def reset(self) -> bool:
        self.set({"start": None, "end": None, "num_data": 0})
        self.timeseries_data.set({"i_data": {}})
        return True

    @classmethod
    def get_parquet(cls, filepath: str = "docs/timeseries.parquet") -> pd.DataFrame:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        try:
            # Load existing data if file exists
            data = pd.read_parquet(filepath)
        except (FileNotFoundError, pd.errors.EmptyDataError):
            data = pd.DataFrame()
        return data

    @classmethod
    def to_parquet(
        cls, data: pd.DataFrame, filepath: str = "docs/timeseries.parquet"
    ) -> None:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        try:
            # Load existing data if file exists
            data_parquet = pd.read_parquet(filepath)
        except (FileNotFoundError, pd.errors.EmptyDataError):
            data_parquet = pd.DataFrame()

        # Append new data
        data_parquet = data_parquet.combine_first(other=data)

        # Ensure the index is datetime
        data_parquet.index = pd.to_datetime(data_parquet.index, errors="coerce")

        # Convert all data to numeric (coerce non-numeric values to NaN)
        data_parquet = data_parquet.map(lambda x: pd.to_numeric(x, errors="coerce"))

        # Ensure the index name is "Date"
        data_parquet.index.name = "Date"

        # Save back to Parquet
        data_parquet.sort_index().to_parquet(filepath, compression=None)

    @classmethod
    def get_csv(cls, filepath: str = "docs/timeseries.csv") -> pd.DataFrame:
        # Ensure the directory exists
        import os

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        try:
            # Load existing data if file exists
            data = pd.read_csv(filepath, index_col=0, parse_dates=True)
        except (FileNotFoundError, pd.errors.EmptyDataError):
            data = pd.DataFrame()
        return data

    @classmethod
    def to_csv(cls, data: pd.DataFrame, filepath: str = "docs/timeseries.csv") -> None:
        # Ensure the directory exists
        import os

        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        try:
            # Load existing data if file exists
            data_csv = pd.read_csv(filepath, index_col=0, parse_dates=True)
        except (FileNotFoundError, pd.errors.EmptyDataError):
            data_csv = pd.DataFrame()

        # Append new data
        data_csv = data_csv.combine_first(other=data)

        # Ensure the index is datetime
        data_csv.index = pd.to_datetime(data_csv.index, errors="coerce")

        # Convert all data to numeric (coerce non-numeric values to NaN)
        data_csv = data_csv.map(lambda x: pd.to_numeric(x, errors="coerce"))

        # Ensure the index name is "Date"
        data_csv.index.name = "Date"

        # Save back to CSV
        data_csv.sort_index().to_csv(filepath)

    def get_data(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None,
    ) -> pd.Series:
        data = self.data
        if start:
            data = data.loc[start:]
        if end:
            data = data.loc[:end]
        return data


class InsightSource(Document):
    url: str
    name: str = "Unnamed"
    frequency: str = "Unclassified"
    remark: Optional[str] = None
    last_visited: datetime = Field(default_factory=datetime.now)


class MarketCommentary(Document):

    asofdate: Annotated[date, Indexed(unique=True)] = Field(default_factory=date.today)
    frequency: str = "Daily"
    content: str = ""
    last_visited: datetime = Field(default_factory=datetime.now)


class Prediction(Document):
    code: Annotated[str, Indexed(unique=True)]
    name: Optional[str] = None
    features: Dict[str, Dict[date, float]]
    target: Dict[date, float]
    prediction: Dict[date, float]


class Asset(BaseModel):

    code: Annotated[str, Indexed(unique=True)]
    name: Optional[str] = None


class Universe(Document):
    code: Annotated[str, Indexed(unique=True)]
    name: Optional[str] = None
    assets: List[Asset]


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

    @classmethod
    def get_dataframe(cls) -> pd.DataFrame:
        releases = [release.model_dump() for release in cls.find().run()]
        releases = pd.DataFrame(releases)
        releases = releases.set_index(keys=["id"], drop=True)
        return releases


class Book(BaseModel):
    d: List[str] = []
    v: List[float] = []
    l: List[float] = []
    b: List[float] = []
    s: List[Dict[str, float]] = []
    c: List[Dict[str, float]] = []
    w: List[Dict[str, float]] = []
    a: List[Dict[str, float]] = []


class Strategy(Document):
    code: Annotated[str, Indexed(unique=True)]
    frequency: str = "ME"
    last_updated: Optional[str] = None
    ann_return: Optional[float] = None
    ann_volatility: Optional[float] = None
    nav_history: Optional[List[float]] = None
    book: Book = Book()


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


from typing import Literal

ValidSources = Literal[
    "Yahoo", "Fred", "Infomax", "Eikon", "FactSet", "Bloomberg", "InvestmentX"
]


def all():
    return [
        EconomicCalendar,
        User,
        Insight,
        TacticalView,
        InsightSource,
        MarketCommentary,
        Prediction,
        Universe,
        Strategy,
        Timeseries,
        TimeseriesData,
    ]
