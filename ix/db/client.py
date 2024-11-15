import pandas as pd
from ix import db
from typing import Union, List, Set, Tuple, Dict, Optional
import logging

# Configure logging
logger = logging.getLogger(__name__)

def get_pxs(
    codes: Union[str, List[str], Set[str], Tuple[str, ...], Dict[str, str], None] = None,
    start: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetches price data from the database for specified asset codes.

    Args:
        codes: Asset codes, which can be a string, list, set, tuple, or dictionary for renaming columns.
        start: Optional start date to filter the data from.

    Returns:
        A DataFrame containing price data with assets as columns and dates as the index.
    """
    # Handle renaming columns if `codes` is a dictionary
    if isinstance(codes, dict):
        keys = list(codes.keys())
        data = get_pxs(codes=keys, start=start)
        return data.rename(columns=codes)

    # Convert single string input to a list of codes, trimming whitespace
    if isinstance(codes, str):
        codes = [code.strip() for code in codes.split(",")]

    # Prepare to hold the data series
    px_data = []

    try:
        # Helper function to fetch data for a given code
        def fetch_px_series(code):
            pxlast = db.PxLast.find_one({"code": code}).run()
            if pxlast is not None:
                return pd.Series(data=pxlast.data, name=pxlast.code)
            return None

        # Fetch all prices if no specific codes are provided
        if codes is None:
            for pxlast in db.PxLast.find_all().run():
                if pxlast:
                    px_data.append(pd.Series(data=pxlast.data, name=pxlast.code))
        else:
            # Fetch prices for each specified code
            for code in codes:
                px_series = fetch_px_series(code)
                if px_series is not None:
                    px_data.append(px_series)

        # Combine series into a DataFrame
        if px_data:
            out = pd.concat(px_data, axis=1)
            out.index = pd.to_datetime(out.index)
            out = out.sort_index()

            # Filter data based on start date if provided
            if start:
                out = out.loc[start:]

            return out
        else:
            logger.warning("No price data found for the specified codes.")
            return pd.DataFrame()

    except Exception as e:
        logger.error(f"Error fetching price data: {e}", exc_info=True)
        return pd.DataFrame()
