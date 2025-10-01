"""
API endpoints for the ix.dash application.
These are Flask routes that extend the Dash app server.
"""

from flask import jsonify, request
from typing import Dict, Any, List, Optional
import pandas as pd
from ix.db.models import Timeseries
from ix.misc import get_logger

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
        return jsonify({"status": "healthy", "service": "ix.dash API"})

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
        try:
            # Get query parameters
            limit = request.args.get("limit", type=int)
            offset = request.args.get("offset", 0, type=int)
            category = request.args.get("category")
            asset_class = request.args.get("asset_class")
            provider = request.args.get("provider")

            # Build query
            query = {}
            if category:
                query["category"] = category
            if asset_class:
                query["asset_class"] = asset_class
            if provider:
                query["provider"] = provider

            # Get timeseries from database
            timeseries_query = Timeseries.find(query)

            # Apply pagination
            if offset:
                timeseries_query = timeseries_query.skip(offset)
            if limit:
                timeseries_query = timeseries_query.limit(limit)

            timeseries_list = timeseries_query.run()

            formatted_timeseries = []

            for ts in timeseries_list:
                formatted_ts = {
                    "id": str(ts.id),
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
                    "parent_id": ts.parent_id,
                    "remark": ts.remark,
                }
                formatted_timeseries.append(formatted_ts)

            logger.info(f"Retrieved {len(formatted_timeseries)} timeseries records")
            return jsonify(formatted_timeseries)

        except Exception as e:
            logger.exception("Failed to fetch timeseries data")
            return jsonify({"error": f"Failed to fetch timeseries data: {str(e)}"}), 500

    @app.server.route("/api/timeseries/<timeseries_id>", methods=["GET"])
    def get_timeseries_by_id(timeseries_id):
        """
        GET /api/timeseries/{id} - Get detailed timeseries information by ID with full data.
        """
        try:
            # Get timeseries by ID
            ts = Timeseries.get(timeseries_id)

            if not ts:
                return jsonify({"error": "Timeseries not found"}), 404

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
                "parent_id": ts.parent_id,
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

        except Exception as e:
            logger.exception(f"Failed to fetch timeseries {timeseries_id}")
            return jsonify({"error": f"Failed to fetch timeseries data: {str(e)}"}), 500

    @app.server.route("/api/timeseries/code/<code>", methods=["GET"])
    def get_timeseries_by_code(code):
        """
        GET /api/timeseries/code/{code} - Get timeseries by its code.
        """
        try:
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
                "parent_id": ts.parent_id,
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
                logger.warning(
                    f"Could not get data stats for timeseries {ts.code}: {e}"
                )
                formatted_ts["data_stats"] = {
                    "count": 0,
                    "last_value": None,
                    "last_date": None,
                    "min": None,
                    "max": None,
                }

            return jsonify(formatted_ts)

        except Exception as e:
            logger.exception(f"Failed to fetch timeseries with code {code}")
            return jsonify({"error": f"Failed to fetch timeseries data: {str(e)}"}), 500

    print("API routes registered:")
    print("  - GET /api/health - Health check")
    print("  - GET /api/timeseries - List all timeseries")
    print("  - GET /api/timeseries/{id} - Get timeseries by ID")
    print("  - GET /api/timeseries/code/{code} - Get timeseries by code")
