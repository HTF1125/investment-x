"""
API endpoints for the ix.web application.
These are Flask routes that extend the Dash app server.
"""

from flask import jsonify, request, Response
from typing import Dict, Any, List, Optional
import pandas as pd
from ix.db.models import Timeseries, Insights, Publishers
from ix.db.conn import ensure_connection
from ix.misc import get_logger
from datetime import datetime
from bson import ObjectId
import re
import ast
import time
from ix.db.custom import FinancialConditionsIndexUS

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

        # Execute query with pagination
        timeseries_query = Timeseries.find(query)

        if offset:
            timeseries_query = timeseries_query.skip(offset)
        if limit:
            timeseries_query = timeseries_query.limit(limit)

        timeseries_list = list(timeseries_query.run())

        formatted_timeseries = []

        for ts in timeseries_list:
            formatted_ts = {
                "id": str(ts.id),  # Use MongoDB ObjectId as string
                "code": ts.code,
                "name": ts.name,
                "provider": ts.provider,
                "asset_class": ts.asset_class,
                "category": ts.category,
                "start": ts.start.isoformat() if ts.start else None,
                "end": ts.end.isoformat() if ts.end else None,
                "source": ts.source,
                "source_code": ts.source_code,
                "frequency": ts.frequency,
                "unit": ts.unit,
                "scale": ts.scale,
                "currency": ts.currency,
                "country": ts.country,
                "num_data": ts.num_data,
                "remark": ts.remark,
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
                # Find existing timeseries by code
                ts = Timeseries.find_one({"code": code}).run()

                if ts is None:
                    # Create new timeseries
                    ts = Timeseries(code=code)
                    ts.create()
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
                    ("source_code", 100),
                    ("frequency", 20),
                    ("unit", 50),
                    ("currency", 10),
                    ("country", 100),
                ]

                update_data = {}
                for field, max_length in string_fields:
                    if field in ts_data:
                        value = ts_data[field]
                        if value is not None:
                            value = str(value)[:max_length]
                        update_data[field] = value

                # Text field (no length limit)
                if "remark" in ts_data:
                    value = ts_data["remark"]
                    if value is not None:
                        value = str(value)
                    update_data["remark"] = value

                # Integer field with overflow protection
                if "scale" in ts_data:
                    value = ts_data["scale"]
                    if value is not None:
                        try:
                            # Ensure scale is within reasonable range
                            scale_value = int(value)
                            if scale_value > 2147483647 or scale_value < -2147483648:
                                logger.warning(
                                    f"Scale value {scale_value} out of range for {code}, setting to 1"
                                )
                                scale_value = 1
                            update_data["scale"] = scale_value
                        except (ValueError, TypeError):
                            logger.warning(
                                f"Invalid scale value '{value}' for {code}, setting to 1"
                            )
                            update_data["scale"] = 1

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
                            update_data["num_data"] = num_data_value
                        except (ValueError, TypeError):
                            logger.warning(
                                f"Invalid num_data value '{value}' for {code}, setting to None"
                            )
                            update_data["num_data"] = None

                # Date fields
                if "start" in ts_data and ts_data["start"]:
                    try:
                        from datetime import datetime

                        update_data["start"] = datetime.fromisoformat(
                            ts_data["start"].replace("Z", "+00:00")
                        ).date()
                    except (ValueError, TypeError):
                        logger.warning(
                            f"Invalid start date '{ts_data['start']}' for {code}"
                        )

                if "end" in ts_data and ts_data["end"]:
                    try:
                        from datetime import datetime

                        update_data["end"] = datetime.fromisoformat(
                            ts_data["end"].replace("Z", "+00:00")
                        ).date()
                    except (ValueError, TypeError):
                        logger.warning(
                            f"Invalid end date '{ts_data['end']}' for {code}"
                        )

                # Update the document
                if update_data:
                    ts.set(update_data)

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

        # Get timeseries by code (primary key in MongoDB)
        ts = Timeseries.find_one({"code": timeseries_id}).run()

        if not ts:
            return jsonify({"error": "Timeseries not found"}), 404

        # Format the timeseries object
        formatted_ts = {
            "id": str(ts.id),  # Use MongoDB ObjectId as string
            "code": ts.code,
            "name": ts.name,
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
        }

        # Add full data
        try:
            data = ts.data
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

        # Get timeseries by code
        ts = Timeseries.find_one({"code": code}).run()

        if not ts:
            return (
                jsonify({"error": f"Timeseries with code '{code}' not found"}),
                404,
            )

        # Format the timeseries object
        formatted_ts = {
            "id": str(ts.id),
            "code": ts.code,
            "name": ts.name,
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

    @app.server.route("/api/insights", methods=["GET"])
    def get_insights():
        """
        GET /api/insights - List all insights with optional filtering and pagination.

        Query parameters:
        - limit: Limit number of results
        - offset: Offset for pagination (default: 0)
        - issuer: Filter by issuer
        - status: Filter by status (new, read, archived, etc.)
        - from_date: Filter by published_date >= from_date (YYYY-MM-DD)
        - to_date: Filter by published_date <= to_date (YYYY-MM-DD)

        Note: Content (PDF binary) is not included in the response.
        """
        # Ensure MongoDB connection
        ensure_connection()

        # Get query parameters
        limit = request.args.get("limit", type=int)
        offset = request.args.get("offset", 0, type=int)
        issuer = request.args.get("issuer")
        status = request.args.get("status")
        from_date = request.args.get("from_date")
        to_date = request.args.get("to_date")

        # Build MongoDB query
        query = {}

        # Apply filters
        if issuer:
            query["issuer"] = {"$regex": issuer, "$options": "i"}
        if status:
            query["status"] = status
        if from_date:
            try:
                from datetime import datetime

                from_dt = datetime.strptime(from_date, "%Y-%m-%d").date()
                query["published_date"] = {"$gte": from_dt}
            except ValueError:
                return (
                    jsonify({"error": f"Invalid from_date format: {from_date}"}),
                    400,
                )
        if to_date:
            try:
                from datetime import datetime

                to_dt = datetime.strptime(to_date, "%Y-%m-%d").date()
                if "published_date" in query:
                    query["published_date"]["$lte"] = to_dt
                else:
                    query["published_date"] = {"$lte": to_dt}
            except ValueError:
                return jsonify({"error": f"Invalid to_date format: {to_date}"}), 400

        # Execute query with pagination and sorting
        insights_query = Insights.find(query).sort("-published_date")

        if offset:
            insights_query = insights_query.skip(offset)
        if limit:
            insights_query = insights_query.limit(limit)

        insights_list = list(insights_query.run())

        formatted_insights = []

        for insight in insights_list:
            formatted_insight = {
                "id": str(insight.id),
                "issuer": insight.issuer,
                "name": insight.name,
                "published_date": (
                    insight.published_date.isoformat()
                    if insight.published_date
                    else None
                ),
                "summary": insight.summary,
                "status": insight.status,
                "has_content": True,  # MongoDB stores content separately via Boto
                "created_at": (
                    insight.created_at.isoformat()
                    if hasattr(insight, "created_at") and insight.created_at
                    else None
                ),
                "updated_at": (
                    insight.updated_at.isoformat()
                    if hasattr(insight, "updated_at") and insight.updated_at
                    else None
                ),
            }
            formatted_insights.append(formatted_insight)

        logger.info(f"Retrieved {len(formatted_insights)} insights records")
        return jsonify(formatted_insights)

    @app.server.route("/api/insights/<int:insight_id>", methods=["GET"])
    def get_insight_by_id(insight_id):
        """
        GET /api/insights/{id} - Get detailed insight information by ID.

        Note: Content (PDF binary) is not included. Use /api/download-pdf/{id} to get the PDF.
        """
        # Ensure MongoDB connection
        ensure_connection()

        # Get insight by id
        insight = Insights.find_one({"id": str(insight_id)}).run()

        if not insight:
            return jsonify({"error": "Insight not found"}), 404

        # Format the insight object
        formatted_insight = {
            "id": str(insight.id),
            "issuer": insight.issuer,
            "name": insight.name,
            "published_date": (
                insight.published_date.isoformat() if insight.published_date else None
            ),
            "summary": insight.summary,
            "status": insight.status,
            "has_content": True,  # MongoDB stores content separately via Boto
            "content_size": 0,  # Size not directly available in MongoDB model
            "created_at": (
                insight.created_at.isoformat()
                if hasattr(insight, "created_at") and insight.created_at
                else None
            ),
            "updated_at": (
                insight.updated_at.isoformat()
                if hasattr(insight, "updated_at") and insight.updated_at
                else None
            ),
        }

        return jsonify(formatted_insight)

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
                ts = Timeseries.find_one({"code": code}).run()
                if ts is None:
                    not_found_codes.append(code)
                    continue

                # Get existing data to merge with new data
                existing_data = ts.data

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
                    # Ensure it's a Series before assignment
                    ts.data = combined_data  # type: ignore
                    logger.info(
                        f"Updated {code}: merged {len(new_series)} new points with {len(existing_data)} existing points"
                    )
                else:
                    # No existing data, just set the new data
                    ts.data = new_series  # type: ignore
                    logger.info(
                        f"Created {code}: set {len(new_series)} new data points"
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

    @app.server.route("/api/publisher-visit", methods=["POST"])
    def track_publisher_visit():
        """
        POST /api/publisher-visit - Track when a publisher link is visited

        Request body:
        {
            "url": "publisher_url",
            "name": "publisher_name"
        }
        """
        try:
            # Ensure MongoDB connection
            ensure_connection()

            data = request.get_json()
            publisher_url = data.get("url")

            if not publisher_url:
                return jsonify({"error": "URL is required"}), 400

            # Find and update the publisher
            publisher = Publishers.find_one({"url": publisher_url}).run()

            if publisher:
                publisher.set({"last_visited": datetime.now()})
                logger.info(f"Updated last_visited for publisher: {publisher.name}")
                return jsonify(
                    {
                        "success": True,
                        "message": f"Updated last visited for {publisher.name}",
                        "timestamp": publisher.last_visited.isoformat(),
                    }
                )
            else:
                return jsonify({"error": "Publisher not found"}), 404

        except Exception as e:
            logger.exception("Failed to track publisher visit")
            return jsonify({"error": str(e)}), 500

    def _download_pdf_impl(insight_id: int):
        """
        Common implementation for PDF download by insight id.

        Returns the PDF file stored in the database for the given insight ID
        """
        try:
            from flask import send_file
            import io

            # Ensure MongoDB connection
            ensure_connection()

            # Get the insight with PDF content
            insight = Insights.find_one({"id": str(insight_id)}).run()

            if not insight:
                return jsonify({"error": "Insight not found"}), 404

            # Get PDF content from Boto storage
            try:
                content = insight.get_content()
            except Exception as e:
                logger.error(f"Failed to get PDF content for insight {insight_id}: {e}")
                return (
                    jsonify({"error": "No PDF content available for this insight"}),
                    404,
                )

            if not content or len(content) == 0:
                return (
                    jsonify({"error": "No PDF content available for this insight"}),
                    404,
                )

            # Create filename from insight metadata
            # Format: YYYYMMDD_issuer_title.pdf
            if insight.published_date:
                date_str = insight.published_date.strftime("%Y%m%d")
            else:
                date_str = "unknown"

            issuer_clean = (
                (insight.issuer or "unknown").replace(" ", "_").replace("/", "_")
            )
            title_clean = (
                (insight.name or "document").replace(" ", "_").replace("/", "_")
            )
            # Truncate title if too long
            if len(title_clean) > 50:
                title_clean = title_clean[:50]

            filename = f"{date_str}_{issuer_clean}_{title_clean}.pdf"

            # Create BytesIO object from binary content
            pdf_io = io.BytesIO(content)
            pdf_io.seek(0)

            logger.info(f"Serving PDF download for insight ID {insight_id}: {filename}")

            # Send file with proper headers for download (Flask compatibility)
            try:
                # Flask >= 2.0
                return send_file(
                    pdf_io,
                    mimetype="application/pdf",
                    as_attachment=True,
                    download_name=filename,
                )
            except TypeError:
                # Flask < 2.0 fallback (download_name not supported)
                return send_file(
                    pdf_io,
                    mimetype="application/pdf",
                    as_attachment=True,
                    attachment_filename=filename,  # type: ignore[arg-type]
                )

        except Exception as e:
            logger.exception(f"Failed to download PDF for insight {insight_id}")
            return jsonify({"error": f"Failed to download PDF: {str(e)}"}), 500

    @app.server.route("/api/download-pdf/<int:insight_id>", methods=["GET"])
    def download_pdf(insight_id):
        # Strict int route
        return _download_pdf_impl(insight_id)

    # Lenient route that accepts string ids and coerces to int
    @app.server.route("/api/download-pdf/<insight_id>", methods=["GET"])
    def download_pdf_str(insight_id):
        try:
            return _download_pdf_impl(int(str(insight_id).strip()))
        except ValueError:
            return jsonify({"error": "Invalid insight id"}), 400

    # Register series routes
    series.register_series_routes(app)

    print("API routes registered:")
    print("  - GET /api/health - Health check")
    print("  - GET /api/timeseries - List all timeseries")
    print("  - POST /api/timeseries - Update timeseries metadata (bulk)")
    print("  - GET /api/timeseries/{id} - Get timeseries by ID")
    print("  - GET /api/timeseries/code/{code} - Get timeseries by code")
    print("  - GET /api/insights - List all insights")
    print("  - GET /api/insights/{id} - Get insight by ID")
    print("  - POST /api/upload_data - Upload timeseries data")
    print("  - POST /api/publisher-visit - Track publisher visits")
    print("  - GET /api/download-pdf/{id} - Download PDF from database")
    print("  - GET /api/series - Advanced series data API with comprehensive features")
