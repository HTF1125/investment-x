"""
Time-based caching system for dashboard data.
Provides 5-minute caching to avoid reloading data on refresh.
"""

import time
import threading
from typing import Any, Dict, Optional, Callable
from functools import wraps
import pandas as pd
from ix.misc import get_logger

logger = get_logger(__name__)


class TimeBasedCache:
    """
    A thread-safe time-based cache that expires entries after a specified time.
    """

    def __init__(self, default_ttl: int = 300):  # 5 minutes default
        """
        Initialize the cache.

        Args:
            default_ttl: Default time-to-live in seconds (300 = 5 minutes)
        """
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()

    def _make_key(self, func_name: str, *args, **kwargs) -> str:
        """Create a cache key from function name and arguments."""
        # Convert args and kwargs to strings, handling pandas DataFrames
        key_parts = [func_name]

        for arg in args:
            if isinstance(arg, pd.DataFrame):
                # Use shape and columns for DataFrame
                key_parts.append(f"df_{arg.shape}_{tuple(arg.columns)}")
            elif isinstance(arg, str):
                key_parts.append(f"s_{arg}")
            else:
                key_parts.append(str(arg))

        for key, value in sorted(kwargs.items()):
            if isinstance(value, pd.DataFrame):
                key_parts.append(f"{key}_df_{value.shape}_{tuple(value.columns)}")
            elif isinstance(value, str):
                key_parts.append(f"{key}_s_{value}")
            else:
                key_parts.append(f"{key}_{str(value)}")

        return "|".join(key_parts)

    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache if it exists and hasn't expired."""
        with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            if time.time() > entry["expires_at"]:
                # Entry has expired, remove it
                del self._cache[key]
                logger.debug(f"Cache entry expired and removed: {key}")
                return None

            logger.debug(f"Cache hit: {key}")
            return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in the cache with optional TTL override."""
        if ttl is None:
            ttl = self.default_ttl

        with self._lock:
            self._cache[key] = {
                "value": value,
                "expires_at": time.time() + ttl,
                "created_at": time.time(),
            }
            logger.debug(f"Cache set: {key} (TTL: {ttl}s)")

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")

    def cleanup_expired(self) -> int:
        """Remove all expired entries and return count of removed entries."""
        with self._lock:
            current_time = time.time()
            expired_keys = [
                key
                for key, entry in self._cache.items()
                if current_time > entry["expires_at"]
            ]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            current_time = time.time()
            active_entries = sum(
                1
                for entry in self._cache.values()
                if current_time <= entry["expires_at"]
            )

            return {
                "total_entries": len(self._cache),
                "active_entries": active_entries,
                "expired_entries": len(self._cache) - active_entries,
                "default_ttl": self.default_ttl,
            }


# Global cache instance
_dashboard_cache = TimeBasedCache(default_ttl=300)  # 5 minutes


def cached(ttl: Optional[int] = None):
    """
    Decorator for caching function results with time-based expiration.

    Args:
        ttl: Time-to-live in seconds. If None, uses cache default (5 minutes).

    Usage:
        @cached(ttl=300)  # Cache for 5 minutes
        def expensive_function(param1, param2):
            return expensive_computation(param1, param2)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            cache_key = _dashboard_cache._make_key(func.__name__, *args, **kwargs)

            # Try to get from cache
            cached_result = _dashboard_cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Execute function and cache result
            try:
                result = func(*args, **kwargs)
                _dashboard_cache.set(cache_key, result, ttl)
                return result
            except Exception as e:
                logger.error(f"Error in cached function {func.__name__}: {e}")
                raise

        return wrapper

    return decorator


def clear_cache():
    """Clear all cached data."""
    _dashboard_cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    return _dashboard_cache.get_stats()


def cleanup_expired_cache() -> int:
    """Clean up expired cache entries."""
    return _dashboard_cache.cleanup_expired()


# Convenience function for universe data caching
@cached(ttl=300)  # 5 minutes
def get_cached_universe_data(
    universe_name: str, start_date: str, end_date: str
) -> pd.DataFrame:
    """
    Cache universe data with 5-minute expiration.
    This replaces the lru_cache version with time-based caching.
    """
    from ix.db import models

    try:
        # Get universe from MongoDB using Bunnet ODM
        universe_db = models.Universe.find_one(
            models.Universe.name == universe_name
        ).run()
        if not universe_db:
            logger.warning(f"Universe '{universe_name}' not found")
            return pd.DataFrame()

        # Get assets and build timeseries DataFrame
        assets = universe_db.assets
        asset_codes = [asset.code + ":PX_LAST" for asset in assets if asset.code]

        if not asset_codes:
            return pd.DataFrame()

        # Fetch all timeseries using Bunnet ODM
        ts_list = []
        for code in asset_codes:
            ts = models.Timeseries.find_one(models.Timeseries.code == code).run()
            if ts:
                ts_list.append(ts)

        # Build DataFrame with asset names as columns
        series_dict = {}
        for ts in ts_list:
            for asset in assets:
                if asset.code and asset.code + ":PX_LAST" == ts.code:
                    series_dict[asset.name or asset.code] = ts.data
                    break

        pxs = pd.DataFrame(series_dict)

        # Apply date range filter
        result = pxs.loc[start_date:end_date] if not pxs.empty else pd.DataFrame()

        logger.info(
            f"Loaded and cached data for {universe_name} ({start_date} to {end_date})"
        )
        return result
    except Exception as e:
        logger.error(f"Error loading {universe_name}: {e}")
        return pd.DataFrame()
