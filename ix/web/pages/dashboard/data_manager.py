"""
Data management module for dashboard.
Handles caching, background refresh, and data loading operations.
"""

import pandas as pd
import time
import threading
import concurrent.futures
from datetime import datetime
from typing import Dict, Any, Optional, Union

from ix.db import Universe, Timeseries
from ix.misc import get_logger
from .visualizations import HeatmapGenerator

logger = get_logger(__name__)

# Global cache for dashboard data
_dashboard_cache = {}
_cache_lock = threading.Lock()
_cache_expiry = {}
CACHE_DURATION = 300  # 5 minutes

# Background refresh thread
_background_refresh_thread = None
_background_refresh_running = False


class DataManager:
    """Manages dashboard data loading, caching, and background refresh operations."""

    @staticmethod
    def get_cached_data(key: str) -> Optional[Any]:
        """Get data from cache if not expired."""
        with _cache_lock:
            if key in _dashboard_cache and key in _cache_expiry:
                if time.time() < _cache_expiry[key]:
                    logger.info(f"Cache hit for {key}")
                    return _dashboard_cache[key]
                else:
                    # Cache expired, remove it
                    del _dashboard_cache[key]
                    del _cache_expiry[key]
                    logger.info(f"Cache expired for {key}")
        return None

    @staticmethod
    def set_cached_data(key: str, data: Any) -> None:
        """Store data in cache with expiry."""
        with _cache_lock:
            _dashboard_cache[key] = data
            _cache_expiry[key] = time.time() + CACHE_DURATION
            logger.info(f"Data cached for {key}")

    @staticmethod
    def load_universe_data_optimized(
        universe_name: str, as_of_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """Optimized function to load data for a single universe."""
        try:
            logger.info(f"Loading data for {universe_name} as of {as_of_date}")
            universe_db = Universe.from_name(universe_name)

            # Batch fetch all timeseries at once
            asset_codes = [
                asset.code + ":PX_LAST"
                for asset in universe_db.assets
                if asset.code is not None
            ]

            if not asset_codes:
                return {
                    "latest_values": None,
                    "performance_matrix": None,
                    "data_available": False,
                    "figure": None,
                    "last_updated": datetime.now().isoformat(),
                }

            # Fetch all timeseries in one query
            re = {}

            # Optimized data fetching - limit to recent data for faster loading
            for asset in universe_db.assets:
                if not asset.code:
                    continue

                try:
                    ts = Timeseries.find_one({"code": asset.code + ":PX_LAST"}).run()
                    if ts:
                        # Safe access to data property with minimal error handling
                        try:
                            ts_data = ts.data
                            if (
                                ts_data is not None
                                and hasattr(ts_data, "empty")
                                and not ts_data.empty
                            ):
                                # Resample to business days and forward fill to avoid NaN
                                resampled_data = ts_data.resample("B").last().ffill()

                                # Limit to last 400 business days for faster processing (includes buffer for 252D calc)
                                recent_data = resampled_data.tail(400)

                                # Filter by as_of_date if provided
                                if as_of_date:
                                    try:
                                        as_of_dt = pd.to_datetime(as_of_date)
                                        recent_data = recent_data.loc[:as_of_dt]
                                    except Exception as e:
                                        logger.warning(
                                            f"Error parsing as_of_date {as_of_date}: {e}"
                                        )

                                if not recent_data.empty:
                                    re[asset.name] = recent_data
                        except Exception as e:
                            logger.warning(
                                f"Error accessing data for {asset.code}: {e}"
                            )
                            continue
                except Exception as e:
                    logger.warning(f"Error loading {asset.code}: {e}")
                    continue

            pxs = pd.DataFrame(re)
            if not pxs.empty:
                # Optimized performance calculation - essential periods
                periods = [1, 5, 21, 63, 252]  # 1D, 1W, 1M, 1Q, 1Y
                perf_matrix = {}

                try:
                    # Ensure we have valid numeric data
                    pxs = pxs.apply(pd.to_numeric, errors="coerce").dropna(how="all")

                    if pxs.empty:
                        return {
                            "latest_values": None,
                            "performance_matrix": None,
                            "data_available": False,
                            "figure": None,
                            "last_updated": datetime.now().isoformat(),
                        }

                    # Data is already resampled to "B" and ffilled, so use directly
                    # Calculate only essential performance metrics for faster loading
                    for p in periods:
                        try:
                            pct = pxs.pct_change(p).ffill().iloc[-1]
                            perf_matrix[f"{p}D"] = pct.to_dict()
                        except Exception as e:
                            logger.warning(
                                f"Error calculating {p}D performance for {universe_name}: {e}"
                            )
                            continue

                    # Store latest values
                    latest_values = pxs.iloc[-1].to_dict()

                except Exception as e:
                    logger.error(f"Error processing data for {universe_name}: {e}")
                    return {
                        "latest_values": None,
                        "performance_matrix": None,
                        "data_available": False,
                        "figure": None,
                        "error": f"Data processing error: {str(e)}",
                        "last_updated": datetime.now().isoformat(),
                    }

                # Generate figures during data loading for pre-loading
                try:
                    # Create performance DataFrame from pre-calculated data
                    perf_data = {"Latest": latest_values}
                    perf_data.update(perf_matrix)
                    perf_df = pd.DataFrame(perf_data)

                    # Generate optimized heatmap figure for pre-loading
                    fig = HeatmapGenerator.performance_heatmap_from_perf_data(
                        perf_df, title=universe_name
                    )

                    # Convert figure to dict for JSON serialization
                    fig_dict = fig.to_dict()

                except Exception as e:
                    logger.warning(f"Error generating figure for {universe_name}: {e}")
                    fig_dict = None

                # Convert numpy arrays to lists for JSON serialization
                def convert_arrays_to_lists(obj):
                    if isinstance(obj, dict):
                        return {k: convert_arrays_to_lists(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_arrays_to_lists(item) for item in obj]
                    elif hasattr(obj, "tolist"):  # numpy array
                        return obj.tolist()
                    else:
                        return obj

                return {
                    "latest_values": convert_arrays_to_lists(latest_values),
                    "performance_matrix": convert_arrays_to_lists(perf_matrix),
                    "data_available": True,
                    "figure": fig_dict,  # Pre-generated figure for instant loading
                    "last_updated": datetime.now().isoformat(),
                }
            else:
                return {
                    "latest_values": None,
                    "performance_matrix": None,
                    "data_available": False,
                    "figure": None,
                    "last_updated": datetime.now().isoformat(),
                }

        except Exception as e:
            logger.error(f"Error loading data for {universe_name}: {e}", exc_info=True)
            return {
                "latest_values": None,
                "performance_matrix": None,
                "data_available": False,
                "figure": None,
                "error": str(e),
                "last_updated": datetime.now().isoformat(),
            }

    @staticmethod
    def refresh_global_dashboard_data() -> Dict[str, Any]:
        """Refresh all dashboard data using parallel processing and caching."""
        universes = [
            "Major Indices",
            "Global Markets",
            "Sectors",
            "Themes",
            "Commodities",
            "Currencies",
        ]

        # Check cache first
        cache_key = "dashboard_data"
        cached_data = DataManager.get_cached_data(cache_key)
        if cached_data:
            return cached_data

        logger.info("Loading dashboard data in parallel...")
        dashboard_data = {}

        # Use fewer workers for faster initial load
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Submit all universe loading tasks
            future_to_universe = {
                executor.submit(
                    DataManager.load_universe_data_optimized, universe
                ): universe
                for universe in universes
            }

            # Collect results as they complete
            for future in concurrent.futures.as_completed(future_to_universe):
                universe = future_to_universe[future]
                try:
                    result = future.result()
                    dashboard_data[universe] = result
                    logger.info(f"Completed loading data for {universe}")
                except Exception as e:
                    logger.error(f"Error loading data for {universe}: {e}")
                    dashboard_data[universe] = {
                        "latest_values": None,
                        "performance_matrix": None,
                        "data_available": False,
                        "figure": None,
                        "error": str(e),
                        "last_updated": datetime.now().isoformat(),
                    }

        # Cache the results
        DataManager.set_cached_data(cache_key, dashboard_data)
        logger.info("Dashboard data loading completed and cached")

        return dashboard_data


class BackgroundRefreshManager:
    """Manages background data refresh operations."""

    @staticmethod
    def background_refresh_worker():
        """Background worker to refresh data without blocking UI."""
        global _background_refresh_running
        _background_refresh_running = True

        while _background_refresh_running:
            try:
                logger.info("Starting background data refresh...")
                start_time = time.time()

                # Refresh data in background
                DataManager.refresh_global_dashboard_data()

                elapsed_time = time.time() - start_time
                logger.info(
                    f"Background refresh completed in {elapsed_time:.2f} seconds"
                )

                # Sleep for 4 minutes before next refresh (cache expires in 5 minutes)
                time.sleep(240)

            except Exception as e:
                logger.error(f"Error in background refresh: {e}")
                time.sleep(60)  # Wait 1 minute before retrying

        logger.info("Background refresh worker stopped")

    @staticmethod
    def start_background_refresh():
        """Start background refresh thread."""
        global _background_refresh_thread

        if (
            _background_refresh_thread is None
            or not _background_refresh_thread.is_alive()
        ):
            _background_refresh_thread = threading.Thread(
                target=BackgroundRefreshManager.background_refresh_worker,
                daemon=True,
                name="DashboardRefreshWorker",
            )
            _background_refresh_thread.start()
            logger.info("Background refresh thread started")

    @staticmethod
    def stop_background_refresh():
        """Stop background refresh thread."""
        global _background_refresh_running, _background_refresh_thread

        _background_refresh_running = False
        if _background_refresh_thread and _background_refresh_thread.is_alive():
            _background_refresh_thread.join(timeout=5)
        logger.info("Background refresh thread stopped")
