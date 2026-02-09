"""
Series router for advanced time series data retrieval.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import Response
from typing import List, Optional
from collections import OrderedDict
import json
import math
import pandas as pd
from datetime import datetime

from ix.db.conn import ensure_connection
from ix.db.query import Series
from ix.misc import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.get("/series")
async def get_series(
    series: List[str] = Query(..., description="Series expressions (can be repeated)"),
    start: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    format: str = Query("json", description="Response format ('json' or 'csv')"),
    sort: str = Query("asc", description="Sort order ('asc' or 'desc')"),
    limit: Optional[int] = Query(None, description="Maximum number of rows"),
    offset: Optional[int] = Query(None, description="Number of rows to skip"),
):
    """
    GET /api/series - Advanced series data API with comprehensive features.

    Query parameters:
    - series: Series expressions (can be repeated multiple times)
    - start: Start date (YYYY-MM-DD format, optional)
    - end: End date (YYYY-MM-DD format, optional)
    - format: Response format ('json', 'csv') (default: 'json')
    - sort: Sort order ('asc', 'desc') (default: 'asc')
    - limit: Maximum number of rows to return (optional)
    - offset: Number of rows to skip (optional)

    Examples:
    - /api/series?series=Series('AAPL')&series=Series('MSFT')
    - /api/series?series=SPY=Series('SPY US EQUITY:PX_LAST')&series=QQQ=Series('QQQ US EQUITY:PX_LAST')
    """
    ensure_connection()

    if not series:
        raise HTTPException(status_code=400, detail="No series expressions provided")

    if format not in ["json", "csv"]:
        raise HTTPException(
            status_code=400, detail="Invalid format. Must be 'json' or 'csv'"
        )

    # Process series expressions
    series_data_list = []

    for series_code in series:
        try:
            # Check for alias syntax: NAME=Series(...) or NAME=MultiSeries(...)
            if (
                "=" in series_code
                and not series_code.startswith("Series")
                and not series_code.startswith("MultiSeries")
            ):
                # Split into alias name and series expression
                alias_name, expression = series_code.split("=", maxsplit=1)
                series_data = eval(expression)

                # For Series: set the name attribute
                if isinstance(series_data, pd.Series):
                    series_data.name = alias_name.strip()
            else:
                # No alias, evaluate expression as-is
                series_data = eval(series_code)

            if series_data.empty:
                continue

            # Apply date filtering
            if start:
                start_dt = pd.to_datetime(start)
                series_data = series_data.loc[series_data.index >= start_dt]

            if end:
                end_dt = pd.to_datetime(end)
                series_data = series_data.loc[series_data.index <= end_dt]

            # Add to list for DataFrame creation
            series_data_list.append(series_data)

        except Exception as e:
            logger.warning(f"Error getting series {series_code}: {e}")
            continue

    # Combine all series into a single DataFrame
    if series_data_list:
        if len(series_data_list) == 1 and isinstance(series_data_list[0], pd.DataFrame):
            df = series_data_list[0]
        else:
            df = pd.concat(series_data_list, axis=1)
        df.index.name = "Date"

        # Apply sorting
        if sort == "desc":
            df = df.sort_index(ascending=False)
        else:
            df = df.sort_index(ascending=True)

        # Apply limit and offset
        if offset:
            df = df.iloc[offset:]
        if limit:
            df = df.iloc[:limit]

        if format == "csv":
            csv_data = df.to_csv()
            return Response(
                content=csv_data,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=series_data.csv"},
            )
        else:
            # Return as column-oriented dict
            df_indexed = df.reset_index()
            column_dict = OrderedDict()

            for col in df_indexed.columns:
                values = df_indexed[col].tolist()
                cleaned_values = []
                for v in values:
                    if v is None or (isinstance(v, float) and math.isnan(v)):
                        cleaned_values.append(None)
                    elif isinstance(v, (pd.Timestamp, datetime)):
                        cleaned_values.append(v.isoformat())
                    else:
                        cleaned_values.append(v)
                column_dict[col] = cleaned_values

            return Response(
                content=json.dumps(column_dict, ensure_ascii=False),
                media_type="application/json",
            )
    else:
        # No data available
        if format == "csv":
            return Response(
                content="date,value\n",
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=series_data.csv"},
            )
        else:
            return Response(
                content=json.dumps({"Date": []}, ensure_ascii=False),
                media_type="application/json",
            )
