"""VOMO Stock Screener — institutional flows + risk-adjusted momentum.

Combines 13F institutional holding data with VOMO (Return/ATR) scoring,
trend confirmation, forward earnings estimates, and market context.
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

# Persistent ticker info cache (sector, market_cap, industry) — survives recomputes
_ticker_info_cache: dict[str, dict[str, Any]] = {}

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


def _normalize_series(values: list[float]) -> list[float]:
    """Normalize a list of floats to 0-1 range."""
    if not values:
        return []
    lo, hi = min(values), max(values)
    span = hi - lo
    if span == 0:
        return [0.5] * len(values)
    return [round((v - lo) / span, 4) for v in values]


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
            from sqlalchemy import func as sqlfunc

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

            # Latest report per fund (for current holdings)
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

            # Previous quarter holdings (for Q-over-Q comparison)
            # Find the two most recent distinct report_dates per fund
            prev_holdings_map: dict[str, dict[str, Any]] = {}  # "fund|symbol" -> holding
            try:
                for fund_row in db.query(InstitutionalHolding.fund_name).distinct().all():
                    fname = fund_row.fund_name
                    # Get 2 most recent distinct report_dates for this fund
                    dates = (
                        db.query(InstitutionalHolding.report_date)
                        .filter(InstitutionalHolding.fund_name == fname)
                        .distinct()
                        .order_by(InstitutionalHolding.report_date.desc())
                        .limit(2)
                        .all()
                    )
                    if len(dates) < 2:
                        continue
                    prev_date = dates[1].report_date
                    prev_rows = (
                        db.query(InstitutionalHolding)
                        .filter(
                            InstitutionalHolding.fund_name == fname,
                            InstitutionalHolding.report_date == prev_date,
                        )
                        .all()
                    )
                    for ph in prev_rows:
                        key = f"{fname}|{ph.symbol or ph.cusip}"
                        prev_holdings_map[key] = {
                            "shares": ph.shares,
                            "value_usd": ph.value_usd,
                        }
            except Exception as e:
                logger.warning(f"Q-over-Q query failed (non-critical): {e}")

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

    # Step 5: Compute VOMO scores + new market data fields
    stocks: list[dict[str, Any]] = []
    for sym in symbols:
        try:
            if is_multi:
                close = data["Close"][sym].dropna()
                high = data["High"][sym].dropna()
                low = data["Low"][sym].dropna()
                volume = data["Volume"][sym].dropna()
            else:
                close = data["Close"].dropna()
                high = data["High"].dropna()
                low = data["Low"].dropna()
                volume = data["Volume"].dropna()

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

            # New: volume metrics
            vol_30d = float(volume.iloc[-30:].mean()) if len(volume) >= 30 else None
            last_vol = float(volume.iloc[-1]) if len(volume) > 0 else None
            rel_vol = round(last_vol / vol_30d, 2) if vol_30d and last_vol and vol_30d > 0 else None

            # New: drawdown from 52-week high
            high_252 = float(close.iloc[-min(252, n):].max())
            drawdown = round((px / high_252 - 1) * 100, 1) if high_252 > 0 else None

            # New: sparkline (last 63 trading days, normalized 0-1)
            spark_raw = close.iloc[-min(63, n):].tolist()
            sparkline = _normalize_series([float(v) for v in spark_raw])

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
                    # New fields
                    "market_cap": None,
                    "sector": None,
                    "avg_volume_30d": round(vol_30d) if vol_30d else None,
                    "relative_volume": rel_vol,
                    "drawdown_52w": drawdown,
                    "rs_percentile": None,  # filled in post-pass
                    "sparkline_3m": sparkline,
                }
            )
        except Exception as e:
            logger.debug(f"Skipping {sym}: {e}")
            continue

    # Step 6: Forward earnings + market cap + sector (rate-limited)
    for stock in stocks[:100]:  # Cap at 100 to avoid excessive API calls
        sym = stock["symbol"]
        try:
            t = yf.Ticker(sym)

            # Forward EPS growth
            ge = t.growth_estimates
            if ge is not None and not ge.empty:
                if "+1y" in ge.index and "stock" in ge.columns:
                    val = ge.loc["+1y", "stock"]
                    if val is not None and not pd.isna(val):
                        stock["fwd_eps_growth"] = round(float(val), 3)

            # Market cap + sector (use persistent cache)
            if sym in _ticker_info_cache:
                cached = _ticker_info_cache[sym]
                stock["market_cap"] = cached.get("market_cap")
                stock["sector"] = cached.get("sector")
            else:
                try:
                    info = t.info
                    mc = info.get("marketCap")
                    sec = info.get("sector")
                    _ticker_info_cache[sym] = {
                        "market_cap": mc,
                        "sector": sec,
                        "industry": info.get("industry"),
                    }
                    stock["market_cap"] = mc
                    stock["sector"] = sec
                except Exception:
                    _ticker_info_cache[sym] = {"market_cap": None, "sector": None, "industry": None}

            time.sleep(0.12)
        except Exception:
            pass

    # Step 6b: Relative strength percentile (post-pass)
    returns_6m = [(i, s.get("return_6m")) for i, s in enumerate(stocks)]
    valid_returns = [(i, r) for i, r in returns_6m if r is not None]
    if valid_returns:
        sorted_returns = sorted(valid_returns, key=lambda x: x[1])
        for rank_idx, (stock_idx, _) in enumerate(sorted_returns):
            pct = round(rank_idx / max(len(sorted_returns) - 1, 1) * 100)
            stocks[stock_idx]["rs_percentile"] = pct

    # Sort by composite VOMO descending
    stocks.sort(key=lambda s: s["vomo_composite"] or -999, reverse=True)
    for i, s in enumerate(stocks):
        s["rank"] = i + 1

    # Build a quick lookup for VOMO by symbol
    vomo_by_sym = {s["symbol"]: s["vomo_composite"] for s in stocks}

    # Step 7: Build flows data (with Q-over-Q comparison)
    flows: list[dict[str, Any]] = []
    for h in all_holdings:
        ticker = symbol_map.get(h.cusip) if h.cusip else h.symbol
        if not ticker or h.put_call:
            continue  # Skip options

        # Q-over-Q comparison
        prev_key = f"{h.fund_name}|{ticker}"
        prev = prev_holdings_map.get(prev_key)
        prev_shares = prev["shares"] if prev else None
        prev_value = prev["value_usd"] if prev else None
        qoq_pct = None
        if prev_shares and h.shares and prev_shares > 0:
            qoq_pct = round((h.shares - prev_shares) / prev_shares * 100, 1)

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
                "vomo_composite": vomo_by_sym.get(ticker),
                # Q-over-Q fields
                "prev_shares": prev_shares,
                "prev_value_usd": prev_value,
                "qoq_shares_change_pct": qoq_pct,
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
        "market_cap", "avg_volume_30d", "relative_volume",
        "drawdown_52w", "rs_percentile",
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


@router.get("/screener/consensus")
@_limiter.limit("20/minute")
def get_consensus(
    request: Request,
    _user=Depends(get_optional_user),
) -> dict[str, Any]:
    """Cross-fund consensus: stocks aggregated by how many funds hold them."""
    data = _get_data()
    flows = data["flows"]
    stocks_by_sym = {s["symbol"]: s for s in data["stocks"]}

    # Aggregate by symbol
    agg: dict[str, dict[str, Any]] = {}
    for f in flows:
        sym = f["symbol"]
        if sym not in agg:
            stock = stocks_by_sym.get(sym, {})
            agg[sym] = {
                "symbol": sym,
                "fund_count": 0,
                "total_value_usd": 0,
                "fund_names": [],
                "actions": {},
                "sector": stock.get("sector"),
                "market_cap": stock.get("market_cap"),
                "vomo_composite": stock.get("vomo_composite"),
                "price": stock.get("price"),
                "drawdown_52w": stock.get("drawdown_52w"),
                "rs_percentile": stock.get("rs_percentile"),
            }
        entry = agg[sym]
        if f["fund_name"] not in entry["fund_names"]:
            entry["fund_names"].append(f["fund_name"])
            entry["fund_count"] += 1
        entry["total_value_usd"] += f["value_usd"] or 0
        action = f["action"]
        entry["actions"][action] = entry["actions"].get(action, 0) + 1

    # Compute consensus label
    for entry in agg.values():
        acts = entry["actions"]
        bullish = acts.get("NEW", 0) + acts.get("INCREASED", 0)
        bearish = acts.get("DECREASED", 0) + acts.get("SOLD", 0)
        total = bullish + bearish
        if total == 0:
            entry["consensus_label"] = "Unchanged"
        elif bullish > bearish:
            entry["consensus_label"] = "Accumulating"
        elif bearish > bullish:
            entry["consensus_label"] = "Reducing"
        else:
            entry["consensus_label"] = "Mixed"

    consensus = sorted(agg.values(), key=lambda x: (x["fund_count"], x["total_value_usd"]), reverse=True)

    return {
        "consensus": consensus,
        "total": len(consensus),
        "computed_at": data["computed_at"],
    }


@router.get("/screener/sector-concentration")
@_limiter.limit("20/minute")
def get_sector_concentration(
    request: Request,
    _user=Depends(get_optional_user),
) -> dict[str, Any]:
    """Sector-level aggregation of institutional positioning."""
    data = _get_data()
    stocks = data["stocks"]
    flows = data["flows"]

    # Build total value by symbol from flows
    sym_value: dict[str, float] = {}
    for f in flows:
        sym_value[f["symbol"]] = sym_value.get(f["symbol"], 0) + (f["value_usd"] or 0)

    # Aggregate by sector
    sectors: dict[str, dict[str, Any]] = {}
    for s in stocks:
        sec = s.get("sector")
        if not sec:
            continue
        if sec not in sectors:
            sectors[sec] = {
                "sector": sec,
                "stock_count": 0,
                "total_value_usd": 0,
                "vomo_sum": 0,
                "fund_count_sum": 0,
                "symbols": [],
            }
        entry = sectors[sec]
        entry["stock_count"] += 1
        entry["total_value_usd"] += sym_value.get(s["symbol"], 0)
        entry["vomo_sum"] += s.get("vomo_composite") or 0
        entry["fund_count_sum"] += s.get("fund_count", 0)
        entry["symbols"].append((s["symbol"], sym_value.get(s["symbol"], 0)))

    result = []
    for entry in sectors.values():
        count = entry["stock_count"]
        # Top 3 symbols by value
        top = sorted(entry["symbols"], key=lambda x: x[1], reverse=True)[:3]
        result.append({
            "sector": entry["sector"],
            "stock_count": count,
            "total_value_usd": round(entry["total_value_usd"]),
            "avg_vomo": round(entry["vomo_sum"] / count, 2) if count else None,
            "avg_fund_count": round(entry["fund_count_sum"] / count, 1) if count else None,
            "top_symbols": [s[0] for s in top],
        })

    result.sort(key=lambda x: x["total_value_usd"], reverse=True)

    return {
        "sectors": result,
        "total": len(result),
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
