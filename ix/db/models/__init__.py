from sqlalchemy import (
    Column,
    Index,
    Integer,
    String,
    Date,
    DateTime,
    Text,
    ForeignKey,
    LargeBinary,
    Boolean,
    Float,
    text,
    func,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB, UUID
from datetime import date, datetime
from typing import Optional, Dict
from ix.db.conn import Base
from ix.misc import get_logger
from .user import User
from .telegram import TelegramMessage
from .charts import Charts
from .task_process import TaskProcess
from .news_item import NewsItem
from .logs import Logs
from .macro_outlook import MacroOutlook
from .research_report import ResearchReport
from .whiteboard import Whiteboard
from .collector_state import CollectorState
from .institutional_holding import InstitutionalHolding
import pandas as pd
import threading

logger = get_logger(__name__)

# ── In-memory cache for parsed timeseries data ──
# Key: timeseries_id (str)
# Value: (updated_timestamp: datetime, parsed_series: pd.Series)
#
# threading.Lock is appropriate here: all access comes from sync ``def``
# route handlers (run in FastAPI's default threadpool) or from
# ``asyncio.to_thread()`` calls.  No coroutine ever touches the cache
# directly, so the lock never blocks the event loop.
_ts_cache: Dict[str, tuple] = {}
_ts_cache_lock = threading.Lock()
_TS_CACHE_MAX = 512  # max entries before eviction


def _cache_get(ts_id: str, updated: Optional[datetime]) -> Optional[pd.Series]:
    """Return cached Series if still valid, else None."""
    with _ts_cache_lock:
        entry = _ts_cache.get(str(ts_id))
    if entry is None:
        return None
    cached_updated, cached_series = entry
    if updated is not None and cached_updated == updated:
        return cached_series.copy()
    return None


def _cache_put(ts_id: str, updated: Optional[datetime], series: pd.Series) -> None:
    """Store parsed Series in cache."""
    with _ts_cache_lock:
        if len(_ts_cache) >= _TS_CACHE_MAX:
            # Evict oldest 25%
            to_remove = list(_ts_cache.keys())[: _TS_CACHE_MAX // 4]
            for k in to_remove:
                _ts_cache.pop(k, None)
        _ts_cache[str(ts_id)] = (updated, series.copy())


def _cache_invalidate(ts_id: str) -> None:
    """Remove a specific entry from cache."""
    with _ts_cache_lock:
        _ts_cache.pop(str(ts_id), None)


# Re-export Base for convenience
__all__ = [
    "Base",
    "Timeseries",
    "TimeseriesData",
    "Universe",
    "TacticalView",
    "User",
    "TelegramMessage",
    "Insights",
    "Charts",
    "TaskProcess",
    "NewsItem",
    "Logs",
    "MacroOutlook",
    "ResearchReport",
    "Whiteboard",
    "CollectorState",
    "InstitutionalHolding",
]


def all():
    """Return all model classes."""
    return [
        User,
        Timeseries,
        TimeseriesData,
        Universe,
        TacticalView,
        Insights,
        Charts,
        TaskProcess,
        NewsItem,
        TelegramMessage,
        Logs,
        MacroOutlook,
        ResearchReport,
        Whiteboard,
        CollectorState,
        InstitutionalHolding,
    ]


class Timeseries(Base):
    """Timeseries model with metadata and associated data payload."""

    __tablename__ = "timeseries"
    __table_args__ = (
        Index("ix_timeseries_source_code", "source", "code"),
        Index("ix_timeseries_source_source_code", "source", "source_code"),
    )

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    code = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=True)
    provider = Column(String, nullable=True)
    asset_class = Column(String, nullable=True)
    category = Column(String, nullable=True, index=True)
    start = Column(Date, nullable=True)
    end = Column(Date, nullable=True)
    num_data = Column(Integer, nullable=True)
    source = Column(String, nullable=True, index=True)
    source_code = Column(String, nullable=True)
    frequency = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    scale = Column(Integer, default=1)
    currency = Column(String, nullable=True)
    country = Column(String, nullable=True)
    parent_id = Column(UUID(as_uuid=False), ForeignKey("timeseries.id"), nullable=True)
    remark = Column(Text, default="")
    favorite = Column(Boolean, default=False, nullable=False)
    latest_value = Column(Float, nullable=True)

    # Legacy JSONB column retained for migration/backward compatibility.
    created = Column(DateTime, default=func.now(), nullable=False)
    updated = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
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
            logger.warning("Unsupported source for timeseries update: %s", source)
            return
        self.data = data

    @property
    def data(self):
        """Return timeseries data as pandas Series."""
        import pandas as pd
        from ix.db.conn import Session, custom_chart_session

        # 1. Check for a shared session in the context (optimization)
        session = custom_chart_session.get()
        is_shared = session is not None

        if is_shared:
            # Use the shared session without a 'with' block (caller manages it)
            return self._fetch_data_logic(session)
        else:
            # Fallback to creating a new scoped session
            with Session() as session:
                return self._fetch_data_logic(session)

    def _fetch_data_logic(self, session) -> pd.Series:
        """Core logic for fetching and processing timeseries data from a session."""
        import pandas as pd

        # Reload the object to ensure it's attached to the current session
        ts = session.query(Timeseries).filter(Timeseries.id == self.id).first()
        if ts is None:
            return pd.Series(
                name=self.code if hasattr(self, "code") else "", dtype=float
            )

        code = ts.code
        frequency = ts.frequency
        ts_id = str(ts.id)

        # Check cache: query only the updated timestamp (no JSONB load)
        data_record_ref = (
            session.query(TimeseriesData.updated)
            .filter(TimeseriesData.timeseries_id == ts_id)
            .first()
        )
        record_updated = data_record_ref[0] if data_record_ref else None

        cached = _cache_get(ts_id, record_updated)
        if cached is not None:
            cached.name = code
            try:
                if frequency and len(cached) > 0:
                    return cached.sort_index().resample(str(frequency)).last().dropna()
                else:
                    return cached.sort_index()
            except Exception:
                return cached.sort_index()

        # Cache miss — load full JSONB data
        data_record = ts._get_or_create_data_record(session)
        column_data = data_record.data if data_record and data_record.data else {}

        if not column_data or len(column_data) == 0:
            return pd.Series(name=code, dtype=float)

        # Convert JSONB dict to pandas Series
        data_dict = column_data if isinstance(column_data, dict) else {}
        series = pd.Series(data_dict)

        try:
            series.index = pd.to_datetime(series.index)
        except Exception:
            valid_dates = pd.to_datetime(series.index, errors="coerce")
            series = series[valid_dates.notna()]
            series.index = pd.to_datetime(series.index)
            # Update the stored data if we found corrupted dates
            if len(series) > 0:
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
        series = series.sort_index()
        series.name = code

        # Store raw (pre-resample) series in cache
        _cache_put(ts_id, data_record.updated, series)

        try:
            if frequency and len(series) > 0:
                return series.resample(str(frequency)).last().dropna()
            else:
                return series
        except Exception:
            return series

    @data.setter
    def data(self, data):
        """Set timeseries data from pandas Series or dict."""
        import pandas as pd
        from ix.db.conn import Session, custom_chart_session

        if isinstance(data, dict):
            data = pd.Series(data)
        data.index = pd.to_datetime(data.index, format="%Y-%m-%d", errors="coerce")
        data = pd.to_numeric(data, errors="coerce")
        data = data.dropna()
        data = data[~data.index.isna()]
        data = data.sort_index()

        if data.empty:
            return

        # Optimization: use shared session if available
        session_ctx = custom_chart_session.get()
        if session_ctx:
            self._save_data_logic(data, session_ctx)
        else:
            with Session() as session:
                self._save_data_logic(data, session)

    def _save_data_logic(self, data, session) -> None:
        """Core logic for saving timeseries data to a session."""
        import pandas as pd

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

        # Compute latest_value from the complete dataset
        if current_data:
            # Vectorized datetime validation and sorting
            temp_series = pd.Series(current_data)
            temp_series.index = pd.to_datetime(
                temp_series.index, format="%Y-%m-%d", errors="coerce"
            )
            temp_series = temp_series[temp_series.index.notna()].sort_index()

            if not temp_series.empty:
                latest_date_str = str(temp_series.index[-1].date())
                latest_val = float(temp_series.iloc[-1])
                ts.latest_value = latest_val
                ts.end = temp_series.index[-1].date()
                ts.start = temp_series.index[0].date()
                ts.num_data = len(temp_series)
            else:
                ts.latest_value = None
                ts.start = None
                ts.end = None
                ts.num_data = 0
        else:
            ts.latest_value = None
            ts.start = None
            ts.end = None
            ts.num_data = 0

        ts.updated = datetime.now()

        # Invalidate cache for this series (and parent if exists)
        _cache_invalidate(str(ts.id))

        # Feed to parent if exists
        self._feed_to_parent_with_session(data, session)

    def _feed_to_parent_with_session(self, new_data, session):
        """Feed data to parent timeseries using an existing session."""
        ts = session.query(Timeseries).filter(Timeseries.id == self.id).first()
        if not ts or not ts.parent_id:
            return

        parent_ts = (
            session.query(Timeseries).filter(Timeseries.id == ts.parent_id).first()
        )
        if parent_ts is None:
            return

        import pandas as pd

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

        # Clean invalid dates using vectorization
        if len(parent_data) > 0:
            temp_series = pd.Series(parent_data)
            temp_series.index = pd.to_datetime(
                temp_series.index, format="%Y-%m-%d", errors="coerce"
            )
            temp_series = temp_series[temp_series.index.notna()].sort_index()

            # Reconstruct the cleaned string dictionary
            parent_data_clean = {
                str(k.date()): float(v) for k, v in temp_series.items()
            }
            data_record.data = parent_data_clean
            data_record.updated = datetime.now()

            if not temp_series.empty:
                parent_ts.start = temp_series.index[0].date()
                parent_ts.end = temp_series.index[-1].date()
                parent_ts.num_data = len(parent_data_clean)
                parent_ts.latest_value = float(temp_series.iloc[-1])
            else:
                parent_ts.start = None
                parent_ts.end = None
                parent_ts.num_data = 0
                parent_ts.latest_value = None
        else:
            data_record.data = {}
            data_record.updated = datetime.now()
            parent_ts.start = None
            parent_ts.end = None
            parent_ts.num_data = 0
            parent_ts.latest_value = None
        parent_ts.updated = datetime.now()
        _cache_invalidate(str(parent_ts.id))

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
        except Exception as exc:
            logger.warning(
                "Failed to validate parent cycle for timeseries %s -> %s: %s",
                getattr(self, "id", None),
                candidate_parent_id,
                exc,
            )
            raise ValueError("Unable to validate parent relationship.") from exc
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
        """Feed data to parent timeseries (opens a new session)."""
        from ix.db.conn import Session

        with Session() as session:
            self._feed_to_parent_with_session(new_data, session)

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
                ts.latest_value = None
                ts.updated = datetime.now()
                _cache_invalidate(str(ts.id))
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
    created = Column(DateTime, default=func.now(), nullable=False)
    updated = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

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
        from ix.db.query import Series as QuerySeries

        series_list = []
        for asset in self.assets or []:
            alias = asset.get("name", "")
            code = asset.get("code", "")
            s = QuerySeries(f"{code}:{field}", freq=freq)
            if alias:
                s.name = alias
            if not s.empty:
                series_list.append(s)
        if not series_list:
            return pd.DataFrame()
        multiseries = pd.concat(series_list, axis=1)
        multiseries.index = pd.to_datetime(multiseries.index)
        multiseries = multiseries.sort_index()
        multiseries.index.name = "Date"
        if start:
            multiseries = multiseries.loc[start:]
        if end:
            multiseries = multiseries.loc[:end]
        return multiseries

    def get_pct_change(self, periods: int = 1):
        """Get percentage change for universe."""
        return self.get_series(field="PX_LAST").pct_change(periods=periods)



class TacticalView(Base):
    """TacticalView model for storing tactical asset allocation views."""

    __tablename__ = "tactical_view"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    views = Column(JSONB, default=dict)  # Store tactical views as JSONB
    published_date = Column(DateTime, default=func.now(), nullable=False)

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
    storage_path = Column(String(512), nullable=True)
    pdf_content = Column(LargeBinary, nullable=True)
    hash = Column(String, nullable=True)
    created = Column(DateTime, default=func.now(), nullable=False)
