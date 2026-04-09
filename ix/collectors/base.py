"""Base collector class for all data collectors."""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional
import pandas as pd

from ix.db.conn import Session
from ix.db.models.collector_state import CollectorState
from ix.common import get_logger


class BaseCollector(ABC):
    """Abstract base for all data collectors."""

    name: str = ""
    display_name: str = ""
    schedule: str = ""  # Cron expression
    category: str = ""  # positioning, sentiment, filings, research, academic

    def __init__(self):
        self.logger = get_logger(f"collector.{self.name}")

    @abstractmethod
    def collect(self, progress_cb=None) -> dict:
        """Execute data collection.

        Args:
            progress_cb: Optional callable(current: int, total: int, message: str)

        Returns:
            {"inserted": int, "updated": int, "errors": int, "message": str}
        """
        ...

    def get_state(self) -> Optional[CollectorState]:
        """Get the current collector state from DB."""
        with Session() as db:
            state = (
                db.query(CollectorState)
                .filter(CollectorState.collector_name == self.name)
                .first()
            )
            if state:
                db.expunge(state)
            return state

    def update_state(
        self,
        *,
        last_data_date: str = None,
        extra_state: dict = None,
        error: str = None,
    ):
        """Update collector state after a fetch attempt."""
        with Session() as db:
            state = (
                db.query(CollectorState)
                .filter(CollectorState.collector_name == self.name)
                .first()
            )
            if state is None:
                state = CollectorState(collector_name=self.name)
                db.add(state)

            state.last_fetch_at = datetime.utcnow()
            if error:
                state.last_error = error
                state.error_count = (state.error_count or 0) + 1
            else:
                state.last_success_at = datetime.utcnow()
                state.last_error = None
            if last_data_date:
                state.last_data_date = last_data_date
            if extra_state:
                current = dict(state.state or {})
                current.update(extra_state)
                state.state = current
            state.fetch_count = (state.fetch_count or 0) + 1

    def _upsert_timeseries(
        self,
        db,
        *,
        source: str,
        code: str,
        source_code: str,
        name: str,
        category: str,
        data: pd.Series,
        frequency: str = None,
        unit: str = None,
    ):
        """Upsert a timeseries entry following existing patterns."""
        from ix.db.models import Timeseries

        ts = db.query(Timeseries).filter(Timeseries.code == code).first()
        if ts is None:
            ts = Timeseries(
                code=code,
                name=name,
                source=source,
                source_code=source_code,
                category=category,
                frequency=frequency,
                unit=unit,
            )
            db.add(ts)
            db.flush()
        # Use the data setter which handles merge + cache invalidation
        ts.data = data

