from __future__ import annotations

import logging
import time
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session as SessionType

from ix.db.models import Timeseries
from ix.misc.date import today

# TTL cache for crawler results: {source_code: (timestamp, pd.Series)}
_crawler_cache: dict[str, tuple[float, pd.Series]] = {}
_CRAWLER_CACHE_TTL = 900  # 15 minutes

logger = logging.getLogger(__name__)

# Re-export transforms so legacy custom chart code using
# `from ix.db.query import ...` continues to work.
from ix.core.transforms import (  # noqa: F401
    Clip,
    CycleForecast,
    Diff,
    Drawdown,
    Ffill,
    MonthEndOffset,
    MonthsOffset,
    MovingAverage,
    Offset,
    PctChange,
    Rebase,
    Resample,
    StandardScalar,
)
from ix.core.quantitative.statistics import Cycle  # noqa: F401


def MultiSeries(series: dict[str, pd.Series] | None = None, **kwargs: pd.Series) -> pd.DataFrame:
    if series is None:
        series = kwargs
    elif kwargs:
        series = {**series, **kwargs}
    out = []
    for name, s in series.items():
        out.append(s.rename(name))

    data = pd.concat(out, axis=1)
    data.index = pd.to_datetime(data.index)
    data = data.sort_index()
    data.index.name = "Date"
    return data


def _fx_pair_series(base: str, quote: str) -> pd.Series:
    """Fetch FX rate series base/quote as PX_LAST, daily and ffilled.
    Tries both 'Curncy' and 'CURNCY' tickers.
    Returns empty series when not found.
    """
    if not base or not quote or base == quote:
        return pd.Series(dtype=float)
    for asset_class in ("Curncy", "CURNCY"):
        fx_code = f"{base}{quote} {asset_class}:PX_LAST"
        fx = Series(fx_code, freq="D", _skip_fx=True)
        if not fx.empty:
            return fx.ffill()
    return pd.Series(dtype=float)


