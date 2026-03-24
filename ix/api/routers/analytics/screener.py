"""VOMO Stock Screener — institutional flows + risk-adjusted momentum.

Combines 13F institutional holding data with VOMO (Return/ATR) scoring,
trend confirmation, and forward earnings estimates.
Data is TTL-cached for 6 hours.
"""

import logging
import threading
import time
from typing import Any

import numpy as np
import pandas as pd
import requests
import yfinance as yf
from cachetools import TTLCache
from fastapi import APIRouter, Depends, Query
from starlette.requests import Request

from ix.api.dependencies import get_current_admin_user, get_optional_user
from ix.api.rate_limit import limiter as _limiter
from ix.db.conn import Session
from ix.db.models.institutional_holding import InstitutionalHolding

logger = logging.getLogger(__name__)

router = APIRouter()

_cache: TTLCache = TTLCache(maxsize=1, ttl=21600)  # 6 hours
_lock = threading.Lock()


# ---------------------------------------------------------------------------
# CUSIP-to-Ticker Resolution
# ---------------------------------------------------------------------------

_sec_name_map: dict[str, str] = {}  # UPPER(company_name) -> ticker
_sec_map_loaded = False
_cusip_ticker_cache: dict[str, str | None] = {}

SEC_HEADERS = {
    "User-Agent": "Investment-X Research Platform admin@investment-x.com",
    "Accept-Encoding": "gzip, deflate",
}


def _ensure_sec_name_map() -> None:
    """Load SEC company_tickers.json once and build name->ticker map."""
    global _sec_map_loaded
    if _sec_map_loaded:
        return
    try:
        resp = requests.get(
            "https://www.sec.gov/files/company_tickers.json",
            headers=SEC_HEADERS,
            timeout=15,
        )
        if resp.status_code == 200:
            data = resp.json()
            for entry in data.values():
                title = (entry.get("title") or "").upper().strip()
                ticker = (entry.get("ticker") or "").upper().strip()
                if title and ticker:
                    _sec_name_map[title] = ticker
            logger.info(f"Loaded {len(_sec_name_map)} SEC name->ticker mappings")
    except Exception as e:
        logger.warning(f"Failed to load SEC company_tickers.json: {e}")
    _sec_map_loaded = True


def _resolve_ticker_from_name(security_name: str) -> str | None:
    """Resolve a ticker from a 13F security name using SEC name map + yfinance."""
    if not security_name:
        return None

    name_upper = security_name.upper().strip()

    # 1. Exact match against SEC names
    _ensure_sec_name_map()
    if name_upper in _sec_name_map:
        return _sec_name_map[name_upper]

    # 2. Prefix match — 13F names often have suffixes like "COM", "CL A"
    clean = name_upper.split(" COM")[0].split(" CL ")[0].split(" CLASS ")[0]
    clean = clean.split(" SHS")[0].split(" NEW")[0].strip()
    if clean in _sec_name_map:
        return _sec_name_map[clean]

    # 3. Try partial match — find SEC names that start with our cleaned name
    for sec_name, ticker in _sec_name_map.items():
        if sec_name.startswith(clean) and len(clean) >= 4:
            return ticker

    # 4. Fallback: yfinance search
    try:
        search_result = yf.Search(clean, max_results=3)
        if hasattr(search_result, "quotes") and search_result.quotes:
            for q in search_result.quotes:
                sym = q.get("symbol", "")
                # Skip non-US tickers (no dots or suffixes)
                if sym and "." not in sym and len(sym) <= 5:
                    return sym
    except Exception:
        pass

    return None


def resolve_cusip_to_ticker(cusip: str, security_name: str = "") -> str | None:
    """Resolve a CUSIP to a ticker symbol, with caching."""
    if cusip in _cusip_ticker_cache:
        return _cusip_ticker_cache[cusip]
    ticker = _resolve_ticker_from_name(security_name)
    _cusip_ticker_cache[cusip] = ticker
    return ticker


