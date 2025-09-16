from typing import Annotated, Dict, Optional, Union, List, Literal
from bunnet import Document, Indexed
from datetime import date, datetime
import pandas as pd
from pydantic import Field, BaseModel
from ix.misc import get_logger
from bson import ObjectId

logger = get_logger(__name__)

# --- Timeseries Data Models ---

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
    unit: Optional[str] = None
    scale: int = 1
    currency: Optional[str] = None
    country: Optional[str] = None
    parent_id: Optional[str] = Field(default=None)
    remark: str = Field(default="", max_length=None)

    @property
    def timeseries_data(self) -> TimeseriesData:
        tsd = TimeseriesData.find_one({"key": str(self.id)}).run()
        if tsd is None:
            tsd = TimeseriesData(key=str(self.id)).create()
        return tsd

    def _get_parent(self) -> Optional["Timeseries"]:
        if not self.parent_id or str(self.parent_id) == str(self.id):
            if str(self.parent_id) == str(self.id):
                logger.warning("Timeseries %s has parent_id equal to self; ignoring.", self.id)
            return None
        try:
            return Timeseries.get(ObjectId(str(self.parent_id)))
        except Exception:
            return None

    def _detect_cycle(self, candidate_parent_id: Optional[str]) -> bool:
        if not candidate_parent_id:
            return False
        seen = {str(self.id)}
        try:
            cur = Timeseries.find_one(Timeseries.id == ObjectId(str(candidate_parent_id))).run()
        except Exception:
            return False
        while cur is not None:
            if str(cur.id) in seen:
                return True
            seen.add(str(cur.id))
            if not cur.parent_id:
                break
            try:
                cur = Timeseries.find_one(Timeseries.id == ObjectId(str(cur.parent_id))).run()
            except Exception:
                return False
        return False

    def set_parent(self, parent: Optional["Timeseries"]) -> None:
        new_parent_id = None if parent is None else str(parent.id)
        if self._detect_cycle(new_parent_id):
            raise ValueError("Setting this parent would create a cycle.")
        self.set({"parent_id": new_parent_id})

    @property
    def data(self) -> pd.Series:
        data = pd.Series(self.timeseries_data.i_data)
        try:
            data.index = pd.to_datetime(data.index)
        except Exception:
            valid_dates = pd.to_datetime(data.index, errors="coerce")
            data = data[valid_dates.notna()]
            data.index = pd.to_datetime(data.index)
            self.timeseries_data.set({"i_data": data.to_dict()})
        data = data.map(lambda x: pd.to_numeric(x, errors="coerce")).dropna()
        data.name = self.code
        try:
            return data.sort_index().resample(str(self.frequency)).last()
        except:
            return data

    @data.setter
    def data(self, data: Union[pd.Series, Dict[Union[date, str], float]]) -> None:
        if isinstance(data, dict):
            data = pd.Series(data)
        data.index = pd.to_datetime(data.index, errors="coerce")
        data = pd.to_numeric(data, errors="coerce")
        data = data.dropna()
        data = data[~data.index.isna()]
        data = data.sort_index()
        if data.empty:
            return
        i_data = self.timeseries_data.i_data.copy()
        i_data.update(data.to_dict())
        self.set({
            "start": pd.to_datetime(list(i_data.keys())).min(),
            "end": pd.to_datetime(list(i_data.keys())).max(),
            "num_data": len(i_data),
        })
        self.timeseries_data.set({"i_data": i_data})
        self._feed_to_parent(data)

    def _feed_to_parent(self, new_data: pd.Series) -> None:
        parent = self._get_parent()
        if parent is None:
            return
        p_i_data = parent.timeseries_data.i_data.copy()
        p_i_data.update(new_data.to_dict())
        p_index = pd.to_datetime(list(p_i_data.keys()), errors="coerce")
        keep_mask = ~pd.isna(p_index)
        if keep_mask.any():
            valid_keys = [k for k, keep in zip(p_i_data.keys(), keep_mask) if keep]
            p_i_data = {k: p_i_data[k] for k in valid_keys}
            p_index = p_index[keep_mask]
        else:
            p_i_data = {}
            p_index = pd.to_datetime([])
        parent.timeseries_data.set({"i_data": p_i_data})
        if len(p_i_data) > 0:
            parent.set({
                "start": p_index.min(),
                "end": p_index.max(),
                "num_data": len(p_i_data),
            })
        else:
            parent.set({"start": None, "end": None, "num_data": 0})

    def reset(self) -> bool:
        self.set({"start": None, "end": None, "num_data": 0})
        self.timeseries_data.set({"i_data": {}})
        return True

# --- Other Data Models ---

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
    code: Optional[str] = None
    name: Optional[str] = None

class Universe(Document):
    name: Optional[str] = None
    assets: Optional[List[Asset]] = None

    @classmethod
    def from_name(cls, name: str) -> "Universe":
        universe = cls.find_one({"name" : name}).run()
        if not universe:
            raise KeyError
        return universe

    @classmethod
    def create_from_assets(cls, assets: list[Asset]) -> "Universe":
        return


    def get_series(
        self,
        field: str = "PX_LAST",
        freq: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        from ix.db.query import MultiSeries
        codes = [f"{asset.name}={asset.code}" for asset in self.assets]
        multiseries = MultiSeries(codes=codes, field=field, freq=freq)
        if start:
            multiseries = multiseries.loc[start:]
        if end:
            multiseries = multiseries.loc[:end]
        return multiseries

    def get_pct_change(self, periods: int = 1) -> pd.DataFrame:
        return self.get_series(field="PX_LAST").pct_change(periods=periods)





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
        return cls.get_user(username=username) is not None

class Insight(Document):
    """
    Represents an insight with metadata, while the actual file content is stored in GridFS.
    """
    issuer: str = "Unnamed"
    name: str = "Unnamed"
    published_date: date = Field(default_factory=date.today)
    summary: Optional[str] = None

    def save_content(self, content: bytes) -> bool:
        from .boto import Boto
        return Boto().save_pdf(pdf_content=content, filename=f"{self.id}.pdf")

    def get_content(self) -> bytes:
        from .boto import Boto
        return Boto().get_pdf(filename=f"{self.id}.pdf")

class TacticalView(Document):
    views: dict
    published_date: datetime

    @classmethod
    def pre_save(cls, document):
        if not document.published_date:
            document.published_date = datetime.now()
        return document

ValidSources = Literal["Yahoo", "Fred", "Infomax", "Eikon", "FactSet", "Bloomberg"]

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
