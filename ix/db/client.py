from typing import Union, List, Set, Tuple, Dict, Optional
import pandas as pd
import re
import io
from datetime import datetime, date
import base64
from ix.misc import get_logger, periods
from .models import Universe, TacticalView, Timeseries
from .query import *

# Configure logging
logger = get_logger(__name__)


def get_timeseries(code: str) -> Timeseries:
    """
    Retrieves a time series for the specified asset code.
    Caching is enabled so that repeated calls with the same parameters
    do not re-query the database.
    """
    from ix.db.conn import Session

    with Session() as session:
        ts = session.query(Timeseries).filter(Timeseries.code == code).first()
        if ts is None:
            raise ValueError(f"Timeseries not found for code: {code}")
        return ts


def get_recent_tactical_view() -> Optional[TacticalView]:
    """Get the most recent tactical view."""
    from ix.db.conn import Session

    with Session() as session:
        return (
            session.query(TacticalView)
            .order_by(TacticalView.published_date.desc())
            .first()
        )


def get_insights(search: Optional[str] = None, limit: int = 10000) -> List[Dict]:
    """
    Placeholder for get_insights.
    The Insight model seems to be missing, so this returns an empty list to prevent import errors.
    """
    logger.warning("get_insights called but not implemented (Insight model missing). Returning empty list.")
    return []
