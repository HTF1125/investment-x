"""Wartime market analysis API — public endpoint, no auth required.

Analyses S&P 500, Gold, and WTI crude performance across historical
geopolitical conflicts, with a focus on the current Iran Attack (2026-02-28).
Data is TTL-cached for 5 minutes to avoid repeated DB round-trips.
"""

import threading
from typing import Any

import numpy as np
import pandas as pd
from cachetools import TTLCache
from fastapi import APIRouter

from ix import Series

router = APIRouter()

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
CONFLICTS: dict[str, tuple[str, str | None]] = {
    "Gulf War (1990)":                    ("1990-08-02", None),
    "Kosovo/NATO Airstrikes (1999)":      ("1999-03-24", None),
    "9/11 / Afghanistan (2001)":          ("2001-09-11", None),
    "Iraq War Invasion (2003)":           ("2003-03-20", None),
    "Libya/Arab Spring (2011)":           ("2011-02-15", None),
    "ISIS/Iraq Crisis (2014)":            ("2014-06-04", None),
    "US-Syria Airstrikes (2017)":         ("2017-04-07", None),
    "Soleimani/Iran Strike (2020)*":      ("2020-01-03", "⚠️ COVID-19 pandemic overlap"),
    "Russia-Ukraine Invasion (2022)":     ("2022-02-24", None),
    "Israel-Hamas War (2023)":            ("2023-10-07", None),
    "Iran Attack — Current (2026-02-28)": ("2026-02-28", "🔴 Live: limited data"),
}

CURRENT_NAME = "Iran Attack — Current (2026-02-28)"

SPX_TICKER   = "SPX INDEX:PX_LAST"
GOLD_TICKER  = "GC1 COMDTY:PX_LAST"
OIL_TICKER   = "WTI COMDTY:PX_LAST"
KRW_TICKER   = "USDKRW Curncy:PX_LAST"
KOSPI_TICKER = "KOSPI INDEX:PX_LAST"
WINDOW      = 200
HORIZONS    = (5, 20, 60, 120, 199)
MIN_ANALOG_DAYS = 10

_cache: TTLCache = TTLCache(maxsize=1, ttl=300)
_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Data loading (TTL-cached)
# ---------------------------------------------------------------------------
def _load_prices() -> tuple[pd.Series, pd.Series, pd.Series, pd.Series, pd.Series]:
    with _lock:
        if "data" in _cache:
            return _cache["data"]
        spx   = Series(SPX_TICKER)
        gold  = Series(GOLD_TICKER)
        oil   = Series(OIL_TICKER)
        krw   = Series(KRW_TICKER)
        kospi = Series(KOSPI_TICKER)
        result = (spx, gold, oil, krw, kospi)
        _cache["data"] = result
        return result


# ---------------------------------------------------------------------------
# Analysis helpers (ported from war_time.py, minus Streamlit)
# ---------------------------------------------------------------------------
def build_rebased(prices: pd.Series) -> dict[str, pd.Series]:
    result: dict[str, pd.Series] = {}
    for name, (start, _) in CONFLICTS.items():
        subset = prices.loc[start:].dropna().iloc[:WINDOW]
        if len(subset) < 1:
            continue
        rebased = subset / subset.iloc[0]
        result[name] = rebased.reset_index(drop=True)
    return result


def _historical_only(rebased: dict[str, pd.Series]) -> dict[str, pd.Series]:
    return {
        name: series
        for name, series in rebased.items()
        if name != CURRENT_NAME and "2020" not in name
    }


def compute_spx_stats(rebased: dict[str, pd.Series]) -> list[dict]:
    rows = []
    for name, s in rebased.items():
        start_date, note = CONFLICTS[name]
        peak     = s.cummax()
        drawdown = (s - peak) / peak
        mdd      = float(drawdown.min())
        days_to_bottom = int(drawdown.idxmin())

        after_bottom = s.iloc[days_to_bottom:]
        recovered    = after_bottom[after_bottom >= 1.0]
        recovery_days = (
            int(recovered.index[0]) - days_to_bottom
            if len(recovered) > 0 else None
        )
        rows.append({
            "conflict":       name,
            "start_date":     start_date,
            "mdd":            round(mdd, 4),
            "days_to_bottom": days_to_bottom,
            "recovery_days":  recovery_days,
            "final_return":   round(float(s.iloc[-1]) - 1.0, 4),
            "days_avail":     len(s),
            "note":           note,
        })
    return rows


