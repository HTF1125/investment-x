from typing import Annotated, Dict, Optional, Union, List
from bunnet import Document, Indexed
from datetime import date, datetime
import pandas as pd
from ix.misc import get_logger
from bson import ObjectId
from pydantic import BaseModel, Field


logger = get_logger(__name__)


class MetaDataBase(BaseModel):
    code: Annotated[str, Indexed(unique=True)]
    name: Optional[str] = None
    exchange: Optional[str] = None
    market: Optional[str] = None
    source: str = "YAHOO"
    bloomberg: Optional[str] = None
    fred: Optional[str] = None
    yahoo: Optional[str] = None
    remark: Optional[str] = None
    disabled: bool = False
    fields: Optional[list[str]] = ["PX_LAST"]


class DataSource(BaseModel):

    field: str
    s_code: str
    s_field: str
    source: str = "YAHOO"


class MetaData(Document):
    code: Annotated[str, Indexed(unique=True)]
    name: Optional[str] = None
    exchange: Optional[str] = None
    market: Optional[str] = None
    source: str = "YAHOO"
    bloomberg: Optional[str] = None
    fred: Optional[str] = None
    yahoo: Optional[str] = None
    remark: Optional[str] = None
    disabled: bool = False
    data_sources: List[DataSource] = []

    def ts(self, field: str = "PX_LAST") -> "TimeSeries":
        if not self.id:
            raise
        ts = TimeSeries.find_one(
            TimeSeries.meta_id == str(self.id),
            TimeSeries.field == field,
        ).run()
        if ts is None:
            logger.info(f"Create new TimeSeries for {self.code} - {field}")
            return TimeSeries(meta_id=str(self.id), field=field).create()
        return ts


class TimeSeries(Document):
    meta_id: str
    field: str
    latest_date: Optional[date] = None
    i_data: Dict[date, float] = {}

    @property
    def metadata_code(self) -> str:
        if not ObjectId.is_valid(self.meta_id):  # Make sure 'self.meta_id' is valid
            raise ValueError(
                f"Invalid ObjectId: {self.meta_id}"
            )  # Raise a more meaningful error
        metadata = MetaData.find_one(MetaData.id == ObjectId(self.meta_id)).run()
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
            self.set({"latest_date": data.index[-1]})
            self.set({"i_data": data.to_dict()})
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
