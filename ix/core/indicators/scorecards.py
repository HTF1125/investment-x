"""Pre-computed scorecard tables: performance returns + RRG-style metrics."""

from __future__ import annotations

import logging
import time
from typing import Any

import numpy as np
import pandas as pd

from ix.core.transforms import daily_ffill

logger = logging.getLogger(__name__)

# ── Asset Universes ────────────────────────────────────────────────────────

UNIVERSES: dict[str, dict[str, Any]] = {
    "Global Equities": {
        "assets": {
            "S&P 500": "SPX INDEX:PX_LAST",
            "Dow Jones": "INDU INDEX:PX_LAST",
            "NASDAQ": "CCMP INDEX:PX_LAST",
            "Russell 2K": "RTY INDEX:PX_LAST",
            "STOXX 50": "SX5E INDEX:PX_LAST",
            "FTSE 100": "UKX INDEX:PX_LAST",
            "DAX": "DAX INDEX:PX_LAST",
            "CAC 40": "CAC INDEX:PX_LAST",
            "Nikkei 225": "NKY INDEX:PX_LAST",
            # "TOPIX": "TPX INDEX:PX_LAST",
            "KOSPI": "KOSPI INDEX:PX_LAST",
            # "NIFTY 50": "NIFTY INDEX:PX_LAST",
            "Hang Seng": "HSI INDEX:PX_LAST",
            "Shanghai": "SHCOMP INDEX:PX_LAST",
        },
        "benchmark": "ACWI US EQUITY:PX_LAST",
    },
    "US Sectors": {
        "assets": {
            "Technology": "XLK US EQUITY:PX_LAST",
            "Financials": "XLF US EQUITY:PX_LAST",
            "Energy": "XLE US EQUITY:PX_LAST",
            "Discretionary": "XLY US EQUITY:PX_LAST",
            "Healthcare": "XLV US EQUITY:PX_LAST",
            "Industrials": "XLI US EQUITY:PX_LAST",
            "Materials": "XLB US EQUITY:PX_LAST",
            "Comm Svcs": "XLC US EQUITY:PX_LAST",
            "Staples": "XLP US EQUITY:PX_LAST",
            "Real Estate": "XLRE US EQUITY:PX_LAST",
        },
        "benchmark": "SPY US EQUITY:PX_LAST",
    },
    "Korea Sectors": {
        "assets": {
            "전기/전자": "A013:PX_LAST",
            "화학": "A008:PX_LAST",
            "금융": "A021:PX_LAST",
            "기계/장비": "A012:PX_LAST",
            "제조": "A027:PX_LAST",
            "금속": "A011:PX_LAST",
            "건설": "A018:PX_LAST",
            "운송장비": "A015:PX_LAST",
            "IT서비스": "A046:PX_LAST",
            "음식료": "A005:PX_LAST",
            "제약": "A009:PX_LAST",
            "통신": "A020:PX_LAST",
            "보험": "A025:PX_LAST",
        },
        "benchmark": "KOSPI INDEX:PX_LAST",
    },
    "Commodities": {
        "assets": {
            "GSCI": "GSG US EQUITY:PX_LAST",
            "WTI Crude": "WTI COMDTY:PX_LAST",
            "Brent Crude": "BZ COMDTY:PX_LAST",
            "Gold": "GC1 COMDTY:PX_LAST",
            "Silver": "SI1 COMDTY:PX_LAST",
            "Copper": "HG1 COMDTY:PX_LAST",
        },
        "benchmark": "GSG US EQUITY:PX_LAST",
    },
    "FX": {
        "assets": {
            "Dollar (DXY)": "DXY INDEX:PX_LAST",
            "EUR/USD": "EURUSD CURNCY:PX_LAST",
            "GBP/USD": "GBPUSD CURNCY:PX_LAST",
            "USD/JPY": "USDJPY CURNCY:PX_LAST",
            "USD/KRW": "USDKRW CURNCY:PX_LAST",
            "USD/CNY": "USDCNY CURNCY:PX_LAST",
            "USD/CHF": "USDCHF CURNCY:PX_LAST",
            "USD/AUD": "USDAUD CURNCY:PX_LAST",
        },
        "benchmark": "DXY INDEX:PX_LAST",
    },
}

