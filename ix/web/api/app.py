"""
API endpoints for the ix.web application.
These are Flask routes that extend the Dash app server.
"""

from flask import jsonify, request, Response
from collections import OrderedDict
import json
import math
import pandas as pd
from ix.db.models import Timeseries
from ix.db.conn import ensure_connection, Session
from ix.misc import get_logger
from datetime import datetime
from ix.db.custom import FinancialConditionsIndexUS
from sqlalchemy.orm import joinedload

# Import routers
from ix.web.api.routers import series


logger = get_logger(__name__)


def register_api_routes(app):
    """
    Register API routes with the Dash app server.
    Call this function after creating your Dash app.

    Args:
        app: The Dash app instance
    """

    @app.server.route("/api/health", methods=["GET"])
    def health_check():
        """Health check endpoint"""
        return jsonify({"status": "healthy", "service": "ix.web API"})

    @app.server.route("/api/timeseries", methods=["GET"])
    def get_timeseries():
        """
        GET /api/timeseries - List all timeseries with optional filtering and pagination.

        Query parameters:
        - limit: Limit number of results
        - offset: Offset for pagination (default: 0)
        - category: Filter by category
        - asset_class: Filter by asset class
        - provider: Filter by provider
        """
        # Ensure MongoDB connection
        ensure_connection()

        # Get query parameters
        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", 0, type=int)
        category = request.args.get("category")
        asset_class = request.args.get("asset_class")
        provider = request.args.get("provider")

        # Build MongoDB query
        query = {}
        if category:
            query["category"] = category
        if asset_class:
            query["asset_class"] = asset_class
        if provider:
            query["provider"] = provider

        # Execute query with pagination using SQLAlchemy
        with Session() as session:
            timeseries_query = session.query(Timeseries)

            # Apply filters
            if query:
                if "category" in query:
                    timeseries_query = timeseries_query.filter(
                        Timeseries.category == query["category"]
                    )
                if "asset_class" in query:
                    timeseries_query = timeseries_query.filter(
                        Timeseries.asset_class == query["asset_class"]
                    )
                if "provider" in query:
                    timeseries_query = timeseries_query.filter(
                        Timeseries.provider == query["provider"]
                    )

            # Apply pagination
            if offset:
                timeseries_query = timeseries_query.offset(offset)
            if limit:
                timeseries_query = timeseries_query.limit(limit)

            timeseries_list = timeseries_query.all()

            # At this point, all columns are loaded for each Timeseries row

        formatted_timeseries = []

        for ts in timeseries_list:
            # Handle both dict and object format
            if isinstance(ts, dict):
                ts_id = ts.get("id")
                ts_code = ts.get("code")
                ts_name = ts.get("name")
                ts_provider = ts.get("provider")
                ts_asset_class = ts.get("asset_class")
                ts_category = ts.get("category")
                ts_source = ts.get("source")
                ts_frequency = ts.get("frequency")
                ts_start = ts.get("start")
                ts_end = ts.get("end")
                ts_favorite = ts.get("favorite", False)
            else:
                ts_id = ts.id
                ts_code = ts.code
                ts_name = ts.name
                ts_provider = ts.provider
                ts_asset_class = ts.asset_class
                ts_category = ts.category
                ts_source = ts.source
                ts_frequency = ts.frequency
                ts_start = ts.start
                ts_end = ts.end
                ts_favorite = ts.favorite if hasattr(ts, "favorite") else False

            formatted_ts = {
                "id": str(ts_id),
                "code": ts_code,
                "name": ts_name,
                "provider": ts_provider,
                "asset_class": ts_asset_class,
                "category": ts_category,
                "start": (
                    ts_start.isoformat()
                    if ts_start and hasattr(ts_start, "isoformat")
                    else (str(ts_start) if ts_start else None)
                ),
                "end": (
                    ts_end.isoformat()
                    if ts_end and hasattr(ts_end, "isoformat")
                    else (str(ts_end) if ts_end else None)
                ),
                "source": ts_source,
                "source_code": (
                    ts.get("source_code")
                    if isinstance(ts, dict)
                    else getattr(ts, "source_code", None)
                ),
                "frequency": ts_frequency,
                "unit": (
                    ts.get("unit")
                    if isinstance(ts, dict)
                    else getattr(ts, "unit", None)
                ),
                "scale": (
                    ts.get("scale")
                    if isinstance(ts, dict)
                    else getattr(ts, "scale", None)
                ),
                "currency": (
                    ts.get("currency")
                    if isinstance(ts, dict)
                    else getattr(ts, "currency", None)
                ),
                "country": (
                    ts.get("country")
                    if isinstance(ts, dict)
                    else getattr(ts, "country", None)
                ),
                "num_data": (
                    ts.get("num_data")
                    if isinstance(ts, dict)
                    else getattr(ts, "num_data", None)
                ),
                "remark": (
                    ts.get("remark")
                    if isinstance(ts, dict)
                    else getattr(ts, "remark", None)
                ),
                "favorite": ts_favorite,
            }
            formatted_timeseries.append(formatted_ts)

        logger.info(f"Retrieved {len(formatted_timeseries)} timeseries records")
        return jsonify(formatted_timeseries)

    @app.server.route("/api/timeseries", methods=["POST"])
    def create_or_update_timeseries_bulk():
        """
        POST /api/timeseries - Create new or update existing timeseries metadata.

        Request body should be a JSON list with timeseries objects:
        [
            {
                "code": "AAPL",
                "name": "Apple Inc.",
                "provider": "Yahoo",
                "asset_class": "Equity",
                "category": "Technology",
                ...
            },
            ...
        ]

        Required fields:
        - code: Timeseries code (used to identify/create the record)

        Optional fields (will be set/updated if provided):
        - name, provider, asset_class, category, source, source_code
        - frequency, unit, scale, currency, country, remark
        - start, end, num_data (for metadata)
        - favorite (boolean, default: false)

        Note: If timeseries doesn't exist, it will be created. If it exists, it will be updated.
        """
        # Ensure MongoDB connection
        ensure_connection()

        # Get the JSON payload
        payload = request.get_json()

        if not isinstance(payload, list):
            return (
                jsonify(
                    {"error": "Invalid payload: expected a list of timeseries objects."}
                ),
                400,
            )

        if not payload:
            return jsonify({"error": "Empty payload provided."}), 400

        updated_codes = []
        created_codes = []
        not_found_codes = []
        errors = []

        for ts_data in payload:
            # Validate required field
            code = ts_data.get("code")
            if not code:
                errors.append("Missing 'code' field in one or more timeseries objects")
                continue

            try:
                # Find existing timeseries by code using SQLAlchemy
                with Session() as session:
                    ts = (
                        session.query(Timeseries)
                        .filter(Timeseries.code == code)
                        .first()
                    )

                    if ts is None:
                        # Create new timeseries
                        ts = Timeseries(code=code)
                        session.add(ts)
                        session.flush()  # Flush to get the ID
                        created_codes.append(code)
                    else:
                        updated_codes.append(code)

                    # Update fields with type validation
                    # String fields
                    string_fields = [
                        ("name", 200),
                        ("provider", 100),
                        ("asset_class", 50),
                        ("category", 100),
                        ("source", 100),
                        ("source_code", 2000),
                        ("frequency", 20),
                        ("unit", 50),
                        ("currency", 10),
                        ("country", 100),
                    ]

                    for field, max_length in string_fields:
                        if field in ts_data:
                            value = ts_data[field]
                            if value is not None:
                                value = str(value)[:max_length]
                                setattr(ts, field, value)

                    # Text field (no length limit)
                    if "remark" in ts_data:
                        value = ts_data["remark"]
                        if value is not None:
                            value = str(value)
                        setattr(ts, "remark", value)

                    # Integer field with overflow protection
                    if "scale" in ts_data:
                        value = ts_data["scale"]
                        if value is not None:
                            try:
                                # Ensure scale is within reasonable range
                                scale_value = int(value)
                                if (
                                    scale_value > 2147483647
                                    or scale_value < -2147483648
                                ):
                                    logger.warning(
                                        f"Scale value {scale_value} out of range for {code}, setting to 1"
                                    )
                                    scale_value = 1
                                setattr(ts, "scale", scale_value)
                            except (ValueError, TypeError):
                                logger.warning(
                                    f"Invalid scale value '{value}' for {code}, setting to 1"
                                )
                                setattr(ts, "scale", 1)

                    # Integer field with overflow protection for num_data
                    if "num_data" in ts_data:
                        value = ts_data["num_data"]
                        if value is not None:
                            try:
                                # Large integer can handle much larger values
                                num_data_value = int(value)
                                if (
                                    num_data_value > 9223372036854775807
                                    or num_data_value < -9223372036854775808
                                ):
                                    logger.warning(
                                        f"num_data value {num_data_value} out of range for {code}, setting to None"
                                    )
                                    num_data_value = None
                                setattr(ts, "num_data", num_data_value)
                            except (ValueError, TypeError):
                                logger.warning(
                                    f"Invalid num_data value '{value}' for {code}, setting to None"
                                )
                                setattr(ts, "num_data", None)

                    # Date fields
                    if "start" in ts_data and ts_data["start"]:
                        try:
                            from datetime import datetime

                            start_date = datetime.fromisoformat(
                                ts_data["start"].replace("Z", "+00:00")
                            ).date()
                            setattr(ts, "start", start_date)
                        except (ValueError, TypeError):
                            logger.warning(
                                f"Invalid start date '{ts_data['start']}' for {code}"
                            )

                    if "end" in ts_data and ts_data["end"]:
                        try:
                            from datetime import datetime

                            end_date = datetime.fromisoformat(
                                ts_data["end"].replace("Z", "+00:00")
                            ).date()
                            setattr(ts, "end", end_date)
                        except (ValueError, TypeError):
                            logger.warning(
                                f"Invalid end date '{ts_data['end']}' for {code}"
                            )

                    # Boolean field (favorite)
                    if "favorite" in ts_data:
                        value = ts_data["favorite"]
                        if value is not None:
                            try:
                                # Convert to boolean (handles string "true"/"false", 1/0, etc.)
                                if isinstance(value, bool):
                                    favorite_value = value
                                elif isinstance(value, str):
                                    favorite_value = value.lower() in (
                                        "true",
                                        "1",
                                        "yes",
                                        "on",
                                    )
                                else:
                                    favorite_value = bool(value)
                                setattr(ts, "favorite", favorite_value)
                            except (ValueError, TypeError):
                                logger.warning(
                                    f"Invalid favorite value '{value}' for {code}, setting to False"
                                )
                                setattr(ts, "favorite", False)

                    # Commit changes
                    session.commit()

            except Exception as e:
                logger.error(f"Error updating timeseries {code}: {e}")
                errors.append(f"Error updating {code}: {str(e)}")
                continue

        logger.info(
            f"Successfully processed {len(created_codes)} new and {len(updated_codes)} updated timeseries records"
        )

        response = {
            "message": f"Successfully processed {len(payload)} timeseries objects.",
            "created_codes": created_codes,
            "created_count": len(created_codes),
            "updated_codes": updated_codes,
            "updated_count": len(updated_codes),
        }

        if not_found_codes:
            response["not_found_codes"] = not_found_codes
            response["not_found_count"] = len(not_found_codes)
            logger.warning(f"Timeseries not found: {not_found_codes}")

        if errors:
            response["errors"] = errors
            response["error_count"] = len(errors)

        # Return 207 Multi-Status if there were partial failures
        status_code = 200 if not (not_found_codes or errors) else 207

        return jsonify(response), status_code

    @app.server.route("/api/timeseries/<timeseries_id>", methods=["GET"])
    def get_timeseries_by_id(timeseries_id):
        """
        GET /api/timeseries/{id} - Get detailed timeseries information by ID (code) with full data.
        """
        # Ensure MongoDB connection
        ensure_connection()

        # Get timeseries by code using SQLAlchemy
        with Session() as session:
            ts = (
                session.query(Timeseries)
                .filter(Timeseries.code == timeseries_id)
                .first()
            )

            if not ts:
                return jsonify({"error": "Timeseries not found"}), 404

            # Extract all attributes while in session
            ts_id = ts.id
            ts_code = ts.code
            ts_name = ts.name
            ts_provider = ts.provider
            ts_asset_class = ts.asset_class
            ts_category = ts.category
            ts_source = ts.source
            ts_source_code = ts.source_code
            ts_frequency = ts.frequency
            ts_unit = ts.unit
            ts_scale = ts.scale
            ts_currency = ts.currency
            ts_country = ts.country
            ts_start = ts.start
            ts_end = ts.end
            ts_num_data = ts.num_data
            ts_remark = ts.remark
            ts_favorite = ts.favorite if hasattr(ts, "favorite") else False
            # Get data within session
            ts_data = ts.data.copy() if hasattr(ts, "data") else pd.Series()

        # Format the timeseries object
        formatted_ts = {
            "id": str(ts_id),
            "code": ts_code,
            "name": ts_name,
            "provider": ts_provider,
            "asset_class": ts_asset_class,
            "category": ts_category,
            "start_date": (
                ts_start.isoformat()
                if ts_start and hasattr(ts_start, "isoformat")
                else (str(ts_start) if ts_start else None)
            ),
            "end_date": (
                ts_end.isoformat()
                if ts_end and hasattr(ts_end, "isoformat")
                else (str(ts_end) if ts_end else None)
            ),
            "num_data_points": ts_num_data,
            "source": ts_source,
            "source_code": ts_source_code,
            "frequency": ts_frequency,
            "unit": ts_unit,
            "scale": ts_scale,
            "currency": ts_currency,
            "country": ts_country,
            "remark": ts_remark,
            "favorite": ts_favorite,
        }

        # Add full data
        try:
            data = ts_data
            if not data.empty:
                # Convert data to list of {date, value} objects
                data_points = []
                for date_idx, value in data.items():
                    data_points.append(
                        {
                            "date": str(date_idx),
                            "value": float(value) if value is not None else None,
                        }
                    )

                formatted_ts["data"] = data_points
                formatted_ts["data_stats"] = {
                    "count": len(data),
                    "min": float(data.min()) if not data.empty else None,
                    "max": float(data.max()) if not data.empty else None,
                    "mean": float(data.mean()) if not data.empty else None,
                    "std": float(data.std()) if not data.empty else None,
                    "last_value": float(data.iloc[-1]) if not data.empty else None,
                    "last_date": str(data.index[-1]) if not data.empty else None,
                }
            else:
                formatted_ts["data"] = []
                formatted_ts["data_stats"] = {
                    "count": 0,
                    "min": None,
                    "max": None,
                    "mean": None,
                    "std": None,
                    "last_value": None,
                    "last_date": None,
                }
        except Exception as e:
            logger.warning(f"Could not get data for timeseries {ts.code}: {e}")
            formatted_ts["data"] = []
            formatted_ts["data_stats"] = {
                "count": 0,
                "min": None,
                "max": None,
                "mean": None,
                "std": None,
                "last_value": None,
                "last_date": None,
            }

        return jsonify(formatted_ts)

    @app.server.route("/api/timeseries/code/<code>", methods=["GET"])
    def get_timeseries_by_code(code):
        """
        GET /api/timeseries/code/{code} - Get timeseries by its code.
        """
        # Ensure MongoDB connection
        ensure_connection()

        # Get timeseries by code using SQLAlchemy
        with Session() as session:
            ts = session.query(Timeseries).filter(Timeseries.code == code).first()

            if not ts:
                return (
                    jsonify({"error": f"Timeseries with code '{code}' not found"}),
                    404,
                )

            # Extract all attributes while in session
            ts_id = ts.id
            ts_code = ts.code
            ts_name = ts.name
            ts_favorite = ts.favorite if hasattr(ts, "favorite") else False
            ts_data = ts.data.copy() if hasattr(ts, "data") else pd.Series()

        # Format the timeseries object
        formatted_ts = {
            "id": str(ts_id),
            "code": ts_code,
            "name": ts_name,
            "provider": ts.provider,
            "asset_class": ts.asset_class,
            "category": ts.category,
            "start_date": ts.start.isoformat() if ts.start else None,
            "end_date": ts.end.isoformat() if ts.end else None,
            "num_data_points": ts.num_data,
            "source": ts.source,
            "source_code": ts.source_code,
            "frequency": ts.frequency,
            "unit": ts.unit,
            "scale": ts.scale,
            "currency": ts.currency,
            "country": ts.country,
            "remark": ts.remark,
            "favorite": ts_favorite,
        }

        # Add basic data statistics (without full data for code lookup)
        try:
            data = ts.data
            if not data.empty:
                formatted_ts["data_stats"] = {
                    "count": len(data),
                    "last_value": float(data.iloc[-1]) if not data.empty else None,
                    "last_date": str(data.index[-1]) if not data.empty else None,
                    "min": float(data.min()) if not data.empty else None,
                    "max": float(data.max()) if not data.empty else None,
                }
            else:
                formatted_ts["data_stats"] = {
                    "count": 0,
                    "last_value": None,
                    "last_date": None,
                    "min": None,
                    "max": None,
                }
        except Exception as e:
            logger.warning(f"Could not get data stats for timeseries {ts.code}: {e}")
            formatted_ts["data_stats"] = {
                "count": 0,
                "last_value": None,
                "last_date": None,
                "min": None,
                "max": None,
            }

        return jsonify(formatted_ts)

    @app.server.route("/api/timeseries/favorites", methods=["GET"])
    def get_favorite_timeseries_data():
        """
        GET /api/timeseries/favorites - Get all favorite timeseries data as a concatenated DataFrame.

        Returns all timeseries marked as favorite (favorite = true) with their data
        concatenated into a single DataFrame format, similar to /api/series.

        Query parameters (optional):
        - start_date: ISO-8601 date or datetime (inclusive lower bound)
        - end_date: ISO-8601 date or datetime (inclusive upper bound)

        Response format: Column-oriented JSON object
        {
          "Date": ["2023-01-01T00:00:00", "2023-01-02T00:00:00"],
          "AAPL US EQUITY:PX_LAST": [150.0, 151.0],
          "MSFT US EQUITY:PX_LAST": [250.0, 251.0]
        }

        Notes:
        - Returns column-oriented format for efficient JSON serialization
        - Date column contains ISO 8601 datetime strings
        - NaN values are represented as null
        - Series are aligned by date (outer join)
        """
        ensure_connection()

        try:
            with Session() as session:
                # Query all favorite timeseries with data_record eagerly loaded
                favorite_timeseries = (
                    session.query(Timeseries)
                    .options(joinedload(Timeseries.data_record))
                    .filter(Timeseries.favorite == True)
                    .all()
                )

                if not favorite_timeseries:
                    return Response(
                        json.dumps({"Date": []}, ensure_ascii=False),
                        mimetype="application/json",
                    )

                # Collect all series data as pandas Series for concatenation
                series_list = []

                for ts in favorite_timeseries:
                    try:
                        ts_code = ts.code

                        # Access data directly via data_record relationship to avoid detached instance error
                        data_record = ts._get_or_create_data_record(session)
                        column_data = (
                            data_record.data if data_record and data_record.data else {}
                        )
                        frequency = ts.frequency

                        # Convert JSONB dict to pandas Series
                        if column_data and isinstance(column_data, dict):
                            ts_data = pd.Series(column_data)
                            try:
                                ts_data.index = pd.to_datetime(ts_data.index)
                                # Convert to numeric and drop NaN
                                ts_data = pd.to_numeric(
                                    ts_data, errors="coerce"
                                ).dropna()
                                ts_data.name = ts_code
                                if frequency and len(ts_data) > 0:
                                    ts_data = (
                                        ts_data.sort_index()
                                        .resample(str(frequency))
                                        .last()
                                        .dropna()
                                    )
                                else:
                                    ts_data = ts_data.sort_index()

                                # Only add non-empty series
                                if not ts_data.empty:
                                    series_list.append(ts_data)
                            except Exception:
                                # If date conversion fails, try to clean it
                                try:
                                    valid_dates = pd.to_datetime(
                                        ts_data.index, errors="coerce"
                                    )
                                    ts_data = ts_data[valid_dates.notna()]
                                    ts_data.index = pd.to_datetime(ts_data.index)
                                    ts_data = pd.to_numeric(
                                        ts_data, errors="coerce"
                                    ).dropna()
                                    ts_data.name = ts_code
                                    ts_data = ts_data.sort_index()
                                    if not ts_data.empty:
                                        series_list.append(ts_data)
                                except Exception:
                                    logger.warning(
                                        f"Error processing timeseries {ts_code}: could not convert to Series"
                                    )
                                    continue
                        else:
                            logger.debug(f"Timeseries {ts_code} has no data")

                    except Exception as e:
                        error_code = ts_code if "ts_code" in locals() else "unknown"
                        logger.warning(
                            f"Error processing favorite timeseries {error_code}: {e}"
                        )
                        continue

                # Concatenate all series into a DataFrame (like /api/series)
                if series_list:
                    # Combine all series into a single DataFrame
                    df = pd.concat(series_list, axis=1)
                    df.index.name = "Date"

                    # Optional date slicing via query params
                    start_date_str = request.args.get("start_date")
                    end_date_str = request.args.get("end_date")

                    start_ts = (
                        pd.to_datetime(start_date_str, errors="coerce")
                        if start_date_str
                        else None
                    )
                    end_ts = (
                        pd.to_datetime(end_date_str, errors="coerce")
                        if end_date_str
                        else None
                    )

                    # Normalize timezone info on both index and bounds for safe comparison
                    try:
                        df.index = pd.DatetimeIndex(df.index).tz_localize(None)
                    except Exception:
                        try:
                            df.index = pd.DatetimeIndex(df.index).tz_convert(None)
                        except Exception:
                            pass

                    if isinstance(start_ts, pd.Timestamp):
                        try:
                            start_ts = start_ts.tz_localize(None)
                        except Exception:
                            try:
                                start_ts = start_ts.tz_convert(None)
                            except Exception:
                                pass

                    if isinstance(end_ts, pd.Timestamp):
                        try:
                            end_ts = end_ts.tz_localize(None)
                        except Exception:
                            try:
                                end_ts = end_ts.tz_convert(None)
                            except Exception:
                                pass

                    # If both provided and reversed, swap to ensure valid range
                    if (
                        isinstance(start_ts, pd.Timestamp)
                        and isinstance(end_ts, pd.Timestamp)
                        and start_ts > end_ts
                    ):
                        start_ts, end_ts = end_ts, start_ts

                    # Apply slicing if bounds are valid Timestamps
                    if isinstance(start_ts, pd.Timestamp):
                        df = df[df.index >= start_ts]
                    if isinstance(end_ts, pd.Timestamp):
                        df = df[df.index <= end_ts]

                    # Convert to column-oriented format like /api/series
                    df_indexed = df.reset_index()

                    # Convert to column-oriented format: {"Date": [...], "SERIES1": [...], ...}
                    column_dict = OrderedDict()

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

                    # Return as JSON with preserved column order
                    return Response(
                        json.dumps(column_dict, ensure_ascii=False),
                        mimetype="application/json",
                    )
                else:
                    # No data available
                    return Response(
                        json.dumps({"Date": []}, ensure_ascii=False),
                        mimetype="application/json",
                    )

        except Exception as e:
            logger.exception(f"Error retrieving favorite timeseries: {e}")
            return jsonify({"error": f"Internal server error: {str(e)}"}), 500

    @app.server.route("/api/timeseries.custom", methods=["GET"])
    def get_custom_timeseries_data():
        """
        GET /api/timeseries.custom - Get selected timeseries data based on provided codes.

        Accepts JSON body (not query string):
        { "codes": ["CODE1", "CODE2", ...] }
        or
        { "codes": "CODE1, CODE2, ..." }

        Optional query parameters:
        - start_date: ISO-8601 date or datetime (inclusive lower bound)
        - end_date: ISO-8601 date or datetime (inclusive upper bound)

        Returns the same column-oriented format as /api/timeseries/favorites.
        - Column order follows the input codes order
        - Dates are sorted descending
        """
        ensure_connection()

        try:
            # Parse codes from JSON body (not from URL)
            payload = request.get_json(silent=True)
            codes = []
            if isinstance(payload, list):
                codes = [str(c).strip() for c in payload if str(c).strip()]
            elif isinstance(payload, dict) and payload is not None:
                raw_codes = payload.get("codes")
                if isinstance(raw_codes, list):
                    codes = [str(c).strip() for c in raw_codes if str(c).strip()]
                elif isinstance(raw_codes, str):
                    codes = [c.strip() for c in raw_codes.split(",") if c.strip()]

            # Fallback to header if provided
            if not codes:
                header_codes = request.headers.get("X-Codes")
                if header_codes:
                    codes = [c.strip() for c in header_codes.split(",") if c.strip()]

            # Ensure we have codes
            if not codes:
                return (
                    jsonify(
                        {
                            "error": "No codes provided. Provide JSON body with 'codes' list or 'X-Codes' header."
                        }
                    ),
                    400,
                )

            # Deduplicate while preserving order to avoid duplicate JSON keys
            seen_codes = set()
            unique_codes = []
            for code in codes:
                if code not in seen_codes:
                    unique_codes.append(code)
                    seen_codes.add(code)
            codes = unique_codes

            # Optional date slicing via query params
            start_date_str = request.args.get("start_date")
            end_date_str = request.args.get("end_date")

            with Session() as session:
                # Fetch all requested timeseries in one query
                ts_list = (
                    session.query(Timeseries)
                    .options(joinedload(Timeseries.data_record))
                    .filter(Timeseries.code.in_(codes))
                    .all()
                )
                code_to_ts = {ts.code: ts for ts in ts_list}

                series_list = []

                for code in codes:
                    ts = code_to_ts.get(code)
                    if not ts:
                        continue
                    try:
                        # Access data directly via data_record
                        data_record = ts._get_or_create_data_record(session)
                        column_data = (
                            data_record.data if data_record and data_record.data else {}
                        )
                        frequency = ts.frequency

                        # Convert JSONB dict to pandas Series
                        if column_data and isinstance(column_data, dict):
                            ts_data = pd.Series(column_data)
                            try:
                                ts_data.index = pd.to_datetime(ts_data.index)
                                ts_data = pd.to_numeric(
                                    ts_data, errors="coerce"
                                ).dropna()
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

                                # Only add non-empty series
                                if not ts_data.empty:
                                    series_list.append(ts_data)
                            except Exception:
                                # If date conversion fails, try to clean it
                                try:
                                    valid_dates = pd.to_datetime(
                                        ts_data.index, errors="coerce"
                                    )
                                    ts_data = ts_data[valid_dates.notna()]
                                    ts_data.index = pd.to_datetime(ts_data.index)
                                    ts_data = pd.to_numeric(
                                        ts_data, errors="coerce"
                                    ).dropna()
                                    ts_data.name = ts.code
                                    ts_data = ts_data.sort_index()
                                    if not ts_data.empty:
                                        series_list.append(ts_data)
                                except Exception:
                                    logger.warning(
                                        f"Error processing timeseries {ts.code}: could not convert to Series"
                                    )
                                    continue
                        else:
                            logger.debug(f"Timeseries {ts.code} has no data")

                    except Exception as e:
                        error_code = code
                        logger.warning(
                            f"Error processing custom timeseries {error_code}: {e}"
                        )
                        continue

                # Concatenate all series into a DataFrame
                if series_list:
                    df = pd.concat(series_list, axis=1)
                    df.index.name = "Date"

                    # Optional date bounds
                    start_ts = (
                        pd.to_datetime(start_date_str, errors="coerce")
                        if start_date_str
                        else None
                    )
                    end_ts = (
                        pd.to_datetime(end_date_str, errors="coerce")
                        if end_date_str
                        else None
                    )

                    # Normalize timezone info on both index and bounds for safe comparison
                    try:
                        df.index = pd.DatetimeIndex(df.index).tz_localize(None)
                    except Exception:
                        try:
                            df.index = pd.DatetimeIndex(df.index).tz_convert(None)
                        except Exception:
                            pass

                    if isinstance(start_ts, pd.Timestamp):
                        try:
                            start_ts = start_ts.tz_localize(None)
                        except Exception:
                            try:
                                start_ts = start_ts.tz_convert(None)
                            except Exception:
                                pass

                    if isinstance(end_ts, pd.Timestamp):
                        try:
                            end_ts = end_ts.tz_localize(None)
                        except Exception:
                            try:
                                end_ts = end_ts.tz_convert(None)
                            except Exception:
                                pass

                    # If both provided and reversed, swap to ensure valid range
                    if (
                        isinstance(start_ts, pd.Timestamp)
                        and isinstance(end_ts, pd.Timestamp)
                        and start_ts > end_ts
                    ):
                        start_ts, end_ts = end_ts, start_ts

                    # Apply slicing if bounds are valid Timestamps
                    if isinstance(start_ts, pd.Timestamp):
                        df = df[df.index >= start_ts]
                    if isinstance(end_ts, pd.Timestamp):
                        df = df[df.index <= end_ts]

                    # Reorder columns to preserve input order
                    present_in_order = [
                        s.name for s in series_list if s.name in df.columns
                    ]
                    # Ensure unique order in case of duplicates
                    seen_present = set()
                    present_in_order = [
                        c
                        for c in present_in_order
                        if not (c in seen_present or seen_present.add(c))
                    ]
                    df = df[present_in_order]

                    # Sort dates descending as requested
                    df = df.sort_index(ascending=False)

                    # Convert to column-oriented format like /api/series and /favorites
                    df_indexed = df.reset_index()

                    column_dict = OrderedDict()

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

                    # Return as JSON with preserved column order
                    return Response(
                        json.dumps(column_dict, ensure_ascii=False),
                        mimetype="application/json",
                    )
                else:
                    # No data available
                    return Response(
                        json.dumps({"Date": []}, ensure_ascii=False),
                        mimetype="application/json",
                    )

        except Exception as e:
            logger.exception(f"Error retrieving custom timeseries: {e}")
            return jsonify({"error": f"Internal server error: {str(e)}"}), 500

    @app.server.route("/api/upload_data", methods=["POST"])
    def upload_data():
        """
        POST /api/upload_data - Upload timeseries data in bulk (updates existing data).

        Request body should be a JSON list with the following structure:
        [
            {"date": "2024-01-01", "code": "AAPL", "value": 150.0},
            {"date": "2024-01-01", "code": "MSFT", "value": 380.0},
            ...
        ]

        Required fields:
        - date: Date string (will be parsed to datetime)
        - code: Timeseries code (must exist in database)
        - value: Numeric value

        Behavior:
        - Merges new data with existing data
        - For overlapping dates, new data takes precedence
        - Preserves all existing data points that don't overlap
        """
        try:
            # Ensure MongoDB connection
            ensure_connection()

            # Get the JSON payload
            payload = request.get_json()

            if not isinstance(payload, list):
                return (
                    jsonify({"error": "Invalid payload: expected a list of records."}),
                    400,
                )

            # Convert to DataFrame
            df = pd.DataFrame(payload)
            required_columns = {"date", "code", "value"}
            missing = required_columns - set(df.columns)
            if missing:
                return (
                    jsonify({"error": f"Missing required fields: {missing}"}),
                    400,
                )

            # Clean the data
            # Convert 'value' to numeric, coercing errors to NaN
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            # Drop rows where 'value' is NaN
            df = df.dropna(subset=["value"])
            # Convert 'date' to datetime, coercing errors to NaT
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            # Drop rows where 'date' or 'code' is missing
            df = df.dropna(subset=["date", "code"])

            if df.empty:
                return (
                    jsonify({"error": "No valid records to upload after cleaning."}),
                    400,
                )

            # Pivot the DataFrame so each code becomes a column, indexed by date
            pivoted = (
                df.pivot(index="date", columns="code", values="value")
                .sort_index()
                .dropna(how="all", axis=1)
                .dropna(how="all", axis=0)
            )
            pivoted.index = pd.to_datetime(pivoted.index)

            # Update each timeseries in the database
            updated_codes = []
            not_found_codes = []
            for code in pivoted.columns:
                with Session() as session:
                    ts = (
                        session.query(Timeseries)
                        .filter(Timeseries.code == code)
                        .first()
                    )
                    if ts is None:
                        not_found_codes.append(code)
                        continue

                    # Get existing data to merge with new data (within session)
                    data_record = ts._get_or_create_data_record(session)
                    column_data = (
                        data_record.data if data_record and data_record.data else {}
                    )
                    if column_data and len(column_data) > 0:
                        # Convert JSONB dict to pandas Series
                        # JSONB stores dates as strings, convert them back to datetime
                        data_dict = column_data if isinstance(column_data, dict) else {}
                        # Convert string keys to datetime index
                        existing_data = pd.Series(data_dict)
                        if not existing_data.empty:
                            # Convert string dates to datetime index
                            existing_data.index = pd.to_datetime(
                                existing_data.index, errors="coerce"
                            )
                            existing_data = (
                                existing_data.dropna()
                            )  # Remove any invalid dates
                    else:
                        existing_data = pd.Series(dtype=float)

                    # Store new data as a Series with date index and float values
                    new_series = pivoted[code].dropna()

                    if not existing_data.empty:
                        # Merge existing data with new data (new data takes precedence for overlapping dates)
                        combined_data = pd.concat([existing_data, new_series], axis=0)
                        # Remove duplicates, keeping the last occurrence (new data)
                        combined_data = combined_data[
                            ~combined_data.index.duplicated(keep="last")
                        ]
                        combined_data = combined_data.sort_index()  # type: ignore
                    else:
                        # No existing data, just use the new data
                        combined_data = new_series

                    # Convert combined_data to dict format with date strings for JSONB storage
                    # Convert dates to strings for JSONB storage
                    data_dict = {}
                    for k, v in combined_data.to_dict().items():
                        if hasattr(k, "date"):
                            date_str = str(k.date())
                        elif isinstance(k, str):
                            date_str = k
                        else:
                            date_str = str(pd.to_datetime(k).date())
                        data_dict[date_str] = float(v)

                    # Update the timeseries data directly (within session)
                    data_record.data = data_dict
                    data_record.updated = datetime.now()
                    ts.start = (
                        combined_data.index.min().date()
                        if len(combined_data.index) > 0
                        else None
                    )
                    ts.end = (
                        combined_data.index.max().date()
                        if len(combined_data.index) > 0
                        else None
                    )
                    ts.num_data = len(combined_data)
                    ts.updated = datetime.now()

                    session.commit()
                    logger.info(
                        f"Updated {code}: merged {len(new_series)} new points with {len(existing_data) if not existing_data.empty else 0} existing points"
                    )
                    updated_codes.append(code)

            logger.info(
                f"Successfully uploaded data for {len(updated_codes)} timeseries"
            )

            response = {
                "message": f"Successfully received {len(payload)} records.",
                "updated_codes": updated_codes,
                "records_processed": len(df),
            }

            if not_found_codes:
                response["warning"] = f"Codes not found in database: {not_found_codes}"
                logger.warning(f"Codes not found: {not_found_codes}")

            return jsonify(response)

        except Exception as e:
            logger.exception("Failed to process data upload")
            return jsonify({"error": f"Failed to process data upload: {str(e)}"}), 500

    # Register series routes
    series.register_series_routes(app)

    print("API routes registered:")
    print("  - GET /api/health - Health check")
    print("  - GET /api/timeseries - List all timeseries")
    print("  - POST /api/timeseries - Update timeseries metadata (bulk)")
    print("  - GET /api/timeseries/{id} - Get timeseries by ID")
    print("  - GET /api/timeseries/code/{code} - Get timeseries by code")
    print("  - GET /api/timeseries/favorites - Get all favorite timeseries with data")
    print(
        "  - GET /api/timeseries.custom - Get selected timeseries by codes (JSON body)"
    )
    print("  - POST /api/upload_data - Upload timeseries data")
    print("  - GET /api/series - Advanced series data API with comprehensive features")