def compute_commodity_stats(rebased: dict[str, pd.Series]) -> list[dict]:
    rows = []
    for name, s in rebased.items():
        start_date, note = CONFLICTS[name]
        peak_gain    = float(s.max()) - 1.0
        days_to_peak = int(s.idxmax())
        cum_peak     = s.cummax()
        drawdown     = (s - cum_peak) / cum_peak
        mdd          = float(drawdown.min())
        rows.append({
            "conflict":     name,
            "start_date":   start_date,
            "peak_gain":    round(peak_gain, 4),
            "days_to_peak": days_to_peak,
            "mdd":          round(mdd, 4),
            "final_return": round(float(s.iloc[-1]) - 1.0, 4),
            "days_avail":   len(s),
            "note":         note,
        })
    return rows


def compute_horizon_stats(rebased: dict[str, pd.Series]) -> list[dict]:
    rows = []
    historical = _historical_only(rebased)

    for horizon in HORIZONS:
        values = [
            float(series.iloc[horizon]) - 1.0
            for series in historical.values()
            if len(series) > horizon
        ]
        if not values:
            rows.append({
                "day": horizon + 1,
                "count": 0,
                "mean": None,
                "median": None,
                "std": None,
                "positive_rate": None,
                "p25": None,
                "p75": None,
            })
            continue

        arr = np.array(values, dtype=float)
        rows.append({
            "day": horizon + 1,
            "count": len(values),
            "mean": round(float(np.mean(arr)), 4),
            "median": round(float(np.median(arr)), 4),
            "std": round(float(np.std(arr, ddof=0)), 4),
            "positive_rate": round(float(np.mean(arr > 0)), 4),
            "p25": round(float(np.percentile(arr, 25)), 4),
            "p75": round(float(np.percentile(arr, 75)), 4),
        })
    return rows


def compute_distribution_bands(rebased: dict[str, pd.Series]) -> list[dict]:
    rows = []
    historical = _historical_only(rebased)

    for day in range(WINDOW):
        values = [
            float(series.iloc[day]) - 1.0
            for series in historical.values()
            if len(series) > day
        ]
        if not values:
            rows.append(
                {
                    "day": day,
                    "count": 0,
                    "median": None,
                    "mean": None,
                    "p10": None,
                    "p25": None,
                    "p75": None,
                    "p90": None,
                }
            )
            continue

        arr = np.array(values, dtype=float)
        rows.append(
            {
                "day": day,
                "count": len(values),
                "median": round(float(np.median(arr)), 4),
                "mean": round(float(np.mean(arr)), 4),
                "p10": round(float(np.percentile(arr, 10)), 4),
                "p25": round(float(np.percentile(arr, 25)), 4),
                "p75": round(float(np.percentile(arr, 75)), 4),
                "p90": round(float(np.percentile(arr, 90)), 4),
            }
        )
    return rows


def _midrank_percentile(arr: np.ndarray, current_value: float) -> float:
    close_mask = np.isclose(arr, current_value, rtol=1e-9, atol=1e-9)
    less = int(np.sum(arr < current_value))
    equal = int(np.sum(close_mask))
    return (less + 0.5 * equal) / len(arr)