RETURN_PERIODS = [
    ("1D", pd.DateOffset(days=1)),
    ("1W", pd.DateOffset(weeks=1)),
    ("1M", pd.DateOffset(months=1)),
    ("3M", pd.DateOffset(months=3)),
    ("6M", pd.DateOffset(months=6)),
    ("1Y", pd.DateOffset(years=1)),
    ("3Y", pd.DateOffset(years=3)),
]
DYNAMIC_WINDOW = 60
TACTICAL_WINDOW = 14
ZSCORE_LOOKBACK = 252

# ── Simple in-process TTL cache ────────────────────────────────────────────

_cache: dict[str, Any] = {}
_CACHE_TTL = 300  # 5 minutes


def clear_scorecard_cache() -> None:
    """Force-clear scorecard cache. Series cache is bypassed via force_live=True."""
    _cache.clear()


# ── Batch data loader ──────────────────────────────────────────────────────


def _batch_load(codes: list[str], force_live: bool = False) -> dict[str, pd.Series]:
    """Load multiple timeseries in a single DB query.
    Falls back to Series() for missing/empty codes so live sources
    (Yahoo, Fred, Naver) trigger a crawler fetch + DB persist.

    When force_live=True, skip the DB entirely and fetch everything
    through Series() (triggers live crawler for Yahoo/Fred/Naver sources).
    """
    from ix.db.query import Series as QSeries

    upper_codes = [c.upper() for c in codes]
    result: dict[str, pd.Series] = {}

    if not force_live:
        from ix.db.conn import Session
        from ix.db.models import Timeseries, TimeseriesData

        with Session() as session:
            rows = (
                session.query(Timeseries.code, TimeseriesData.data)
                .join(TimeseriesData, TimeseriesData.timeseries_id == Timeseries.id)
                .filter(Timeseries.code.in_(upper_codes))
                .all()
            )

            for code, raw_data in rows:
                if not raw_data:
                    continue
                try:
                    s = pd.Series(raw_data, dtype=float)
                    s.index = pd.to_datetime(s.index, errors="coerce")
                    s = s.dropna().sort_index()
                    s.name = code
                    if len(s) > 100:
                        result[code] = s
                except Exception:
                    logger.debug("Failed to parse %s", code)

    # Use Series() for codes missing from the batch result (or all codes if force_live).
    # This triggers the crawler for live sources and persists to DB.
    missing = [c for c in upper_codes if c not in result]
    if missing:
        for code in missing:
            try:
                s = QSeries(code)
                if not s.empty and len(s) > 100:
                    result[code.upper()] = s
            except Exception:
                logger.debug("Fallback Series() failed for %s", code)

    return result


# ── Helpers ────────────────────────────────────────────────────────────────


def _load_prices_batch(
    assets: dict[str, str], extra_codes: list[str] | None = None,
    force_live: bool = False,
) -> tuple[pd.DataFrame, dict[str, pd.Series]]:
    """Load all prices for a universe in one query. Returns (asset_df, raw_series_map)."""
    all_codes = list(assets.values())
    if extra_codes:
        all_codes.extend(extra_codes)
    raw = _batch_load(all_codes, force_live=force_live)

    data: dict[str, pd.Series] = {}
    for name, code in assets.items():
        uc = code.upper()
        if uc in raw:
            data[name] = raw[uc]

    if not data:
        return pd.DataFrame(), raw
    df = pd.DataFrame(data)
    df = daily_ffill(df)
    return df, raw


def _compute_returns(prices: pd.DataFrame) -> dict[str, dict]:
    if prices.empty:
        return {}
    today = prices.index[-1]
    year_start = pd.Timestamp(year=today.year, month=1, day=1)
    month_start = pd.Timestamp(year=today.year, month=today.month, day=1)
    results: dict[str, dict] = {}
    for name in prices.columns:
        px = prices[name].dropna()
        if px.empty or len(px) < 2:
            continue
        row: dict[str, Any] = {"level": round(float(px.iloc[-1]), 2)}
        last_px = float(px.iloc[-1])
        for label, offset in RETURN_PERIODS:
            try:
                base_px = px.asof(today - offset)
                if pd.notna(base_px) and base_px != 0:
                    row[label] = round((last_px / float(base_px) - 1) * 100, 2)
                else:
                    row[label] = None
            except Exception as exc:
                logger.debug("Return calc failed for %s/%s: %s", name, label, exc)
                row[label] = None
        # MTD / YTD
        for tag, base_date in [("MTD", month_start), ("YTD", year_start)]:
            try:
                base_px = px.asof(base_date)
                if pd.notna(base_px) and base_px != 0:
                    row[tag] = round((last_px / float(base_px) - 1) * 100, 2)
                else:
                    row[tag] = None
            except Exception as exc:
                logger.debug("Return calc failed for %s/%s: %s", name, tag, exc)
                row[tag] = None
        results[name] = row
    return results


