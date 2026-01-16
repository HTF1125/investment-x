from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    DateTime,
    Text,
    ForeignKey,
    LargeBinary,
    Boolean,
    text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID
from datetime import date, datetime
from typing import Optional, Dict
from ix.db.conn import Base
from .user import User
from .telegram import TelegramMessage

# Re-export Base for convenience
__all__ = [
    "Base",
    "Timeseries",
    "TimeseriesData",
    "Universe",
    "EconomicCalendar",
    "TacticalView",
    "User",
    "TelegramMessage",
    "Insights",
]


class Timeseries(Base):
    """Timeseries model with metadata and associated data payload."""

    __tablename__ = "timeseries"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    code = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    provider = Column(String, nullable=True)
    asset_class = Column(String, nullable=True)
    category = Column(String, nullable=True)
    start = Column(Date, nullable=True)
    end = Column(Date, nullable=True)
    num_data = Column(Integer, nullable=True)
    source = Column(String, nullable=True)
    source_code = Column(String, nullable=True)
    frequency = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    scale = Column(Integer, default=1)
    currency = Column(String, nullable=True)
    country = Column(String, nullable=True)
    parent_id = Column(UUID(as_uuid=False), ForeignKey("timeseries.id"), nullable=True)
    remark = Column(Text, default="")
    favorite = Column(Boolean, default=False, nullable=False)

    # Legacy JSONB column retained for migration/backward compatibility.
    created = Column(DateTime, default=datetime.now, nullable=False)
    updated = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )
    num_data_queried = Column(Integer, default=0, nullable=False)

    data_record = relationship(
        "TimeseriesData",
        uselist=False,
        back_populates="timeseries",
        cascade="all, delete-orphan",
        lazy="select",
        passive_deletes=True,
    )

    def _get_or_create_data_record(self, session):
        """Ensure a TimeseriesData record exists."""
        from sqlalchemy.exc import SQLAlchemyError

        record = (
            session.query(TimeseriesData)
            .filter(TimeseriesData.timeseries_id == self.id)
            .first()
        )
        if record is None:
            record = TimeseriesData(timeseries_id=self.id, data={})
            session.add(record)
            # Flush to ensure the record is persisted before returning
            try:
                session.flush()
            except SQLAlchemyError:
                session.rollback()
                raise

        return record

    def update_data(self) -> None:
        if self.source_code is None:
            raise ValueError(f"Source code is not set for {self.code}")
        ticker, field = str(self.source_code).rsplit(":", 1)
        source = str(self.source)
        if source == "Yahoo":
            from ix.misc.crawler import get_yahoo_data

            data = get_yahoo_data(ticker)[field]
        elif source == "Fred":
            from ix.misc.crawler import get_fred_data

            data = get_fred_data(ticker)[field]
        elif source == "Naver":
            from ix.misc.crawler import get_naver_data

            data = get_naver_data(ticker)[field]
        else:
            print(f"Unsupported source: {source}")
            return
        self.data = data

    @property
    def data(self):
        """Return timeseries data as pandas Series."""
        import pandas as pd
        from ix.db.conn import Session

        # Reload the object from the database within session context
        with Session() as session:
            # Reload the object by querying with the same ID
            ts = session.query(Timeseries).filter(Timeseries.id == self.id).first()
            if ts is None:
                # If not found, return empty series
                return pd.Series(
                    name=self.code if hasattr(self, "code") else "", dtype=float
                )

            # Increment num_data_queried
            ts.num_data_queried = (ts.num_data_queried or 0) + 1
            data_record = ts._get_or_create_data_record(session)
            column_data = data_record.data if data_record and data_record.data else {}
            code = ts.code
            frequency = ts.frequency

        if not column_data or len(column_data) == 0:
            return pd.Series(name=code, dtype=float)

        # Convert JSONB dict to pandas Series
        # JSONB stores dates as strings, convert them back
        data_dict = column_data if isinstance(column_data, dict) else {}
        series = pd.Series(data_dict)

        try:
            series.index = pd.to_datetime(series.index)
        except Exception:
            valid_dates = pd.to_datetime(series.index, errors="coerce")
            series = series[valid_dates.notna()]
            series.index = pd.to_datetime(series.index)
            # Update the stored data
            if len(series) > 0:
                from ix.db.conn import Session

                with Session() as session:
                    ts = (
                        session.query(Timeseries)
                        .filter(Timeseries.id == self.id)
                        .first()
                    )
                    if ts is not None:
                        data_record = ts._get_or_create_data_record(session)
                        cleaned = {}
                        for k, v in series.to_dict().items():
                            try:
                                if hasattr(k, "date"):
                                    key = str(k.date())
                                else:
                                    key = str(pd.to_datetime(k).date())
                                cleaned[key] = float(v)
                            except Exception:
                                continue
                        data_record.data = cleaned
                        data_record.updated = datetime.now()

        series = series.map(lambda x: pd.to_numeric(x, errors="coerce")).dropna()
        series.name = code
        try:
            if frequency and len(series) > 0:
                return series.sort_index().resample(str(frequency)).last().dropna()
            else:
                return series.sort_index()
        except:
            return series.sort_index()

    @data.setter
    def data(self, data):
        """Set timeseries data from pandas Series or dict."""
        import pandas as pd
        from ix.db.conn import Session

        if isinstance(data, dict):
            data = pd.Series(data)
        data.index = pd.to_datetime(data.index, errors="coerce")
        data = pd.to_numeric(data, errors="coerce")
        data = data.dropna()
        data = data[~data.index.isna()]
        data = data.sort_index()

        if data.empty:
            return

        with Session() as session:
            ts = session.query(Timeseries).filter(Timeseries.id == self.id).first()
            if ts is None:
                return

            data_record = ts._get_or_create_data_record(session)
            current_data = (
                data_record.data.copy() if data_record and data_record.data else {}
            )

            # Convert dates to strings for storage
            new_data = {}
            for k, v in data.to_dict().items():
                if hasattr(k, "date"):
                    date_str = str(k.date())
                elif isinstance(k, str):
                    date_str = k
                else:
                    date_str = str(pd.to_datetime(k).date())
                new_data[date_str] = float(v)

            current_data.update(new_data)
            data_record.data = current_data
            data_record.updated = datetime.now()
            ts.start = data.index.min().date() if len(data.index) > 0 else None
            ts.end = data.index.max().date() if len(data.index) > 0 else None
            ts.num_data = len(data)
            ts.updated = datetime.now()

        # Feed to parent if exists
        self._feed_to_parent(data)

    def _get_parent(self):
        """Get parent timeseries."""
        from ix.db.models import Timeseries
        from ix.db.conn import Session

        try:
            with Session() as session:
                # Reload the object to get attributes within session
                ts = session.query(Timeseries).filter(Timeseries.id == self.id).first()
                if ts is None:
                    return None

                parent_id = ts.parent_id
                ts_id = ts.id

                if not parent_id or str(parent_id) == str(ts_id):
                    if str(parent_id) == str(ts_id):
                        import logging

                        logger = logging.getLogger(__name__)
                        logger.warning(
                            f"Timeseries {ts_id} has parent_id equal to self; ignoring."
                        )
                    return None

                # Query for parent
                parent = (
                    session.query(Timeseries).filter(Timeseries.id == parent_id).first()
                )
                return parent
        except Exception:
            return None

    def _detect_cycle(self, candidate_parent_id: Optional[str]) -> bool:
        """Detect if setting parent would create a cycle."""
        from ix.db.models import Timeseries
        from ix.db.conn import Session

        if not candidate_parent_id:
            return False

        try:
            with Session() as session:
                # Reload the object to get id within session
                ts = session.query(Timeseries).filter(Timeseries.id == self.id).first()
                if ts is None:
                    return False

                seen = {str(ts.id)}
                cur = (
                    session.query(Timeseries)
                    .filter(Timeseries.id == candidate_parent_id)
                    .first()
                )
                while cur is not None:
                    if str(cur.id) in seen:
                        return True
                    seen.add(str(cur.id))
                    if not cur.parent_id:
                        break
                    cur = (
                        session.query(Timeseries)
                        .filter(Timeseries.id == cur.parent_id)
                        .first()
                    )
        except Exception:
            return False
        return False

    def set_parent(self, parent):
        """Set parent timeseries."""
        from ix.db.conn import Session

        new_parent_id = None if parent is None else str(parent.id)
        if self._detect_cycle(new_parent_id):
            raise ValueError("Setting this parent would create a cycle.")

        with Session() as session:
            # Reload the object from the database
            ts = session.query(Timeseries).filter(Timeseries.id == self.id).first()
            if ts is not None:
                ts.parent_id = new_parent_id

    def _feed_to_parent(self, new_data):
        """Feed data to parent timeseries."""
        from ix.db.conn import Session

        parent = self._get_parent()
        if parent is None:
            return

        import pandas as pd

        with Session() as session:
            parent_ts = (
                session.query(Timeseries).filter(Timeseries.id == parent.id).first()
            )
            if parent_ts is None:
                return

            data_record = parent_ts._get_or_create_data_record(session)
            parent_data = (
                data_record.data.copy() if data_record and data_record.data else {}
            )

            # Convert new_data to dict format with date strings
            new_data_dict = {}
            for k, v in new_data.to_dict().items():
                if hasattr(k, "date"):
                    date_str = str(k.date())
                elif isinstance(k, str):
                    date_str = k
                else:
                    date_str = str(pd.to_datetime(k).date())
                new_data_dict[date_str] = float(v)

            parent_data.update(new_data_dict)

            # Clean invalid dates
            parent_data_clean = {}
            for k, v in parent_data.items():
                try:
                    pd.to_datetime(k)
                    parent_data_clean[k] = v
                except Exception:
                    continue

            data_record.data = parent_data_clean
            data_record.updated = datetime.now()
            if len(parent_data_clean) > 0:
                dates = pd.to_datetime(list(parent_data_clean.keys()), errors="coerce")
                valid_dates = dates[~pd.isna(dates)]
                if len(valid_dates) > 0:
                    parent_ts.start = valid_dates.min().date()
                    parent_ts.end = valid_dates.max().date()
                    parent_ts.num_data = len(parent_data_clean)
            else:
                parent_ts.start = None
                parent_ts.end = None
                parent_ts.num_data = 0
            parent_ts.updated = datetime.now()

    def reset(self) -> bool:
        """Reset timeseries data."""
        from ix.db.conn import Session

        with Session() as session:
            # Reload the object from the database
            ts = session.query(Timeseries).filter(Timeseries.id == self.id).first()
            if ts is not None:
                data_record = ts._get_or_create_data_record(session)
                data_record.data = {}
                data_record.updated = datetime.now()
                ts.start = None
                ts.end = None
                ts.num_data = 0
                ts.updated = datetime.now()
                return True
            return False


