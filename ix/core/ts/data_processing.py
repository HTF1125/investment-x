"""Timeseries data loading and pandas conversion."""

from __future__ import annotations

from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session as SessionType

from ix.common import get_logger
from ix.db.models import Timeseries

logger = get_logger(__name__)


def process_database_timeseries(
    ts: Timeseries, db: SessionType
) -> Optional[pd.Series]:
    """Load a Timeseries record's data and return as a cleaned pandas Series."""
    try:
        # Use eagerly-loaded data_record when available (from joinedload),
        # only fall back to DB query if not loaded yet
        data_record = ts.data_record or ts._get_or_create_data_record(db)
        column_data = data_record.data if data_record and data_record.data else {}
        frequency = ts.frequency

        if column_data and isinstance(column_data, dict):
            ts_data = pd.Series(column_data)
            try:
                ts_data.index = pd.to_datetime(ts_data.index)
                ts_data = pd.to_numeric(ts_data, errors="coerce").dropna()
                ts_data.name = ts.code
                if frequency and len(ts_data) > 0:
                    ts_data = (
                        ts_data.sort_index()
                        .resample(str(frequency))
                        .last()
                        .dropna()
                    )
                else:
                    ts_data = ts_data.sort_index()

                if not ts_data.empty:
                    return ts_data
            except Exception:
                try:
                    valid_dates = pd.to_datetime(ts_data.index, errors="coerce")
                    ts_data = ts_data[valid_dates.notna()]
                    ts_data.index = pd.to_datetime(ts_data.index)
                    ts_data = pd.to_numeric(ts_data, errors="coerce").dropna()
                    ts_data.name = ts.code
                    ts_data = ts_data.sort_index()
                    if not ts_data.empty:
                        return ts_data
                except Exception:
                    logger.warning(
                        "Error processing timeseries %s: could not convert to Series",
                        ts.code,
                    )
                    return None
    except Exception as e:
        logger.warning("Error processing database timeseries %s: %s", ts.code, e)
        return None

    return None