def _safe(v: Any) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
        return round(f, 2) if np.isfinite(f) else None
    except (TypeError, ValueError):
        return None


def _quadrant(momentum: float | None, strength: float | None) -> str | None:
    """RRG quadrant: Leading / Weakening / Lagging / Improving."""
    if momentum is None or strength is None:
        return None
    if strength > 0 and momentum > 0:
        return "Leading"
    if strength > 0 and momentum <= 0:
        return "Weakening"
    if strength <= 0 and momentum <= 0:
        return "Lagging"
    return "Improving"


def _compute_rrg(
    prices: pd.DataFrame,
    benchmark_px: pd.Series | None,
    window: int,
    mom_lookback: int = 5,
) -> dict[str, dict[str, Any]]:
    """RS-Ratio (Strength) and RS-Momentum for each asset vs benchmark."""
    if prices.empty:
        return {}

    if benchmark_px is None:
        rebased = prices.div(prices.bfill().iloc[0])
        benchmark_px = rebased.mean(axis=1)

    null_entry: dict[str, Any] = {"momentum": None, "strength": None, "quadrant": None}
    results: dict[str, dict[str, Any]] = {}
    min_required = ZSCORE_LOOKBACK + window + mom_lookback

    for name in prices.columns:
        px = prices[name].dropna()
        bm = benchmark_px.reindex(px.index).ffill().dropna()
        common = px.index.intersection(bm.index)

        if len(common) < min_required:
            results[name] = null_entry.copy()
            continue

        px_c = px.loc[common]
        bm_c = bm.loc[common]

        with np.errstate(divide="ignore", invalid="ignore"):
            rs = np.log(px_c / bm_c)

        rs_change = rs.diff(window).dropna()
        if len(rs_change) < ZSCORE_LOOKBACK:
            results[name] = null_entry.copy()
            continue

        rs_mean = rs_change.rolling(ZSCORE_LOOKBACK, min_periods=60).mean()
        rs_std = rs_change.rolling(ZSCORE_LOOKBACK, min_periods=60).std()
        z = (rs_change - rs_mean) / rs_std.replace(0, np.nan)

        if z.empty or z.isna().all():
            results[name] = null_entry.copy()
            continue

        strength = z.iloc[-1]
        momentum = (
            z.iloc[-1] - z.iloc[-1 - mom_lookback]
            if len(z) > mom_lookback
            else None
        )
        m = _safe(momentum)
        s = _safe(strength)
        results[name] = {"momentum": m, "strength": s, "quadrant": _quadrant(m, s)}

    return results


# ── Public API ─────────────────────────────────────────────────────────────


def compute_scorecard(category: str, config: dict, force_live: bool = False) -> dict:
    extra = [config["benchmark"]] if config.get("benchmark") else []
    prices, raw = _load_prices_batch(config["assets"], extra_codes=extra, force_live=force_live)
    if prices.empty:
        return {"name": category, "benchmark": "\u2014", "as_of": None, "assets": []}

    returns = _compute_returns(prices)

    benchmark_px: pd.Series | None = None
    if config.get("benchmark"):
        uc = config["benchmark"].upper()
        if uc in raw:
            benchmark_px = daily_ffill(raw[uc])

    dynamic = _compute_rrg(prices, benchmark_px, DYNAMIC_WINDOW, mom_lookback=10)
    tactical = _compute_rrg(prices, benchmark_px, TACTICAL_WINDOW, mom_lookback=5)

    null_rrg = {"momentum": None, "strength": None}
    assets = []
    for name in prices.columns:
        if name not in returns:
            continue
        ret = returns[name]
        assets.append(
            {
                "name": name,
                "level": ret.get("level"),
                "returns": {
                    k: ret.get(k)
                    for k in ["1D", "1W", "1M", "3M", "6M", "1Y", "3Y", "MTD", "YTD"]
                },
                "dynamic": dynamic.get(name, null_rrg),
                "tactical": tactical.get(name, null_rrg),
            }
        )

    _BM_LABELS = {
        "ACWI US EQUITY:PX_LAST": "MSCI ACWI Index",
        "SPY US EQUITY:PX_LAST": "S&P 500",
        "KOSPI INDEX:PX_LAST": "KOSPI",
        "BCOM-CME:PX_LAST": "Bloomberg Cmdty",
        "DXY INDEX:PX_LAST": "DXY Index",
    }
    bm_code = config.get("benchmark")
    bm_label = _BM_LABELS.get(bm_code, bm_code.split(":")[0].split()[0] if bm_code else "Equal Wt")
    as_of = prices.index[-1].strftime("%Y-%m-%d") if not prices.empty else None
    return {"name": category, "benchmark": bm_label, "as_of": as_of, "assets": assets}


