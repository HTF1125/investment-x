from typing import Annotated, Dict, Optional, Union, List
from bunnet import Document, Indexed
from datetime import date, datetime
import pandas as pd
from ix.misc import get_logger
from ix.misc import relative_timestamp
from pydantic import Field, BaseModel, ValidationError
import os

logger = get_logger(__name__)


class TimeseriesData(Document):
    key: Annotated[str, Indexed(unique=True)]
    i_data: Dict[date, str | int | float] = {}


from typing import Annotated, Dict, Optional, Union
from bunnet import Document, Indexed
from datetime import date, datetime
import pandas as pd
from pydantic import Field, BaseModel, ValidationError
from ix.misc import get_logger

logger = get_logger(__name__)


class TimeseriesData(Document):
    key: Annotated[str, Indexed(unique=True)]
    i_data: Dict[date, str | int | float] = {}


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
    source_code: Optional[str] = None
    frequency: Optional[str] = None
    source_ticker: Optional[str] = None
    source_field: Optional[str] = None
    unit: Optional[str] = None
    currency: Optional[str] = None
    country: Optional[str] = None

    # New: parent relationship (store as string to match your current key usage)
    parent_id: Optional[str] = Field(default=None)

    @property
    def timeseries_data(self) -> TimeseriesData:
        tsd = TimeseriesData.find_one({"key": str(self.id)}).run()
        if tsd is None:
            tsd = TimeseriesData(key=str(self.id)).create()
        return tsd

    def _get_parent(self) -> Optional["Timeseries"]:
        if not self.parent_id:
            return None
        # Prevent obvious self-link
        if str(self.parent_id) == str(self.id):
            logger.warning("Timeseries %s has parent_id equal to self; ignoring.", self.id)
            return None
        parent = Timeseries.get(self.parent_id).run()
        return parent

    def _detect_cycle(self, candidate_parent_id: Optional[str]) -> bool:
        """
        Return True if setting candidate_parent_id would create a cycle.
        """
        if not candidate_parent_id:
            return False
        seen = set([str(self.id)])
        cur = Timeseries.find_one({"_id": candidate_parent_id}).run()
        while cur is not None:
            if str(cur.id) in seen:
                return True
            seen.add(str(cur.id))
            if not cur.parent_id:
                break
            cur = Timeseries.find_one({"_id": cur.parent_id}).run()
        return False

    def set_parent(self, parent: Optional["Timeseries"]) -> None:
        """
        Explicit helper to set/unset parent with cycle check.
        """
        new_parent_id = None if parent is None else str(parent.id)
        if self._detect_cycle(new_parent_id):
            raise ValueError("Setting this parent would create a cycle.")
        self.set({"parent_id": new_parent_id})

    @property
    def data(self) -> pd.Series:
        data = pd.Series(data=self.timeseries_data.i_data)
        try:
            data.index = pd.to_datetime(data.index)
        except Exception:
            valid_dates = pd.to_datetime(data.index, errors="coerce")
            data = data[valid_dates.notna()]
            data.index = pd.to_datetime(data.index)
            # keep storage normalized
            self.timeseries_data.set({"i_data": data.to_dict()})
        data = data.map(lambda x: pd.to_numeric(x, errors="coerce")).dropna()
        data.name = self.code
        return data.sort_index()

    @data.setter
    def data(self, data: Union[pd.Series, Dict[Union[date, str], float]]) -> None:
        if isinstance(data, dict):
            data = pd.Series(data)

        # normalize index and values
        data.index = pd.to_datetime(data.index, errors="coerce")
        data = pd.to_numeric(data, errors="coerce")
        data = data.dropna()
        data = data[~data.index.isna()]
        data = data.sort_index()

        if data.empty:
            return

        # Update self
        i_data = self.timeseries_data.i_data.copy()
        i_data.update(data.to_dict())

        # Persist child first
        self.set(
            {
                "start": pd.to_datetime(list(i_data.keys())).min(),
                "end": pd.to_datetime(list(i_data.keys())).max(),
                "num_data": len(i_data),
            }
        )
        self.timeseries_data.set({"i_data": i_data})

        # Then feed to parent (append/merge semantics)
        self._feed_to_parent(data)

    def _feed_to_parent(self, new_data: pd.Series) -> None:
        """
        Merge `new_data` into the parent series (if any).
        Child values overwrite parent for overlapping dates.
        """
        parent = self._get_parent()
        if parent is None:
            return

        p_i_data = parent.timeseries_data.i_data.copy()
        p_i_data.update(new_data.to_dict())

        # Recompute parent metadata from merged keys
        # Convert keys to datetime safely (keys may be date or str)
        p_index = pd.to_datetime(list(p_i_data.keys()), errors="coerce")
        # Filter out any non-parseable keys to be safe
        keep_mask = ~pd.isna(p_index)
        if keep_mask.any():
            # rebuild dict with only valid keys
            valid_keys = [k for k, keep in zip(p_i_data.keys(), keep_mask) if keep]
            p_i_data = {k: p_i_data[k] for k in valid_keys}
            p_index = p_index[keep_mask]
        else:
            # if somehow all invalid, just clear
            p_i_data = {}
            p_index = pd.to_datetime([])

        parent.timeseries_data.set({"i_data": p_i_data})

        if len(p_i_data) > 0:
            parent.set(
                {
                    "start": p_index.min(),
                    "end": p_index.max(),
                    "num_data": len(p_i_data),
                }
            )
        else:
            parent.set({"start": None, "end": None, "num_data": 0})

    def reset(self) -> bool:
        self.set({"start": None, "end": None, "num_data": 0})
        self.timeseries_data.set({"i_data": {}})
        return True






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