class TimeseriesData(Base):
    """Stores timeseries payload data separately from metadata."""

    __tablename__ = "timeseries_data"

    timeseries_id = Column(
        UUID(as_uuid=False),
        ForeignKey("timeseries.id", ondelete="CASCADE"),
        primary_key=True,
    )
    data = Column(JSONB, default=dict, nullable=False)
    created = Column(DateTime, default=datetime.now, nullable=False)
    updated = Column(
        DateTime, default=datetime.now, onupdate=datetime.now, nullable=False
    )

    timeseries = relationship(
        "Timeseries",
        back_populates="data_record",
        lazy="select",
    )


class Universe(Base):
    """Universe model."""

    __tablename__ = "universe"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    name = Column(String, nullable=True)
    assets = Column(JSONB, default=list)  # List of Asset dicts

    @classmethod
    def from_name(cls, name: str):
        """Get universe by name."""
        from ix.db.conn import Session

        with Session() as session:
            universe = session.query(cls).filter(cls.name == name).first()
            if not universe:
                raise KeyError
            return universe

    def add_asset(self, asset: Dict[str, Optional[str]]) -> None:
        """Add asset to universe."""
        assets = self.assets.copy() if self.assets else []
        if isinstance(asset, dict):
            assets.append(asset)
        else:
            # Handle case where asset might be an object with code/name attributes
            assets.append(
                {
                    "code": getattr(asset, "code", None),
                    "name": getattr(asset, "name", None),
                }
            )
        self.assets = assets

    def delete_asset(self, asset: Dict[str, Optional[str]]) -> None:
        """Delete asset from universe."""
        assets = self.assets.copy() if self.assets else []
        if isinstance(asset, dict):
            asset_dict = asset
        else:
            asset_dict = {
                "code": getattr(asset, "code", None),
                "name": getattr(asset, "name", None),
            }
        assets = [
            a
            for a in assets
            if not (
                a.get("code") == asset_dict.get("code")
                and a.get("name") == asset_dict.get("name")
            )
        ]
        self.assets = assets

    def get_series(
        self,
        field: str = "PX_LAST",
        freq: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ):
        """Get series for universe assets."""
        from ix.db.query import D_MultiSeries
        import pandas as pd

        codes = [
            f"{asset.get('name', '')}={asset.get('code', '')}"
            for asset in (self.assets or [])
        ]
        multiseries = D_MultiSeries(codes=codes, field=field, freq=freq)
        if start:
            multiseries = multiseries.loc[start:]
        if end:
            multiseries = multiseries.loc[:end]
        return multiseries

    def get_pct_change(self, periods: int = 1):
        """Get percentage change for universe."""
        return self.get_series(field="PX_LAST").pct_change(periods=periods)


