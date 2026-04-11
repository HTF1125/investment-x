"""VAMS technicals computation — dashboard index data.

Per-index architecture: each index is fetched and computed independently.
CACRI is computed separately from cross-asset proxies only.
"""

from __future__ import annotations

import threading
import time

import pandas as pd

from ix.core.technical.vams import (
    compute_vams_series,
    score_to_regime,
    weeks_in_regime,
    period_return,
    compute_cacri,
)
from ix.common import get_logger

logger = get_logger(__name__)

# Lock for yfinance calls — yfinance is NOT thread-safe
_yfinance_lock = threading.Lock()

# Per-index cache
_index_cache: dict[str, dict] = {}      # name → full index result dict
_index_cache_ts: dict[str, float] = {}   # name → monotonic timestamp
_CACHE_TTL = 60  # seconds

# CACRI cache (separate — only depends on 8 cross-asset proxies)
_cacri_cache: dict | None = None         # {cacri, cross_asset_vams}
_cacri_cache_ts: float = 0.0
_cacri_compute_lock = threading.Lock()
_cacri_computing: bool = False

INDEX_YF: dict[str, str] = {
    "S&P 500":      "ES=F",
    "Nasdaq 100":   "NQ=F",
    "Russell2K":    "RTY=F",
    "DAX":          "^GDAXI",
    "Nikkei 225":   "^N225",
    "KOSPI":        "^KS11",
    "Dollar":       "^NYICDX",
    "USDKRW":       "USDKRW=X",
    "Gold":         "GC=F",
    "Silver":       "SI=F",
    "Treasury 2Y":  "ZT=F",
    "Treasury 10Y": "ZN=F",
    "Bitcoin":      "BTC-USD",
}

