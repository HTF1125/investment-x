from typing import Annotated, Dict, Optional, Union, List
from bunnet import Document, Indexed
from datetime import date, datetime
import pandas as pd
from ix.misc import get_logger
from ix.misc import get_yahoo_data
from ix.misc import get_fred_data
from ix.misc import relative_timestamp
from pydantic import BaseModel, Field
import os

logger = get_logger(__name__)


def get_performance(px_last: pd.Series) -> dict:
    px_last = px_last.resample("D").last().ffill()
    asofdate = pd.Timestamp(str(px_last.index[-1]))
    level = px_last.loc[asofdate]
    pct_chg = (level / px_last).sub(1).mul(100).round(2)
    out = {}
    for period in ["1D", "1W", "1M", "3M", "6M", "1Y", "3Y", "MTD", "YTD"]:
        r_date = relative_timestamp(asofdate=asofdate, period=period)
        try:
            out[f"PCT_CHG_{period}"] = pct_chg.loc[r_date]
        except:
            pass
    return out


from typing import Any


class Metadata(Document):
    code: Annotated[str, Indexed(unique=True)]
    exchange: Optional[str] = None
    market: Optional[str] = None
    id_isin: Optional[str] = None
    name: Optional[str] = None
    remark: Optional[str] = None
    disabled: bool = False
    bbg_ticker: Optional[str] = None
    yah_ticker: Optional[str] = None
    fre_ticker: Optional[str] = None
    ts_fields: Optional[str] = None
    tp_fields: Optional[str] = None
    has_performance: bool = False

    @classmethod
    def to_dataframe(cls) -> pd.DataFrame:
        out = [metadata.model_dump() for metadata in cls.find().run()]
        out = pd.DataFrame(out)
        out = out.set_index(keys=["id"], drop=True)
        return out

    def update_px(self):
        if self.yah_ticker:
            ts = get_yahoo_data(code=self.yah_ticker)
            if ts.empty:
                logger.warning(f"No Yahoo data returned for ticker {self.yah_ticker}")
                return False

            # Mapping of source field to metadata field.
            field_mappings = {
                # "Open": "PX_OPEN",
                # "High": "PX_HIGH",
                # "Low": "PX_LOW",
                # "Close": "PX_CLOSE",
                # "Volume": "PX_VOLUME",
                "Adj Close": "PX_LAST",
            }
            for source_field, target_field in field_mappings.items():
                try:
                    # Ensure the data is converted to float.
                    series = ts[source_field].astype(float)
                except Exception as conv_err:
                    logger.error(
                        f"Error converting {source_field} to float for code {self.code}: {conv_err}"
                    )
                    continue

                # Update the timeseries data.
                self.ts(field=target_field).data = series
                logger.debug(
                    f"Set timeseries field {target_field} for code {self.code}"
                )
                logger.info(
                    f"Successfully updated {target_field} for metadata code: {self.code}"
                )

    def ts(
        self,
        field: str = "PX_LAST",
    ) -> "TimeSeries":
        if not self.id:
            raise
        ts = TimeSeries.find_one({"code": self.code, "field": field}).run()
        if ts is None:
            logger.debug(f"Create new TimeSeries for {self.code} - {field}")
            ts = TimeSeries(code=self.code, field=field).create()
        return ts

    def tp(self) -> "TimePoint":
        tp = TimePoint.find_one({"code": self.code}).run()
        if tp is None:
            return TimePoint(code=self.code).create()
        return tp


class TimeSeries(Document):
    code: str
    field: str
    i_data: Dict[date | str, str | int | float] = {}

    @property
    def data(self) -> pd.Series:
        data = pd.Series(data=self.i_data)
        try:
            data.index = pd.to_datetime(data.index)
        except:
            valid_dates = pd.to_datetime(data.index, errors="coerce")
            data = data[valid_dates.notna()]
            data.index = pd.to_datetime(data.index)
            self.set({"i_data": data.to_dict()})
        data = data.map(lambda x: pd.to_numeric(x, errors="coerce")).dropna()
        return data.sort_index()

    @data.setter
    def data(self, data: Union[pd.Series, Dict[Union[date, str], float]]) -> None:
        if isinstance(data, dict):
            data = pd.Series(data)

        # Normalize index and values
        data.index = pd.to_datetime(data.index, errors="coerce")
        data = pd.to_numeric(data, errors="coerce")
        data = data.dropna()
        data = data[~data.index.isna()]  # remove any rows with bad datetime index
        # Update i_data in-place: new keys added, existing keys overwritten
        i_data = self.i_data.copy()
        i_data.update(data.to_dict())
        self.set({"i_data": i_data})

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
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.Series:
        data = self.data
        if start_date:
            data = data.loc[start_date:]
        if end_date:
            data = data.loc[:end_date]
        return data


