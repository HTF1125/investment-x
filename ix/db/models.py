from typing import Annotated, Dict, Optional, Union, List
from bunnet import Document, Indexed
from datetime import date, datetime
import pandas as pd
from ix.misc import get_logger
from ix.misc import get_yahoo_data
from ix.misc import get_relative_date
from bson import ObjectId
from pydantic import BaseModel, Field


logger = get_logger(__name__)


def get_performance(px_last: pd.Series) -> dict:
    px_last = px_last.resample("D").last().ffill()
    asofdate = pd.Timestamp(str(px_last.index[-1]))
    level = px_last.loc[asofdate]
    pct_chg = (level / px_last).sub(1).mul(100).round(2)
    out = {}
    for period in ["1D", "1W", "1M", "3M", "6M", "1Y", "3Y", "MTD", "YTD"]:
        r_date = get_relative_date(asofdate=asofdate, period=period)
        try:
            out[f"PCT_CHG_{period}"] = pct_chg.loc[r_date]
        except:
            pass
    return out


class DataSource(Document):
    meta_id: str
    field: str
    s_code: str
    s_field: str
    source: str = "YAHOO"


class Source(BaseModel):
    field: str
    s_code: str
    s_field: str
    source: str = "YAHOO"


from typing import Any


class Metadata(Document):
    code: Annotated[str, Indexed(unique=True)]
    exchange: Optional[str] = None
    market: Optional[str] = None
    id_isin: Optional[str] = None
    name: Optional[str] = None
    remark: Optional[str] = None
    disabled: bool = False
    bbg_ticker: Any = None
    yah_ticker: Any = None
    fre_ticker: Any = None

    def update_px(self):

        if self.yah_ticker:
            ts = get_yahoo_data(code=self.yah_ticker)
            if ts.empty:
                logger.warning(
                    f"No Yahoo data returned for ticker {self.yah_ticker}"
                )
                return False

            # Mapping of source field to metadata field.
            field_mappings = {
                "Open": "PX_OPEN",
                "High": "PX_HIGH",
                "Low": "PX_LOW",
                "Close": "PX_CLOSE",
                "Volume": "PX_VOLUME",
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

                # For PX_LAST, update the TP (timepoint) value and calculate performance.
                if target_field == "PX_LAST":
                    last_value = series.iloc[-1]
                    self.tp(field=target_field).data = last_value
                    logger.debug(
                        f"Set timepoint {target_field} (last value: {last_value}) for code {self.code}"
                    )

                    # Calculate and update performance metrics.
                    performance = get_performance(px_last=series)
                    for perf_field, perf_value in performance.items():
                        self.tp(field=perf_field).data = float(perf_value)
                        logger.debug(
                            f"Set performance field {perf_field} to {perf_value} for code {self.code}"
                        )

                logger.info(
                    f"Successfully updated {target_field} for metadata code: {self.code}"
                )

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
            logger.debug(f"Create new TimePoint for {self.code} - {field}")
            return TimePoint(meta_id=str(self.id), field=field).create()
        return tp


class TimeSeries(Document):
    meta_id: str
    field: str
    latest_date: Optional[date] = None
    i_data: Dict[date | str, str | int | float] = {}

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
        return TimePoint(meta_id=str(self.id), field=self.field).create()

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
        try:
            data.index = pd.to_datetime(data.index)
        except:
            valid_dates = pd.to_datetime(data.index, errors="coerce")
            data = data[valid_dates.notna()]
            data.index = pd.to_datetime(data.index)
            self.set({"i_data" : data.to_dict()})
        return data.sort_index()

    @data.setter
    def data(self, data: Union[pd.Series, Dict[date, float]]) -> None:
        if isinstance(data, dict):
            data = pd.Series(data=data)
            data.index = pd.to_datetime(data.index)
        if self.i_data:
            data = data.combine_first(self.data)
        if data is not None:
            data = data.dropna()
            self.set({"i_data": data.to_dict()})
            tp = self.timepoint
            tp.set({"i_data": float(data.iloc[-1])})
            logger.info(f"Update {self.metadata_code} {self.field}")


class TimePoint(Document):
    meta_id: str
    field: str
    i_data: float | None = None

    @property
    def data(self) -> float | None:
        return self.i_data

    @data.setter
    def data(self, data: float) -> None:
        self.set({"i_data": data})


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