CROSS_ASSET_YF: dict[str, str] = {
    "SPY": "SPY", "TLT": "TLT", "HYG": "HYG", "LQD": "LQD",
    "DBC": "DBC", "GLD": "GLD", "EEM": "EEM", "UUP": "UUP",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resample_weekly(s: pd.Series) -> pd.Series:
    """Resample daily close to weekly (Wednesday)."""
    if s.empty:
        return s
    from ix.common.data.transforms import Resample
    return Resample(s, "W-WED", ffill=True)


def _compute_vomo(df: pd.DataFrame, days: int) -> float | None:
    """VOMO = Return% / Average ATR% over the period."""
    if len(df) < days + 1:
        return None
    recent = df.tail(days + 1)
    close = recent["Close"].squeeze()
    high = recent["High"].squeeze()
    low = recent["Low"].squeeze()
    prev_close = close.shift(1)

    ret_pct = (float(close.iloc[-1]) / float(close.iloc[0]) - 1) * 100

    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    avg_atr_pct = (tr / close).mean() * 100

    if avg_atr_pct == 0 or pd.isna(avg_atr_pct):
        return None
    return round(ret_pct / avg_atr_pct, 2)


def _compute_vomo_history(df: pd.DataFrame) -> dict:
    """Compute weekly rolling VOMO composite series for chart shading."""
    close = df["Close"].squeeze()
    high = df["High"].squeeze()
    low = df["Low"].squeeze()
    prev_close = close.shift(1)

    tr = pd.concat([
        high - low, (high - prev_close).abs(), (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr_pct = tr / close

    results_dates = []
    results_values = []

    indices = list(range(252, len(df), 5))  # start after 1Y warmup
    if indices and indices[-1] != len(df) - 1:
        indices.append(len(df) - 1)

    for i in indices:
        composites = []
        for days, weight in [(21, 0.2), (126, 0.4), (252, 0.4)]:
            if i < days:
                continue
            ret_pct = (float(close.iloc[i]) / float(close.iloc[i - days]) - 1) * 100
            avg_atr = float(atr_pct.iloc[i - days:i].mean()) * 100
            if avg_atr > 0:
                composites.append((weight, ret_pct / avg_atr))
        if composites:
            total_w = sum(w for w, _ in composites)
            comp = sum(w * v for w, v in composites) / total_w if total_w > 0 else 0
            results_dates.append(df.index[i].strftime("%Y-%m-%d"))
            results_values.append(round(comp, 2))

    return {"dates": results_dates, "values": results_values}


# ---------------------------------------------------------------------------
# Per-index compute
# ---------------------------------------------------------------------------

SHORT_W, MEDIUM_W = 4, 13


def _compute_index(name: str, df: pd.DataFrame) -> dict | None:
    """Compute VAMS regime, VOMO scores, and OHLCV for a single index."""
    try:
        if df.empty or len(df) < 100:
            return None

        five_years_ago = pd.Timestamp.now() - pd.DateOffset(years=5)

        close = df["Close"].squeeze().dropna()
        weekly = _resample_weekly(close)
        if weekly.empty or len(weekly) < SHORT_W + MEDIUM_W + 1:
            return None

        vams_scores = compute_vams_series(weekly, SHORT_W, MEDIUM_W)
        valid_scores = vams_scores.dropna()
        if valid_scores.empty:
            return None

        current_score = int(valid_scores.iloc[-1])
        regime = score_to_regime(current_score)
        weeks_in = weeks_in_regime(valid_scores)

        vomo_1m = _compute_vomo(df, 21)
        vomo_6m = _compute_vomo(df, 126)
        vomo_1y = _compute_vomo(df, 252)

        vomo_composite = None
        if vomo_1m is not None and vomo_6m is not None and vomo_1y is not None:
            vomo_composite = round(0.2 * vomo_1m + 0.4 * vomo_6m + 0.4 * vomo_1y, 2)

        vomo_history = _compute_vomo_history(df)

        df_5y = df[df.index >= five_years_ago].dropna(subset=["Close"])

        # Daily return (last two closes)
        daily_ret = None
        if len(close) >= 2 and close.iloc[-2] != 0:
            daily_ret = round(
                ((float(close.iloc[-1]) - float(close.iloc[-2])) / float(close.iloc[-2])) * 100, 2
            )

        return {
            "name": name,
            "regime": regime,
            "score": current_score,
            "price": round(float(close.iloc[-1]), 2),
            "daily_ret": daily_ret,
            "ret_1m": period_return(close, 4),
            "ret_3m": period_return(close, 13),
            "ret_6m": period_return(close, 26),
            "ret_1y": period_return(close, 52),
            "weeks_in_regime": weeks_in,
            "vomo": {
                "1m": vomo_1m,
                "6m": vomo_6m,
                "1y": vomo_1y,
                "composite": vomo_composite,
                "history": vomo_history,
            },
            "daily_prices": {
                "dates":  [d.strftime("%Y-%m-%d") for d in df_5y.index],
                "open":   [round(float(v), 2) for v in df_5y["Open"].values],
                "high":   [round(float(v), 2) for v in df_5y["High"].values],
                "low":    [round(float(v), 2) for v in df_5y["Low"].values],
                "close":  [round(float(v), 2) for v in df_5y["Close"].values],
                "volume": [int(v) if not pd.isna(v) else 0 for v in df_5y["Volume"].values],
            },
            "weekly_vams": {
                "dates": [d.strftime("%Y-%m-%d") for d in valid_scores.index],
                "scores": [int(v) for v in valid_scores.values],
            },
        }
    except Exception:
        logger.exception(f"Failed to compute VAMS regime for {name}")
        return None


def _compute_cross_asset(ca_name: str, df: pd.DataFrame) -> tuple[str, int] | None:
    """Compute cross-asset VAMS score for CACRI."""
    try:
        if df.empty:
            return None
        close = df["Close"].squeeze().dropna()
        weekly = _resample_weekly(close)
        if weekly.empty or len(weekly) < SHORT_W + MEDIUM_W + 1:
            return None
        ca_scores = compute_vams_series(weekly, SHORT_W, MEDIUM_W).dropna()
        if ca_scores.empty:
            return None
        return (ca_name, int(ca_scores.iloc[-1]))
    except Exception:
        logger.warning(f"Failed to compute cross-asset VAMS for {ca_name}")
        return None


def compute_single(index_name: str) -> dict | None:
    """Download and compute VAMS/VOMO for a single index."""
    from ix.collectors.crawler import get_yahoo_data

    yf_ticker = INDEX_YF.get(index_name)
    if yf_ticker is None:
        return None

    with _yfinance_lock:
        try:
            df = get_yahoo_data(yf_ticker)
        except Exception:
            logger.warning(f"Failed to download {index_name} ({yf_ticker})")
            return None

    return _compute_index(index_name, df)


# ---------------------------------------------------------------------------
# CACRI (cross-asset only — independent of indices)
# ---------------------------------------------------------------------------

def _compute_cacri_snapshot() -> dict:
    """Download 8 cross-asset tickers, compute current CACRI. Cached."""
    global _cacri_cache, _cacri_cache_ts

    if _cacri_cache is not None and (time.monotonic() - _cacri_cache_ts) < _CACHE_TTL:
        return _cacri_cache

    from ix.collectors.crawler import get_yahoo_data

    cross_asset_vams: dict[str, int] = {}
    with _yfinance_lock:
        for ca_name, yf_ticker in CROSS_ASSET_YF.items():
            try:
                df = get_yahoo_data(yf_ticker)
                result = _compute_cross_asset(ca_name, df)
                if result is not None:
                    cross_asset_vams[result[0]] = result[1]
            except Exception:
                logger.warning(f"Failed to download cross-asset {ca_name}")

    snapshot = {
        "cacri": compute_cacri(cross_asset_vams),
        "cross_asset_vams": cross_asset_vams,
    }
    _cacri_cache = snapshot
    _cacri_cache_ts = time.monotonic()
    return snapshot


# ---------------------------------------------------------------------------
# Cached access (used by router)
# ---------------------------------------------------------------------------

def get_or_compute_index(name: str) -> dict | None:
    """Return cached index data or compute on miss (single yfinance call)."""
    now = time.monotonic()
    ts = _index_cache_ts.get(name, 0.0)
    if name in _index_cache and (now - ts) < _CACHE_TTL:
        return _index_cache[name]

    result = compute_single(name)
    if result is not None:
        _index_cache[name] = result
        _index_cache_ts[name] = time.monotonic()
    return result


_indices_compute_lock = threading.Lock()
_indices_computing: bool = False


def ensure_cacri_background() -> None:
    """Kick off a background thread to populate CACRI cache if not already running."""
    global _cacri_computing
    with _cacri_compute_lock:
        if _cacri_computing:
            return
        _cacri_computing = True

    def _worker() -> None:
        global _cacri_computing
        try:
            _compute_cacri_snapshot()
        except Exception:
            logger.exception("Background CACRI compute failed")
        finally:
            with _cacri_compute_lock:
                _cacri_computing = False

    threading.Thread(target=_worker, name="cacri-compute", daemon=True).start()


def ensure_indices_background() -> None:
    """Kick off a background thread to warm up the per-index cache."""
    global _indices_computing
    with _indices_compute_lock:
        if _indices_computing:
            return
        now = time.monotonic()
        stale = [
            name for name in INDEX_YF
            if name not in _index_cache
            or (now - _index_cache_ts.get(name, 0.0)) >= _CACHE_TTL
        ]
        if not stale:
            return
        _indices_computing = True

    def _worker() -> None:
        global _indices_computing
        try:
            for name in stale:
                try:
                    result = compute_single(name)
                    if result is not None:
                        _index_cache[name] = result
                        _index_cache_ts[name] = time.monotonic()
                except Exception:
                    logger.exception(f"Background compute failed for {name}")
        finally:
            with _indices_compute_lock:
                _indices_computing = False

    threading.Thread(target=_worker, name="indices-compute", daemon=True).start()


def _strip_heavy(idx: dict) -> dict:
    """Remove chart-weight fields from an index dict."""
    light = {k: v for k, v in idx.items() if k not in ("daily_prices", "weekly_vams")}
    if "vomo" in idx:
        light["vomo"] = {k: v for k, v in idx["vomo"].items() if k != "history"}
    return light


def get_summary() -> dict:
    """Non-blocking summary: static name list + whatever is already cached.

    Never triggers yfinance downloads — returns instantly.
    Indices without cached data get a stub with just the name.
    """
    light_indices = []
    for name in INDEX_YF:
        cached = _index_cache.get(name)
        if cached and (time.monotonic() - _index_cache_ts.get(name, 0.0)) < _CACHE_TTL:
            light_indices.append(_strip_heavy(cached))
        else:
            # Stub entry — frontend uses this for the dropdown
            light_indices.append({"name": name})

    # CACRI: return cached value; kick off background compute if stale/missing
    cacri_stale = (
        _cacri_cache is None
        or (time.monotonic() - _cacri_cache_ts) >= _CACHE_TTL
    )
    if cacri_stale:
        ensure_cacri_background()
    cacri_snap = _cacri_cache if _cacri_cache is not None else {"cacri": 0.0, "cross_asset_vams": {}}

    # Indices: kick off background warm-up for any missing/stale entries
    ensure_indices_background()

    return {
        "indices": light_indices,
        "cacri": cacri_snap["cacri"],
        "cross_asset_vams": cacri_snap["cross_asset_vams"],
        "computed_at": pd.Timestamp.now(tz="UTC").isoformat(),
    }


def get_detail(index: str) -> dict | None:
    """Full data for a single index (fetches on cache miss — 1 yfinance call).

    Returns ALL fields: summary + chart data.  The frontend uses this as
    the primary data source for the selected index.
    """
    idx = get_or_compute_index(index)
    if idx is None:
        return None
    return idx


def refresh_single(index_name: str) -> dict | None:
    """Clear one index from cache, recompute, return full result."""
    _index_cache.pop(index_name, None)
    _index_cache_ts.pop(index_name, None)
    return get_or_compute_index(index_name)


# ---------------------------------------------------------------------------
# CACRI history (unchanged — already cross-asset only)
# ---------------------------------------------------------------------------

def compute_cacri_history() -> dict:
    """Compute full CACRI history response via crawler, persist to DB cache."""
    from ix.collectors.crawler import get_yahoo_data
    from ix.db.conn import Session as SessionCtx
    from ix.db.models.api_cache import ApiCache

    all_scores: dict[str, pd.Series] = {}
    with _yfinance_lock:
        for ca_name, yf_ticker in CROSS_ASSET_YF.items():
            try:
                df = get_yahoo_data(yf_ticker)
                if df.empty:
                    continue
                close = df["Close"].squeeze().dropna()
                weekly = _resample_weekly(close)
                if weekly.empty or len(weekly) < SHORT_W + MEDIUM_W + 1:
                    continue
                scores = compute_vams_series(weekly, SHORT_W, MEDIUM_W).dropna()
                if not scores.empty:
                    all_scores[ca_name] = scores
            except Exception:
                logger.warning(f"CACRI history: failed for {ca_name}")

    if not all_scores:
        return {"dates": [], "cacri": [], "assets": {}}

    df = pd.DataFrame(all_scores)
    df = df.dropna(how="all")

    def _row_cacri(row: pd.Series) -> float | None:
        valid = row.dropna()
        if valid.empty:
            return None
        return round(float((valid <= -1).sum() / len(valid)), 4)

    cacri_series = df.apply(_row_cacri, axis=1).dropna()

    assets: dict[str, dict] = {}
    for col in df.columns:
        s = df[col].dropna()
        assets[col] = {
            "dates": [d.strftime("%Y-%m-%d") for d in s.index],
            "scores": [int(v) for v in s.values],
        }

    response = {
        "dates": [d.strftime("%Y-%m-%d") for d in cacri_series.index],
        "cacri": [round(float(v) * 100, 1) for v in cacri_series.values],
        "assets": assets,
        "computed_at": pd.Timestamp.now(tz="UTC").isoformat(),
    }

    with SessionCtx() as session:
        entry = session.query(ApiCache).get("cacri-history")
        if entry:
            entry.value = response
        else:
            session.add(ApiCache(key="cacri-history", value=response))

    return response
