from __future__ import annotations

from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session as SessionType

from ix.db.models import Timeseries
from ix.misc.date import today

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


def MultiSeries(**series: pd.Series) -> pd.DataFrame:
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
            s = Series(code=real_code, freq=freq).sort_index()
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

        def _extract(ts_obj: Timeseries) -> pd.Series:
            nonlocal ts_start, ts_currency, ts_scale
            ts_start = ts_obj.start
            ts_currency = (ts_obj.currency or "").upper() if hasattr(ts_obj, "currency") else ""
            try:
                ts_scale = int(ts_obj.scale or 1)
            except Exception:
                ts_scale = 1
            return ts_obj.data.copy()

        found = False
        if session:
            ts = session.query(Timeseries).filter(Timeseries.code == code).first()
            if ts:
                s = _extract(ts)
                found = True
        else:
            from ix.db.conn import custom_chart_session

            ctx_session = custom_chart_session.get()
            if ctx_session:
                ts = ctx_session.query(Timeseries).filter(Timeseries.code == code).first()
                if ts:
                    s = _extract(ts)
                    found = True
            else:
                with Session() as session_local:
                    ts = session_local.query(Timeseries).filter(Timeseries.code == code).first()
                    if ts:
                        s = _extract(ts)
                        found = True

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
            except Exception:
                # If target_freq is invalid, fall back to unsampled series
                pass

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
                target_scale = None
            if target_scale and target_scale != 0:
                s = s.mul(ts_scale).div(target_scale)

        # Override name if provided
        if name:
            s.name = name

        return s.copy()
    except Exception as e:
        import logging

        logger = logging.getLogger(__name__)
        logger.exception(f"Error loading series {code}: {e}")
        if strict or session is not None:
            raise
        return pd.Series(name=code, dtype=float)