class TimePoint(Document):
    code: Annotated[str, Indexed(unique=True)]
    i_data: Dict[str, str | int | float] = {}

    @property
    def data(self) -> pd.Series:
        return pd.Series(data=self.i_data)

    @data.setter
    def data(self, data: Union[pd.Series, Dict[date, float]]) -> None:
        if isinstance(data, dict):
            data = pd.Series(data=data)
        if self.i_data:
            data = data.combine_first(self.data)
        if data is not None:
            data = data.dropna()
            self.set({"i_data": data.to_dict()})


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


import numpy as np


class Perforamnce(Document):

    code: Annotated[str, Indexed(unique=True)]
    PX_LAST: Optional[float] = None
    PCT_CHG_1D: Optional[float] = None
    PCT_CHG_1W: Optional[float] = None
    PCT_CHG_1M: Optional[float] = None
    PCT_CHG_3M: Optional[float] = None
    PCT_CHG_6M: Optional[float] = None
    PCT_CHG_1Y: Optional[float] = None
    PCT_CHG_3Y: Optional[float] = None
    PCT_CHG_5Y: Optional[float] = None
    PCT_CHG_MTD: Optional[float] = None
    PCT_CHG_YTD: Optional[float] = None
    VOL_1D: Optional[float] = None
    VOL_1W: Optional[float] = None
    VOL_1M: Optional[float] = None
    VOL_3M: Optional[float] = None
    VOL_6M: Optional[float] = None
    VOL_1Y: Optional[float] = None
    VOL_3Y: Optional[float] = None
    VOL_5Y: Optional[float] = None
    VOL_MTD: Optional[float] = None
    VOL_YTD: Optional[float] = None

    @classmethod
    def get_dataframe(cls) -> pd.DataFrame:
        return (
            pd.DataFrame([p.model_dump() for p in cls.find().run()])
            .set_index(keys=["id"], drop=True)
            .replace({np.nan: None})
        )


from typing import Literal

ValidSources = Literal[
    "Yahoo", "Fred", "Infomax", "Eikon", "FactSet", "Bloomberg", "InvestmentX"
]


class Source(BaseModel):
    field: str
    source: ValidSources
    source_ticker: Optional[str] = None
    source_field: Optional[str] = None


class Ticker(Document):

    code: Annotated[str, Indexed(unique=True)]
    name: Optional[str] = None
    category: Optional[str] = None
    asset_class: Optional[str] = None
    frequency: Optional[str] = None
    fields: List[Source] = []

    def add_field(self, source: Source) -> None:
        """
        Add or update a field entry in the Ticker's fields dictionary.

        Args:
            field (str): The name of the field to add or update.
            sources (Sources): The Sources object containing source mappings.

        Raises:
            ValueError: If the input arguments are invalid.
        """
        self.fields.append(source)
        self.save()

    def get_timeseries(
        self, field: str = "PX_LAST", create: bool = True
    ) -> "TimeSeries":
        if not self.id:
            raise
        ts = TimeSeries.find_one({"code": self.code, "field": field}).run()
        if ts is not None:
            return ts
        if create:
            logger.debug(f"Create new TimeSeries for {self.code} - {field}")
            ts = TimeSeries(code=self.code, field=field).create()
            return ts
        raise ValueError(f"TimeSeries not found for {self.code} - {field}")

    def get_data(
        self,
        field: str = "PX_LAST",
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.Series:

        timeseries = self.get_timeseries(field=field, create=False)
        if timeseries is None:
            raise ValueError(f"TimeSeries not found for {self.code} - {field}")
        data = timeseries.get_data(start_date=start_date, end_date=end_date)
        return data

    def get_sources(self) -> pd.DataFrame:
        """
        Returns a dictionary of sources for the Ticker.
        """
        sources = pd.DataFrame([source.model_dump() for source in self.fields])
        sources = sources.set_index(keys=["field"], drop=True)
        return sources

    @classmethod
    def get_dataframe(cls) -> pd.DataFrame:
        tickers = []
        for ticker in cls.find().run():
            tickers.append(ticker.model_dump())
        return pd.DataFrame(tickers)


def all():
    return [
        Metadata,
        TimeSeries,
        TimePoint,
        EconomicCalendar,
        User,
        Insight,
        TacticalView,
        InsightSource,
        MarketCommentary,
        Prediction,
        Universe,
        Ticker,
    ]
