"""Timeseries and TimeseriesData ORM models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import pandas as pd
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from ix.common import get_logger
from ix.db.conn import Base
from .cache import _cache_get, _cache_invalidate, _cache_put

logger = get_logger(__name__)


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
    parent_id = Column(UUID(as_uuid=False), ForeignKey("timeseries.id"), nullable=True, index=True)
    remark = Column(Text, default="")
    favorite = Column(Boolean, default=False, nullable=False)
    latest_value = Column(Float, nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    deleted_at = Column(DateTime, nullable=True)

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
            from ix.collectors.crawler import get_yahoo_data

            data = get_yahoo_data(ticker)[field]
        elif source == "Fred":
            from ix.collectors.crawler import get_fred_data

            data = get_fred_data(ticker)[field]
        elif source == "Naver":
            from ix.collectors.crawler import get_naver_data

            data = get_naver_data(ticker)[field]
        else:
            logger.warning("Unsupported source for timeseries update: %s", source)
            return
        self.data = data

    @property
    def data(self):
        """Return timeseries data as pandas Series."""
        from ix.db.conn import Session

        with Session() as session:
            return self._fetch_data_logic(session)

    def _fetch_data_logic(self, session) -> pd.Series:
        """Core logic for fetching and processing timeseries data from a session."""
        code = self.code
        frequency = self.frequency
        ts_id = str(self.id)

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
            except Exception as exc:
                logger.debug("Resample failed for cached %s (freq=%s): %s", code, frequency, exc)
                return cached.sort_index()

        # Cache miss — load full JSONB data
        # Ensure self is associated with this session for relationship access
        merged = session.merge(self, load=False)
        data_record = merged._get_or_create_data_record(session)
        column_data = data_record.data if data_record and data_record.data else {}

        if not column_data or len(column_data) == 0:
            return pd.Series(name=code, dtype=float)

        # Convert JSONB dict to pandas Series
        data_dict = column_data if isinstance(column_data, dict) else {}
        series = pd.Series(data_dict)

        try:
            series.index = pd.to_datetime(series.index)
        except Exception as exc:
            logger.warning("Date parsing failed for %s, cleaning invalid dates: %s", code, exc)
            valid_dates = pd.to_datetime(series.index, errors="coerce")
            series = series[valid_dates.notna()]
            series.index = pd.to_datetime(series.index)
            # Update the stored data if we found corrupted dates
            if len(series) > 0:
                data_record = merged._get_or_create_data_record(session)
                cleaned = {}
                for k, v in series.to_dict().items():
                    try:
                        if hasattr(k, "date"):
                            key = str(k.date())
                        else:
                            key = str(pd.to_datetime(k).date())
                        cleaned[key] = float(v)
                    except Exception as exc:
                        logger.debug("Skipping uncleanable entry %r in %s: %s", k, code, exc)
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
        except Exception as exc:
            logger.debug("Resample failed for %s (freq=%s): %s", code, frequency, exc)
            return series

    @data.setter
    def data(self, data):
        """Set timeseries data from pandas Series or dict."""
        from ix.db.conn import Session

        if isinstance(data, dict):
            data = pd.Series(data)
        data.index = pd.to_datetime(data.index, format="%Y-%m-%d", errors="coerce")
        data = pd.to_numeric(data, errors="coerce")
        data = data.dropna()
        data = data[~data.index.isna()]
        data = data.sort_index()

        if data.empty:
            return

        with Session() as session:
            self._save_data_logic(data, session)

    def _save_data_logic(self, data, session) -> None:
        """Core logic for saving timeseries data to a session."""
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

        # Also invalidate the Series()-level result cache for this code
        from ix.db.query import clear_series_cache
        clear_series_cache(ts.code)

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
                        logger.warning(
                            "Timeseries %s has parent_id equal to self; ignoring.",
                            ts_id,
                        )
                    return None

                # Query for parent
                parent = (
                    session.query(Timeseries).filter(Timeseries.id == parent_id).first()
                )
                return parent
        except Exception as exc:
            logger.warning("Failed to get parent for timeseries %s: %s", getattr(self, "id", None), exc)
            return None

    def _detect_cycle(self, candidate_parent_id: Optional[str]) -> bool:
        """Detect if setting parent would create a cycle."""
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
