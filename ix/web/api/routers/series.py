"""
Series API router for time series data retrieval.
"""

from collections import OrderedDict
import json
import time
from flask import jsonify, request, Response
import pandas as pd
from ix.db.conn import ensure_connection
from ix.db.query import Series, D_MultiSeries
from ix.misc import get_logger
from datetime import datetime
from ix.db.custom import FinancialConditionsIndexUS
from ix.db import MonthEndOffset, Cycle
from ix.db.query import M2
from ix.db.query import InvestorPositions, Offset
from ix.db.query import (
    Series,
    StandardScalar,
    Offset,
    Cycle,
    D_MultiSeries,
    MonthEndOffset,
    M2,
    InvestorPositions,
    NumOfOECDLeadingPositiveMoM,
    NumOfPmiMfgPositiveMoM,
    NumOfPmiServicesPositiveMoM,
)

logger = get_logger(__name__)


def register_series_routes(app):
    """
    Register series API routes with the Flask app.

    Args:
        app: The Flask app instance
    """

    @app.server.route("/api/series", methods=["GET"])
    def get_series():
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
        - fields: Comma-separated list of fields to include (optional)
        - freq: Frequency for resampling (optional)
        - method: Resampling method ('last', 'first', 'mean', 'sum', 'min', 'max') (default: 'last')

        Examples:
        # Basic series retrieval
        - /api/series?series=Series('AAPL')&series=Series('MSFT')

        # With custom column names (alias syntax)
        - /api/series?series=SPY=Series('SPY US EQUITY:PX_LAST')&series=QQQ=Series('QQQ US EQUITY:PX_LAST')

        # With date filtering
        - /api/series?series=Series('AAPL')&series=Series('MSFT')&start=2023-01-01&end=2023-12-31

        # With resampling
        - /api/series?series=Series('AAPL').resample('ME').last()&series=Series('MSFT').resample('ME').last()

        # Multiple series with different operations
        - /api/series?series=Series('AAPL').pct_change()&series=Series('MSFT').rolling(20).mean()

        # Using MultiSeries for bulk operations
        - /api/series?series=MultiSeries(['AAPL', 'MSFT', 'GOOGL'], 'PX_LAST')

        # With frequency and method
        - /api/series?series=Series('SPX INDEX')&freq=ME&method=last

        # CSV output
        - /api/series?series=Series('AAPL')&format=csv

        # With sorting and limiting
        - /api/series?series=Series('AAPL')&sort=desc&limit=100

        # Complex expressions
        - /api/series?series=Series('AAPL').rolling(20).mean()&series=Series('AAPL').rolling(50).mean()

        Response format: Column-oriented JSON object for efficient time series data

        Without aliases:
        {
          "Date": ["2023-01-01T00:00:00", "2023-01-02T00:00:00"],
          "Series('AAPL')": [150.0, 151.0],
          "Series('MSFT')": [250.0, 251.0]
        }

        With aliases (SPY=Series(...)):
        {
          "Date": ["2023-01-01T00:00:00", "2023-01-02T00:00:00"],
          "SPY": [450.0, 451.0],
          "QQQ": [380.0, 381.0]
        }

        Notes:
        - Returns column-oriented format for efficient JSON serialization
        - Preserves column order from the original DataFrame
        - Date column contains ISO 8601 datetime strings
        - NaN values are represented as null
        - Empty arrays represent no data available
        """
        start_time = time.time()

        try:
            # Ensure MongoDB connection
            ensure_connection()

            # Get query parameters
            series_list = request.args.getlist("series")
            start_date = request.args.get("start")
            end_date = request.args.get("end")
            response_format = request.args.get("format", "json").lower()

            # Validate parameters
            if not series_list:
                return jsonify({"error": "No series expressions provided"}), 400

            if response_format not in ["json", "csv"]:
                return (
                    jsonify({"error": "Invalid format. Must be 'json' or 'csv'"}),
                    400,
                )

            # Process series expressions
            series_data_list = []

            for series_code in series_list:
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
                        # For DataFrame from MultiSeries: can't easily rename all columns
                        # Just let it keep its original column names
                    else:
                        # No alias, evaluate expression as-is
                        series_data = eval(series_code)

                    if series_data.empty:
                        continue

                    # Apply date filtering
                    if start_date:
                        start_dt = pd.to_datetime(start_date)
                        series_data = series_data.loc[series_data.index >= start_dt]

                    if end_date:
                        end_dt = pd.to_datetime(end_date)
                        series_data = series_data.loc[series_data.index <= end_dt]

                    # Add to list for DataFrame creation
                    series_data_list.append(series_data)

                except Exception as e:
                    logger.warning(f"Error getting series {series_code}: {e}")
                    continue

            # Combine all series into a single DataFrame
            if series_data_list:
                # Combine all series into a single DataFrame
                if len(series_data_list) == 1 and isinstance(
                    series_data_list[0], pd.DataFrame
                ):
                    # Single DataFrame (e.g., from MultiSeries)
                    df = series_data_list[0]
                else:
                    # Multiple Series
                    df = pd.concat(series_data_list, axis=1)
                df.index.name = "Date"
                if response_format == "csv":
                    # Convert to CSV format
                    csv_data = df.to_csv()

                    return Response(
                        csv_data,
                        mimetype="text/csv",
                        headers={
                            "Content-Disposition": "attachment; filename=series_data.csv"
                        },
                    )
                else:
                    # Return as column-oriented dict with NaN converted to None
                    df_indexed = df.reset_index()

                    # Convert to column-oriented format: {"Date": [...], "SPY": [...], ...}
                    # Use OrderedDict to preserve column order from DataFrame
                    column_dict = OrderedDict()
                    import math

                    # Iterate in DataFrame column order to preserve order
                    for col in df_indexed.columns:
                        values = df_indexed[col].tolist()
                        # Clean values for JSON serialization
                        cleaned_values = []
                        for v in values:
                            if v is None or (isinstance(v, float) and math.isnan(v)):
                                cleaned_values.append(None)
                            elif isinstance(v, (pd.Timestamp, datetime)):
                                # Convert timestamp/datetime to ISO string
                                cleaned_values.append(v.isoformat())
                            else:
                                cleaned_values.append(v)
                        column_dict[col] = cleaned_values

                    # Use json.dumps with sort_keys=False to preserve OrderedDict order
                    # Flask jsonify may not preserve order in some versions
                    return Response(
                        json.dumps(column_dict, ensure_ascii=False),
                        mimetype="application/json",
                    )
            else:
                # No data available
                if response_format == "csv":
                    return Response(
                        "date,value\n",
                        mimetype="text/csv",
                        headers={
                            "Content-Disposition": "attachment; filename=series_data.csv"
                        },
                    )
                else:
                    # Return empty column-oriented format (maintain order)
                    return Response(
                        json.dumps({"Date": []}, ensure_ascii=False),
                        mimetype="application/json",
                    )

        except Exception as e:
            logger.exception(f"Error in series endpoint: {e}")
            return jsonify({"error": f"Internal server error: {str(e)}"}), 500