def compute_current_vs_history(current_series: pd.Series | None, rebased: dict[str, pd.Series]) -> dict[str, Any]:
    historical = _historical_only(rebased)
    if current_series is None or len(current_series) == 0:
        return {
            "day": None,
            "current_return": None,
            "hist_mean": None,
            "hist_median": None,
            "hist_std": None,
            "hist_p10": None,
            "hist_p25": None,
            "hist_p75": None,
            "hist_p90": None,
            "percentile_rank": None,
            "sample_size": 0,
        }

    day = len(current_series) - 1
    values = [
        float(series.iloc[day]) - 1.0
        for series in historical.values()
        if len(series) > day
    ]
    current_return = float(current_series.iloc[-1]) - 1.0

    if not values:
        return {
            "day": day,
            "current_return": round(current_return, 4),
            "hist_mean": None,
            "hist_median": None,
            "hist_std": None,
            "hist_p10": None,
            "hist_p25": None,
            "hist_p75": None,
            "hist_p90": None,
            "percentile_rank": None,
            "sample_size": 0,
        }

    arr = np.array(values, dtype=float)
    return {
        "day": day,
        "current_return": round(current_return, 4),
        "hist_mean": round(float(np.mean(arr)), 4),
        "hist_median": round(float(np.median(arr)), 4),
        "hist_std": round(float(np.std(arr, ddof=0)), 4),
        "hist_p10": round(float(np.percentile(arr, 10)), 4),
        "hist_p25": round(float(np.percentile(arr, 25)), 4),
        "hist_p75": round(float(np.percentile(arr, 75)), 4),
        "hist_p90": round(float(np.percentile(arr, 90)), 4),
        "percentile_rank": round(float(_midrank_percentile(arr, current_return)), 4),
        "sample_size": len(values),
    }


def compute_path_analogues(rebased: dict[str, pd.Series]) -> dict[str, Any]:
    current = rebased.get(CURRENT_NAME)
    if current is None:
        return {"days_used": 0, "available": False, "min_days_required": MIN_ANALOG_DAYS, "rows": []}

    days_used = len(current) - 1
    if days_used + 1 < MIN_ANALOG_DAYS:
        return {
            "days_used": max(days_used, 0),
            "available": False,
            "min_days_required": MIN_ANALOG_DAYS,
            "rows": [],
        }

    historical = _historical_only(rebased)
    current_path = current.iloc[: days_used + 1].astype(float) - 1.0
    rows: list[dict[str, Any]] = []

    for name, series in historical.items():
        if len(series) <= days_used:
            continue
        hist_path = series.iloc[: days_used + 1].astype(float) - 1.0
        diff = hist_path.values - current_path.values
        rmse = float(np.sqrt(np.mean(np.square(diff))))

        corr = None
        if len(hist_path) >= 3 and np.std(hist_path.values) > 0 and np.std(current_path.values) > 0:
            corr = float(np.corrcoef(current_path.values, hist_path.values)[0, 1])

        full_return = float(series.iloc[min(WINDOW - 1, len(series) - 1)]) - 1.0
        running_peak = series.iloc[: days_used + 1].cummax()
        matched_mdd = float(((series.iloc[: days_used + 1] - running_peak) / running_peak).min())
        rows.append(
            {
                "conflict": name,
                "matched_return": round(float(hist_path.iloc[-1]), 4),
                "full_return": round(full_return, 4),
                "path_rmse": round(rmse, 4),
                "path_corr": round(corr, 4) if corr is not None else None,
                "matched_mdd": round(matched_mdd, 4),
            }
        )

    rows.sort(key=lambda row: (row["path_rmse"], -(row["path_corr"] or -1.0)))
    return {
        "days_used": days_used,
        "available": len(rows) > 0,
        "min_days_required": MIN_ANALOG_DAYS,
        "rows": rows[:3],
    }


def _series_to_xy(rebased: dict[str, pd.Series]) -> dict[str, dict]:
    return {
        name: {"x": s.index.tolist(), "y": [round(v, 6) for v in s.tolist()]}
        for name, s in rebased.items()
    }


