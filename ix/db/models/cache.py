"""In-memory cache for parsed timeseries data.

Key: timeseries_id (str)
Value: (updated_timestamp, parsed_series, monotonic_time)

TTL is absolute from write time — accessing an entry does NOT reset its expiry.
Eviction is FIFO: when the cache exceeds ``_TS_CACHE_MAX`` entries, the oldest
25% (by insertion order) are removed before the new entry is stored.

threading.Lock is appropriate here: all access comes from sync ``def``
route handlers (run in FastAPI's default threadpool) or from
``asyncio.to_thread()`` calls.  No coroutine ever touches the cache
directly, so the lock never blocks the event loop.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Dict, Optional

import pandas as pd

_ts_cache: Dict[str, tuple] = {}
_ts_cache_lock = threading.Lock()
_TS_CACHE_MAX = 48  # max entries before eviction
_TS_CACHE_TTL = 180  # 3-minute TTL in seconds


def _cache_get(ts_id: str, updated: Optional[datetime]) -> Optional[pd.Series]:
    """Return cached Series if still valid, else None.

    Validity requires both:
    1. The entry is younger than ``_TS_CACHE_TTL`` seconds (absolute, not reset on read).
    2. The ``updated`` timestamp matches the one stored at write time.
    """
    with _ts_cache_lock:
        entry = _ts_cache.get(str(ts_id))
    if entry is None:
        return None
    cached_updated, cached_series, cached_time = entry
    # TTL check — expire after _TS_CACHE_TTL seconds
    if time.monotonic() - cached_time > _TS_CACHE_TTL:
        _cache_invalidate(ts_id)
        return None
    if updated is not None and cached_updated == updated:
        return cached_series.copy()
    return None


def _cache_put(ts_id: str, updated: Optional[datetime], series: pd.Series) -> None:
    """Store parsed Series in cache.

    If the cache is full, the oldest 25% of entries (by insertion order)
    are evicted before storing the new entry.
    """
    with _ts_cache_lock:
        if len(_ts_cache) >= _TS_CACHE_MAX:
            # Evict oldest 25%
            to_remove = list(_ts_cache.keys())[: _TS_CACHE_MAX // 4]
            for k in to_remove:
                _ts_cache.pop(k, None)
        _ts_cache[str(ts_id)] = (updated, series.copy(), time.monotonic())


def _cache_invalidate(ts_id: str) -> None:
    """Remove a specific entry from cache."""
    with _ts_cache_lock:
        _ts_cache.pop(str(ts_id), None)