def compute_all_scorecards(force_live: bool = False) -> list[dict]:
    if not force_live:
        now = time.time()
        cached = _cache.get("data")
        if cached and now - _cache.get("ts", 0) < _CACHE_TTL:
            return cached

    # ── Single mega-batch: load ALL codes across all categories in one DB query ──
    all_codes: list[str] = []
    for config in UNIVERSES.values():
        all_codes.extend(config["assets"].values())
        if config.get("benchmark"):
            all_codes.append(config["benchmark"])
    all_codes = list(set(all_codes))  # deduplicate

    t0 = time.time()
    raw_all = _batch_load(all_codes, force_live=force_live)
    logger.info("Mega-batch loaded %d/%d codes in %.1fs", len(raw_all), len(all_codes), time.time() - t0)

    # ── Build each category from the shared raw data (no extra DB calls) ──
    def _build_category(cat: str, config: dict) -> dict:
        data: dict[str, pd.Series] = {}
        for name, code in config["assets"].items():
            uc = code.upper()
            if uc in raw_all:
                data[name] = raw_all[uc]
        if not data:
            return {"name": cat, "benchmark": "\u2014", "as_of": None, "assets": []}

        prices = pd.DataFrame(data)
        prices = daily_ffill(prices)

        returns = _compute_returns(prices)

        benchmark_px: pd.Series | None = None
        if config.get("benchmark"):
            uc = config["benchmark"].upper()
            if uc in raw_all:
                benchmark_px = daily_ffill(raw_all[uc])

        dynamic = _compute_rrg(prices, benchmark_px, DYNAMIC_WINDOW, mom_lookback=10)
        tactical = _compute_rrg(prices, benchmark_px, TACTICAL_WINDOW, mom_lookback=5)

        null_rrg = {"momentum": None, "strength": None}
        assets = []
        for name in prices.columns:
            if name not in returns:
                continue
            ret = returns[name]
            assets.append({
                "name": name,
                "level": ret.get("level"),
                "returns": {k: ret.get(k) for k in ["1D", "1W", "1M", "3M", "6M", "1Y", "3Y", "MTD", "YTD"]},
                "dynamic": dynamic.get(name, null_rrg),
                "tactical": tactical.get(name, null_rrg),
            })

        _BM_LABELS = {
            "ACWI US EQUITY:PX_LAST": "MSCI ACWI Index",
            "SPY US EQUITY:PX_LAST": "S&P 500",
            "KOSPI INDEX:PX_LAST": "KOSPI",
            "BCOM-CME:PX_LAST": "Bloomberg Cmdty",
            "DXY INDEX:PX_LAST": "DXY Index",
            "GSG US EQUITY:PX_LAST": "S&P GSCI",
        }
        bm_code = config.get("benchmark")
        bm_label = _BM_LABELS.get(bm_code, bm_code.split(":")[0].split()[0] if bm_code else "Equal Wt")
        as_of = prices.index[-1].strftime("%Y-%m-%d") if not prices.empty else None
        return {"name": cat, "benchmark": bm_label, "as_of": as_of, "assets": assets}

    # ── Parallel RRG computation per category ──
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results: list[dict] = [{}] * len(UNIVERSES)
    cat_items = list(UNIVERSES.items())

    with ThreadPoolExecutor(max_workers=min(len(cat_items), 5)) as pool:
        future_to_idx = {
            pool.submit(_build_category, cat, config): i
            for i, (cat, config) in enumerate(cat_items)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception:
                logger.exception("Scorecard failed for %s", cat_items[idx][0])

    # Remove any empty slots from failures
    results = [r for r in results if r]

    _cache["data"] = results
    _cache["ts"] = time.time()
    logger.info("All scorecards computed in %.1fs", time.time() - t0)
    return results