# ---------------------------------------------------------------------------
# VOMO Computation Helpers
# ---------------------------------------------------------------------------


def _atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range."""
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(period).mean()


def _vomo_score(
    close: pd.Series, high: pd.Series, low: pd.Series, window: int
) -> float | None:
    """VOMO = Return% / Average ATR% over a lookback window."""
    if len(close) < window + 14:
        return None
    ret = (close.iloc[-1] / close.iloc[-window] - 1) * 100
    atr_series = _atr(high, low, close)
    avg_atr_pct = (atr_series / close * 100).iloc[-window:].mean()

    if avg_atr_pct == 0 or pd.isna(avg_atr_pct):
        return None
    return round(float(ret / avg_atr_pct), 2)


def _trend_flags(close: pd.Series) -> tuple[bool, bool]:
    """Check price vs 50d and 200d SMA."""
    if len(close) < 200:
        sma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else np.nan
        px = close.iloc[-1]
        return bool(not pd.isna(sma50) and px > sma50), False

    sma50 = close.rolling(50).mean().iloc[-1]
    sma200 = close.rolling(200).mean().iloc[-1]
    px = close.iloc[-1]
    return bool(px > sma50), bool(px > sma200)


# ---------------------------------------------------------------------------
# Main Computation
# ---------------------------------------------------------------------------


def compute_screener() -> dict[str, Any]:
    """Batch compute VOMO scores for all symbols held by tracked institutions."""
    logger.info("Computing VOMO screener...")
    start = time.time()
    empty_result = {
        "stocks": [],
        "flows": [],
        "total": 0,
        "computed_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "universe_size": 0,
    }

    # Step 1: Query holdings from DB
    try:
        with Session() as db:
            # Distinct CUSIPs with security names
            distinct_cusips = (
                db.query(
                    InstitutionalHolding.cusip,
                    InstitutionalHolding.symbol,
                    InstitutionalHolding.security_name,
                )
                .distinct(InstitutionalHolding.cusip)
                .filter(InstitutionalHolding.cusip.isnot(None))
                .all()
            )

            # All holdings for flow data (latest report per fund)
            from sqlalchemy import func as sqlfunc

            latest_dates = (
                db.query(
                    InstitutionalHolding.fund_name,
                    sqlfunc.max(InstitutionalHolding.report_date).label("max_date"),
                )
                .group_by(InstitutionalHolding.fund_name)
                .subquery()
            )

            all_holdings = (
                db.query(InstitutionalHolding)
                .join(
                    latest_dates,
                    (InstitutionalHolding.fund_name == latest_dates.c.fund_name)
                    & (InstitutionalHolding.report_date == latest_dates.c.max_date),
                )
                .all()
            )
    except Exception as e:
        logger.error(f"DB query failed: {e}")
        return empty_result

    if not distinct_cusips:
        logger.warning("No holdings found in DB")
        return empty_result

    # Step 2: Resolve CUSIPs to tickers
    symbol_map: dict[str, str] = {}  # cusip -> ticker
    for row in distinct_cusips:
        cusip = row.cusip
        if not cusip:
            continue
        if row.symbol:
            symbol_map[cusip] = row.symbol
        else:
            ticker = resolve_cusip_to_ticker(cusip, row.security_name or "")
            if ticker:
                symbol_map[cusip] = ticker
                # Backfill in DB
                try:
                    with Session() as db2:
                        db2.query(InstitutionalHolding).filter(
                            InstitutionalHolding.cusip == cusip,
                            InstitutionalHolding.symbol.is_(None),
                        ).update({InstitutionalHolding.symbol: ticker})
                        db2.commit()
                except Exception as e:
                    logger.debug(f"Backfill failed for {cusip}: {e}")
            time.sleep(0.05)

    symbols = sorted(set(symbol_map.values()))
    if not symbols:
        logger.warning("No tickers resolved from 13F holdings")
        return empty_result

    logger.info(f"Resolved {len(symbols)} unique tickers from {len(distinct_cusips)} CUSIPs")

    # Step 3: Download price data in batch
    try:
        data = yf.download(symbols, period="2y", progress=False, threads=True)
    except Exception as e:
        logger.error(f"yfinance download failed: {e}")
        empty_result["universe_size"] = len(symbols)
        return empty_result

    if data.empty:
        empty_result["universe_size"] = len(symbols)
        return empty_result

    is_multi = isinstance(data.columns, pd.MultiIndex)

    # Step 4: Build fund count per ticker
    ticker_funds: dict[str, set[str]] = {}
    for h in all_holdings:
        ticker = symbol_map.get(h.cusip) if h.cusip else h.symbol
        if ticker:
            ticker_funds.setdefault(ticker, set()).add(h.fund_name)
    ticker_fund_count = {t: len(funds) for t, funds in ticker_funds.items()}

    # Step 5: Compute VOMO scores
    stocks: list[dict[str, Any]] = []
    for sym in symbols:
        try:
            if is_multi:
                close = data["Close"][sym].dropna()
                high = data["High"][sym].dropna()
                low = data["Low"][sym].dropna()
            else:
                close = data["Close"].dropna()
                high = data["High"].dropna()
                low = data["Low"].dropna()

            if len(close) < 50:
                continue

            px = float(close.iloc[-1])

            vomo_1m = _vomo_score(close, high, low, 21)
            vomo_6m = _vomo_score(close, high, low, 126)
            vomo_1y = _vomo_score(close, high, low, 252)

            # Weighted composite
            scores, weights = [], []
            if vomo_1m is not None:
                scores.append(vomo_1m)
                weights.append(0.2)
            if vomo_6m is not None:
                scores.append(vomo_6m)
                weights.append(0.4)
            if vomo_1y is not None:
                scores.append(vomo_1y)
                weights.append(0.4)
            if not scores:
                continue
            w_total = sum(weights)
            composite = round(sum(s * w / w_total for s, w in zip(scores, weights)), 2)

            short_trend, long_trend = _trend_flags(close)

            n = len(close)
            ret_1m = round(float(close.iloc[-1] / close.iloc[-min(21, n)] - 1) * 100, 1) if n >= 21 else None
            ret_6m = round(float(close.iloc[-1] / close.iloc[-min(126, n)] - 1) * 100, 1) if n >= 126 else None
            ret_1y = round(float(close.iloc[-1] / close.iloc[-min(252, n)] - 1) * 100, 1) if n >= 252 else None

            stocks.append(
                {
                    "symbol": sym,
                    "price": round(px, 2),
                    "vomo_1m": vomo_1m,
                    "vomo_6m": vomo_6m,
                    "vomo_1y": vomo_1y,
                    "vomo_composite": composite,
                    "short_trend": short_trend,
                    "long_trend": long_trend,
                    "trend_confirmed": short_trend and long_trend,
                    "fwd_eps_growth": None,
                    "fund_count": ticker_fund_count.get(sym, 0),
                    "return_1m": ret_1m,
                    "return_6m": ret_6m,
                    "return_1y": ret_1y,
                }
            )
        except Exception as e:
            logger.debug(f"Skipping {sym}: {e}")
            continue

    # Step 6: Forward earnings estimates (rate-limited)
    for stock in stocks[:100]:  # Cap at 100 to avoid excessive API calls
        try:
            t = yf.Ticker(stock["symbol"])
            ge = t.growth_estimates
            if ge is not None and not ge.empty:
                # growth_estimates rows: 0q, +1q, 0y, +1y, +5y; cols: stock, industry, sector
                if "+1y" in ge.index and "stock" in ge.columns:
                    val = ge.loc["+1y", "stock"]
                    if val is not None and not pd.isna(val):
                        stock["fwd_eps_growth"] = round(float(val), 3)
            time.sleep(0.12)
        except Exception:
            pass

    # Sort by composite VOMO descending
    stocks.sort(key=lambda s: s["vomo_composite"] or -999, reverse=True)
    for i, s in enumerate(stocks):
        s["rank"] = i + 1

    # Step 7: Build flows data
    flows: list[dict[str, Any]] = []
    for h in all_holdings:
        ticker = symbol_map.get(h.cusip) if h.cusip else h.symbol
        if not ticker or h.put_call:
            continue  # Skip options

        vomo = None
        for s in stocks:
            if s["symbol"] == ticker:
                vomo = s["vomo_composite"]
                break

        flows.append(
            {
                "fund_name": h.fund_name,
                "symbol": ticker,
                "security_name": h.security_name,
                "action": h.action or "UNKNOWN",
                "shares": h.shares,
                "value_usd": h.value_usd,
                "shares_change_pct": (
                    round(float(h.shares_change_pct), 1) if h.shares_change_pct else None
                ),
                "report_date": str(h.report_date) if h.report_date else None,
                "vomo_composite": vomo,
            }
        )

    elapsed = time.time() - start
    logger.info(f"VOMO screener: {len(stocks)} stocks, {len(flows)} flows in {elapsed:.1f}s")

    result = {
        "stocks": stocks,
        "flows": flows,
        "total": len(stocks),
        "computed_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "universe_size": len(symbols),
    }

    with _lock:
        _cache["data"] = result

    return result


def _get_data() -> dict[str, Any]:
    """Get cached screener data, computing on first access."""
    with _lock:
        if "data" in _cache:
            return _cache["data"]
    return compute_screener()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/screener/rankings")
@_limiter.limit("20/minute")
def get_rankings(
    request: Request,
    trend_filter: bool = Query(False, description="Only show trend-confirmed stocks"),
    min_funds: int = Query(0, description="Minimum fund count"),
    sort_by: str = Query("vomo_composite", description="Sort column"),
    _user=Depends(get_optional_user),
) -> dict[str, Any]:
    """VOMO-ranked stock screener with institutional flow data."""
    data = _get_data()
    stocks = list(data["stocks"])  # shallow copy for filtering

    if trend_filter:
        stocks = [s for s in stocks if s["trend_confirmed"]]
    if min_funds > 0:
        stocks = [s for s in stocks if s["fund_count"] >= min_funds]

    valid_sorts = {
        "vomo_composite", "vomo_1m", "vomo_6m", "vomo_1y",
        "fund_count", "price", "fwd_eps_growth",
        "return_1m", "return_6m", "return_1y",
    }
    if sort_by in valid_sorts:
        stocks = sorted(stocks, key=lambda s: s.get(sort_by) or -999, reverse=True)

    for i, s in enumerate(stocks):
        s["rank"] = i + 1

    return {
        "stocks": stocks,
        "total": len(stocks),
        "computed_at": data["computed_at"],
        "universe_size": data["universe_size"],
    }


@router.get("/screener/flows")
@_limiter.limit("20/minute")
def get_flows(
    request: Request,
    action: str | None = Query(None, description="Filter by action"),
    fund: str | None = Query(None, description="Filter by fund name substring"),
    _user=Depends(get_optional_user),
) -> dict[str, Any]:
    """13F institutional flows joined with VOMO scores."""
    data = _get_data()
    flows = list(data["flows"])

    if action:
        flows = [f for f in flows if f["action"] == action.upper()]
    if fund:
        fund_lower = fund.lower()
        flows = [f for f in flows if fund_lower in f["fund_name"].lower()]

    return {
        "flows": flows,
        "total": len(flows),
        "computed_at": data["computed_at"],
    }


@router.post("/screener/refresh")
@_limiter.limit("5/minute")
def refresh_screener(request: Request, _user=Depends(get_current_admin_user)) -> dict[str, str]:
    """Force recompute the screener (admin only)."""
    with _lock:
        _cache.clear()
    compute_screener()
    return {"status": "ok", "message": "Screener recomputed"}
