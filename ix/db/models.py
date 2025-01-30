from typing import Annotated, Dict, Optional, Union, List
from bunnet import Document, Indexed
from datetime import date, datetime
import pandas as pd
from ix.misc import get_logger
from bson import ObjectId
from pydantic import BaseModel, Field


logger = get_logger(__name__)


class DataSource(Document):
    meta_id: str
    field: str
    s_code: str
    s_field: str
    source: str = "YAHOO"


class Metadata(Document):
    code: Annotated[str, Indexed(unique=True)]
    exchange: Optional[str] = None
    market: Optional[str] = None
    id_isin: Optional[str] = None
    name: Optional[str] = None
    remark: Optional[str] = None
    disabled: bool = False

    def ds(self) -> List[DataSource]:
        if not self.id:
            raise
        ds = DataSource.find_many({"meta_id": str(self.id)}).run()
        if ds is None:
            raise
        return ds

    def ts(self, field: str = "PX_LAST") -> "TimeSeries":
        if not self.id:
            raise
        ts = TimeSeries.find_one({"meta_id": str(self.id), "field": field}).run()
        if ts is None:
            logger.debug(f"Create new TimeSeries for {self.code} - {field}")
            return TimeSeries(meta_id=str(self.id), field=field).create()
        return ts

    def tp(self, field: str = "PX_LAST") -> "TimePoint":
        if not self.id:
            raise
        tp = TimePoint.find_one({"meta_id": str(self.id), "field": field}).run()
        if tp is None:
            logger.debug(f"Create new TimeSeries for {self.code} - {field}")
            return TimePoint(meta_id=str(self.id), field=field).create()
        return tp


class TimeSeries(Document):
    meta_id: str
    field: str
    latest_date: Optional[date] = None
    i_data: Dict[date, float] = {}

    @property
    def metadata(self) -> Metadata:
        metadata = Metadata.find_one(Metadata.id == ObjectId(self.meta_id)).run()
        if metadata is None:
            raise
        return metadata

    @property
    def timepoint(self) -> "TimePoint":
        timepoint = TimePoint.find_one(
            {"meta_id": str(self.id), "field": self.field}
        ).run()
        if timepoint:
            return timepoint
        return TimePoint(meta_id=self.meta_id, field=self.field).create()

    @property
    def metadata_code(self) -> str:
        if not ObjectId.is_valid(self.meta_id):  # Make sure 'self.meta_id' is valid
            raise ValueError(
                f"Invalid ObjectId: {self.meta_id}"
            )  # Raise a more meaningful error
        metadata = Metadata.find_one(Metadata.id == ObjectId(self.meta_id)).run()
        if not metadata:
            raise ValueError(
                f"Metadata not found for id {self.meta_id}"
            )  # Raise an error if metadata is not found
        return metadata.code

    @property
    def data(self) -> pd.Series:
        data = pd.Series(data=self.i_data)
        data.index = pd.to_datetime(data.index)
        return data

    @data.setter
    def data(self, data: Union[pd.Series, Dict[date, float]]) -> None:
        if isinstance(data, dict):
            data = pd.Series(data=data)
            data.index = pd.to_datetime(data.index)
        if self.i_data:
            data = data.combine_first(self.data)
        if data is not None:
            data = data.dropna()
            self.set({"latest_date": data.index[-1]})
            self.set({"i_data": data.to_dict()})
            self.timepoint.set({"data": data.iloc[-1]})
            logger.info(f"Update {self.metadata_code} {self.field}")


class TimePoint(Document):
    meta_id: str
    field: str
    data: str | int | float | None = None


class InsightSourceBase(BaseModel):
    url: str
    name: str = "Unnamed"
    frequency: str = "Unclassified"
    remark: Optional[str] = None
    last_visited: datetime = Field(default_factory=datetime.now)


class InsightSource(InsightSourceBase, Document): ...


class MarketCommentary(Document):

    asofdate: Annotated[date, Indexed(unique=True)] = Field(default_factory=date.today)
    frequency: str = "Daily"
    content: str = ""


class Prediction(Document):
    code: Annotated[str, Indexed(unique=True)]
    name: Optional[str] = None
    features: Dict[str, Dict[date, float]]
    target: Dict[date, float]
    prediction: Dict[date, float]