def Series(
    code: str,
    freq: str | None = None,
    name: str | None = None,
    ccy: str | None = None,
    scale: int | None = None,
    session: Optional[SessionType] = None,
    _skip_fx: bool = False,
    strict: bool = False,
) -> pd.Series:
    """
    Return a pandas Series for `code`, resampled to `freq` if provided,
    otherwise to the DB frequency `ts.frequency`. Slice to [ts.start, today()].

    Alias:
      If code contains '=', e.g. 'NAME=REAL_CODE', return REAL_CODE with name 'NAME'.
    """
    try:
        # Alias handling: if code contains '=', treat as NAME=REAL_CODE
        if "=" in code and ":" not in code.split("=", 1)[0]:
            alias_name, real_code = code.split("=", maxsplit=1)
            s = Series(code=real_code, freq=freq, ccy=ccy, scale=scale, session=session, _skip_fx=_skip_fx, strict=strict).sort_index()
            s.name = alias_name.upper()
            return s.copy()

        if ":" not in code:
            code = f"{code}:PX_LAST"
        code = code.upper()

        # Query using SQLAlchemy — extract all needed fields before session closes
        from ix.db.conn import Session

        ts_start = None
        ts_currency = ""
        ts_scale = 1
        s = pd.Series(name=code, dtype=float)

        _LIVE_SOURCES = {"Yahoo", "Fred", "Naver"}

        def _fetch_from_crawler(source: str, source_code: str) -> pd.Series:
            """Fetch data from web crawler with 15-min TTL cache."""
            # Check cache first
            cached = _crawler_cache.get(source_code)
            if cached and (time.time() - cached[0]) < _CRAWLER_CACHE_TTL:
                result = cached[1].copy()
                result.name = code
                return result

            from ix.misc.crawler import get_yahoo_data, get_fred_data, get_naver_data
            ticker, field = source_code.rsplit(":", 1)
            try:
                if source == "Yahoo":
                    df = get_yahoo_data(ticker)
                elif source == "Fred":
                    df = get_fred_data(ticker)
                elif source == "Naver":
                    df = get_naver_data(ticker)
                else:
                    return pd.Series(dtype=float)
                if df.empty or field not in df.columns:
                    return pd.Series(dtype=float)
                result = df[field].dropna()
                result.index = pd.to_datetime(result.index)
                _crawler_cache[source_code] = (time.time(), result.copy())
                result.name = code
                logger.info("Fetched %s from %s crawler", source_code, source)
                return result
            except Exception as exc:
                logger.warning("Crawler fetch failed for %s (%s): %s", source_code, source, exc)
                return pd.Series(dtype=float)

        def _update_db_in_background(ts_id: str, crawled_data: pd.Series) -> None:
            """Update DB with crawled data in a separate session (non-blocking)."""
            try:
                with Session() as db:
                    ts = db.query(Timeseries).filter(Timeseries.id == ts_id).first()
                    if ts:
                        ts.data = crawled_data
                        db.commit()
            except Exception as exc:
                logger.warning("Background DB update failed for %s: %s", ts_id, exc)

        def _extract(ts_obj: Timeseries) -> pd.Series:
            nonlocal ts_start, ts_currency, ts_scale
            ts_start = ts_obj.start
            ts_currency = (ts_obj.currency or "").upper() if hasattr(ts_obj, "currency") else ""
            try:
                ts_scale = int(ts_obj.scale or 1)
            except Exception:
                logger.warning("Invalid scale value %r for %s, defaulting to 1", ts_obj.scale, code)
                ts_scale = 1
            return ts_obj.data.copy()

        def _lookup_ts(db_session):
            """Look up timeseries metadata. For live sources, fetch from crawler."""
            nonlocal ts_start, ts_currency, ts_scale
            ts = db_session.query(Timeseries).filter(Timeseries.code == code).first()
            if not ts:
                return None, pd.Series(dtype=float)
            src = str(ts.source or "")
            if src in _LIVE_SOURCES and ts.source_code:
                # Fetch from crawler, not DB
                ts_currency = (ts.currency or "").upper()
                try:
                    ts_scale = int(ts.scale or 1)
                except Exception:
                    ts_scale = 1
                crawled = _fetch_from_crawler(src, ts.source_code)
                if not crawled.empty:
                    ts_start = crawled.index.min().date()
                    _update_db_in_background(str(ts.id), crawled)
                    return ts, crawled
                # Fallback to DB if crawler fails
            return ts, _extract(ts)

        found = False
        if session:
            ts, s = _lookup_ts(session)
            found = ts is not None
        else:
            from ix.db.conn import custom_chart_session

            ctx_session = custom_chart_session.get()
            if ctx_session:
                ts, s = _lookup_ts(ctx_session)
                found = ts is not None
            else:
                with Session() as session_local:
                    ts, s = _lookup_ts(session_local)
                    found = ts is not None

        if not found:
            return pd.Series(name=code)

        # Ensure DateTimeIndex just in case
        if not isinstance(s.index, pd.DatetimeIndex):
            s.index = pd.to_datetime(s.index, errors="coerce")
            s = s.dropna()

        # Compute slice window: [start, today]
        start_dt = pd.to_datetime(ts_start) if ts_start else s.index.min()
        end_dt = pd.to_datetime(today())

        # Choose target frequency: override > DB value
        if freq:
            try:
                # Forward-fill daily series first to ensure target frequency dates get values
                # This ensures month-end dates (e.g., 2025-10-31) get the value from the last
                # available day in the month (e.g., 2025-10-30)
                s = s.resample("D").last().ffill()
                idx = pd.date_range(start_dt, end_dt, freq=freq)
                # Resample to target frequency using last observation in each bin
                s = s.reindex(idx)
            except Exception as exc:
                # If target_freq is invalid, fall back to unsampled series
                logger.warning("Resample to freq=%r failed for %s: %s", freq, code, exc)

        # Slice to [start, today] regardless of resampling for consistency
        s = s.loc[start_dt:end_dt]

        # Currency conversion to requested `ccy`
        src_ccy = ts_currency
        tgt_ccy = (ccy or "").upper()

        if not _skip_fx and tgt_ccy and src_ccy and src_ccy != tgt_ccy:
            # Try direct pair
            fx = _fx_pair_series(src_ccy, tgt_ccy)
            if not fx.empty:
                fx = fx.reindex(s.index).ffill()
                s = s.mul(fx).dropna()
            else:
                # Try reverse pair
                fx_rev = _fx_pair_series(tgt_ccy, src_ccy)
                if not fx_rev.empty:
                    fx_rev = fx_rev.reindex(s.index).ffill()
                    s = s.div(fx_rev).dropna()
                else:
                    # Fallback via USD cross (src -> USD -> tgt)
                    pivot = "USD"
                    tmp = s
                    if src_ccy != pivot:
                        fx1 = _fx_pair_series(src_ccy, pivot)
                        if fx1.empty:
                            fx1 = _fx_pair_series(pivot, src_ccy)
                            if not fx1.empty:
                                fx1 = fx1.reindex(tmp.index).ffill()
                                tmp = tmp.div(fx1)
                        else:
                            fx1 = fx1.reindex(tmp.index).ffill()
                            tmp = tmp.mul(fx1)
                    if tgt_ccy != pivot:
                        fx2 = _fx_pair_series(pivot, tgt_ccy)
                        if fx2.empty:
                            fx2 = _fx_pair_series(tgt_ccy, pivot)
                            if not fx2.empty:
                                fx2 = fx2.reindex(tmp.index).ffill()
                                tmp = tmp.div(fx2)
                        else:
                            fx2 = fx2.reindex(tmp.index).ffill()
                            tmp = tmp.mul(fx2)
                    s = tmp.dropna()

        # Apply scale conversion if requested:
        # Convert stored series by its intrinsic ts_scale to target `scale`.
        if scale is not None:
            try:
                target_scale = int(scale) if scale else None
            except Exception:
                logger.warning("Invalid target scale %r for %s, skipping scale conversion", scale, code)
                target_scale = None
            if target_scale and target_scale != 0:
                s = s.mul(ts_scale).div(target_scale)

        # Override name if provided
        if name:
            s.name = name

        return s.copy()
    except Exception as e:
        logger.exception("Error loading series %s: %s", code, e)
        if strict or session is not None:
            raise
        return pd.Series(name=code, dtype=float)


