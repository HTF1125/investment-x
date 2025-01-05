import pandas as pd
from ix import db
from typing import Union, List, Set, Tuple, Dict, Optional
import logging
from .models import Metadata

# Configure logging
logger = logging.getLogger(__name__)


def get_ts(*args: Dict[str, str], start: Optional[str] = None) -> pd.DataFrame:
    """
    Fetches price data from the database for specified asset codes.

    Args:
        codes: Asset codes, which can be a string, list, set, tuple, or dictionary for renaming columns.
        start: Optional start date to filter the data from.

    Returns:
        A DataFrame containing price data with assets as columns and dates as the index.
    """
    timeseries = []
    for arg in args:
        timeseries.append(get_timeseries(**arg, start=start))
    data = pd.concat(timeseries, axis=1)
    return data


def get_timeseries(
    code: str,
    field: str = "PX_LAST",
    name: Optional[str] = None,
    start: Optional[str] = None,
) -> pd.Series:
    metadata = Metadata.find_one({"code": code}).run()
    if metadata is None:
        raise ValueError(f"No metadata found for code: {code}")
    px_last = metadata.ts(field=field).data
    if start:
        px_last = px_last.loc[start:]
    px_last.name = name or code
    return px_last


def get_px_last(codes: List[str]) -> pd.DataFrame:
    return get_ts(*[{"code": code, "field": "PX_LAST", "name": code} for code in codes])