class EconomicCalendar(Base):
    """EconomicCalendar model."""

    __tablename__ = "economic_calendar"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    date = Column(String, nullable=False)
    time = Column(String, nullable=False)
    event = Column(String, nullable=False)
    zone = Column(String, nullable=True)
    currency = Column(String, nullable=True)
    importance = Column(String, nullable=True)
    actual = Column(String, nullable=True)
    forecast = Column(String, nullable=True)
    previous = Column(String, nullable=True)

    @classmethod
    def get_dataframe(cls):
        """Get economic calendar as DataFrame."""
        import pandas as pd
        from ix.db.conn import Session

        with Session() as session:
            releases = session.query(cls).all()
            data = [
                {
                    "id": str(r.id),
                    "date": r.date,
                    "time": r.time,
                    "event": r.event,
                    "zone": r.zone,
                    "currency": r.currency,
                    "importance": r.importance,
                    "actual": r.actual,
                    "forecast": r.forecast,
                    "previous": r.previous,
                }
                for r in releases
            ]
            df = pd.DataFrame(data)
            if not df.empty:
                df = df.set_index("id")
            return df


class TacticalView(Base):
    """TacticalView model for storing tactical asset allocation views."""

    __tablename__ = "tactical_view"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    views = Column(JSONB, default=dict)  # Store tactical views as JSONB
    published_date = Column(DateTime, default=datetime.now, nullable=False)

    def __repr__(self):
        return f"<TacticalView(id={self.id}, published_date={self.published_date})>"


class Insights(Base):
    """Insights model for storing PDF summaries and metadata."""

    __tablename__ = "insights"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    published_date = Column(Date, nullable=True)
    issuer = Column(String, nullable=True)
    name = Column(String, nullable=True)
    status = Column(String, default="new")
    summary = Column(Text, nullable=True)
    pdf_content = Column(LargeBinary, nullable=True)
    hash = Column(String, nullable=True)
    created = Column(DateTime, default=datetime.now, nullable=False)


def all():
    """Return all model classes."""
    return [
        EconomicCalendar,
        Universe,
        Timeseries,
        TacticalView,
        Insights,
    ]