# ---------------------------------------------------------------------------
# Route — fully public, no Depends(get_current_user)
# ---------------------------------------------------------------------------
@router.get("/wartime/data")
def get_wartime_data() -> dict[str, Any]:
    spx_raw, gold_raw, oil_raw, krw_raw, kospi_raw = _load_prices()

    spx_rebased   = build_rebased(spx_raw)
    gold_rebased  = build_rebased(gold_raw)
    oil_rebased   = build_rebased(oil_raw)
    krw_rebased   = build_rebased(krw_raw)
    kospi_rebased = build_rebased(kospi_raw)

    spx_stats   = compute_spx_stats(spx_rebased)
    gold_stats  = compute_commodity_stats(gold_rebased)
    oil_stats   = compute_commodity_stats(oil_rebased)
    krw_stats   = compute_commodity_stats(krw_rebased)
    kospi_stats = compute_spx_stats(kospi_rebased)
    spx_horizon_stats = compute_horizon_stats(spx_rebased)
    spx_distribution = compute_distribution_bands(spx_rebased)

    # Summary averages (historical conflicts only, excluding current)
    hist = [
        r for r in spx_stats
        if r["conflict"] != CURRENT_NAME and "2020" not in r["conflict"]
    ]
    mdd_vals      = [r["mdd"] for r in hist]
    bottom_vals   = [r["days_to_bottom"] for r in hist]
    recovery_vals = [r["recovery_days"] for r in hist if r["recovery_days"] is not None]
    final_vals    = [r["final_return"] for r in hist]

    summary = {
        "avg_mdd":           round(float(np.mean(mdd_vals)), 4)      if mdd_vals      else None,
        "median_mdd":        round(float(np.median(mdd_vals)), 4)    if mdd_vals      else None,
        "mdd_std":           round(float(np.std(mdd_vals, ddof=0)), 4) if mdd_vals    else None,
        "p25_mdd":           round(float(np.percentile(mdd_vals, 25)), 4) if mdd_vals else None,
        "p75_mdd":           round(float(np.percentile(mdd_vals, 75)), 4) if mdd_vals else None,
        "avg_bottom_days":   round(float(np.mean(bottom_vals)), 1)   if bottom_vals   else None,
        "avg_recovery_days": round(float(np.mean(recovery_vals)), 1) if recovery_vals else None,
        "recovery_rate":     round(len(recovery_vals) / len(hist), 4) if hist         else None,
        "median_final_return": round(float(np.median(final_vals)), 4) if final_vals else None,
        "p25_final_return":    round(float(np.percentile(final_vals, 25)), 4) if final_vals else None,
        "p75_final_return":    round(float(np.percentile(final_vals, 75)), 4) if final_vals else None,
        "sample_size":       len(hist),
    }

    # Current conflict live metrics
    cs  = spx_rebased.get(CURRENT_NAME)
    gc  = gold_rebased.get(CURRENT_NAME)
    oc  = oil_rebased.get(CURRENT_NAME)
    kc  = krw_rebased.get(CURRENT_NAME)
    koc = kospi_rebased.get(CURRENT_NAME)
    current = {
        "name":             CURRENT_NAME,
        "spx_days_elapsed": max(len(cs) - 1, 0) if cs is not None else 0,
        "spx_return":       round(float(cs.iloc[-1]) - 1.0, 4)   if cs  is not None else None,
        "spx_low":          round(float(cs.min())    - 1.0, 4)   if cs  is not None else None,
        "gold_return":      round(float(gc.iloc[-1]) - 1.0, 4)   if gc  is not None else None,
        "oil_return":       round(float(oc.iloc[-1]) - 1.0, 4)   if oc  is not None else None,
        "krw_return":       round(float(kc.iloc[-1]) - 1.0, 4)   if kc  is not None else None,
        "kospi_return":     round(float(koc.iloc[-1]) - 1.0, 4)  if koc is not None else None,
    }

    current_compare = {
        "spx": compute_current_vs_history(cs, spx_rebased),
        "gold": compute_current_vs_history(gc, gold_rebased),
        "oil": compute_current_vs_history(oc, oil_rebased),
        "krw": compute_current_vs_history(kc, krw_rebased),
        "kospi": compute_current_vs_history(koc, kospi_rebased),
    }
    spx_analogues = compute_path_analogues(spx_rebased)

    return {
        "conflicts": {
            name: {"start_date": sd, "note": note}
            for name, (sd, note) in CONFLICTS.items()
        },
        "spx":  {
            "rebased": _series_to_xy(spx_rebased),
            "stats": spx_stats,
            "horizon_stats": spx_horizon_stats,
            "distribution": spx_distribution,
            "analogues": spx_analogues,
        },
        "gold":  {"rebased": _series_to_xy(gold_rebased),  "stats": gold_stats},
        "oil":   {"rebased": _series_to_xy(oil_rebased),   "stats": oil_stats},
        "krw":   {"rebased": _series_to_xy(krw_rebased),   "stats": krw_stats},
        "kospi": {"rebased": _series_to_xy(kospi_rebased), "stats": kospi_stats},
        "current": current,
        "current_compare": current_compare,
        "summary": summary,
    }
