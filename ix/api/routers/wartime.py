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

SPX_TICKER  = "SPX INDEX:PX_LAST"
GOLD_TICKER = "GC1 COMDTY:PX_LAST"
OIL_TICKER  = "WTI COMDTY:PX_LAST"
WINDOW      = 200

_cache: TTLCache = TTLCache(maxsize=1, ttl=300)
_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Data loading (TTL-cached)
# ---------------------------------------------------------------------------
def _load_prices() -> tuple[pd.Series, pd.Series, pd.Series]:
    with _lock:
        if "data" in _cache:
            return _cache["data"]
        spx  = Series(SPX_TICKER)
        gold = Series(GOLD_TICKER)
        oil  = Series(OIL_TICKER)
        result = (spx, gold, oil)
        _cache["data"] = result
        return result


# ---------------------------------------------------------------------------
# Analysis helpers (ported from war_time.py, minus Streamlit)
# ---------------------------------------------------------------------------
def build_rebased(prices: pd.Series) -> dict[str, pd.Series]:
    result: dict[str, pd.Series] = {}
    for name, (start, _) in CONFLICTS.items():
        subset = prices.loc[start:].dropna().iloc[:WINDOW]
        if len(subset) < 2:
            continue
        rebased = subset / subset.iloc[0]
        result[name] = rebased.reset_index(drop=True)
    return result


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
    spx_raw, gold_raw, oil_raw = _load_prices()

    spx_rebased  = build_rebased(spx_raw)
    gold_rebased = build_rebased(gold_raw)
    oil_rebased  = build_rebased(oil_raw)

    spx_stats  = compute_spx_stats(spx_rebased)
    gold_stats = compute_commodity_stats(gold_rebased)
    oil_stats  = compute_commodity_stats(oil_rebased)

    # Summary averages (historical conflicts only, excluding current)
    hist = [r for r in spx_stats if "Current" not in r["conflict"]]
    mdd_vals      = [r["mdd"] for r in hist]
    bottom_vals   = [r["days_to_bottom"] for r in hist]
    recovery_vals = [r["recovery_days"] for r in hist if r["recovery_days"] is not None]

    summary = {
        "avg_mdd":           round(float(np.mean(mdd_vals)), 4)      if mdd_vals      else None,
        "avg_bottom_days":   round(float(np.mean(bottom_vals)), 1)   if bottom_vals   else None,
        "avg_recovery_days": round(float(np.mean(recovery_vals)), 1) if recovery_vals else None,
        "recovery_rate":     round(len(recovery_vals) / len(hist), 4) if hist         else None,
    }

    # Current conflict live metrics
    cs = spx_rebased.get(CURRENT_NAME)
    gc = gold_rebased.get(CURRENT_NAME)
    oc = oil_rebased.get(CURRENT_NAME)
    current = {
        "name":             CURRENT_NAME,
        "spx_days_elapsed": max(len(cs) - 1, 0) if cs is not None else 0,
        "spx_return":       round(float(cs.iloc[-1]) - 1.0, 4)  if cs is not None else None,
        "spx_low":          round(float(cs.min())    - 1.0, 4)  if cs is not None else None,
        "gold_return":      round(float(gc.iloc[-1]) - 1.0, 4)  if gc is not None else None,
        "oil_return":       round(float(oc.iloc[-1]) - 1.0, 4)  if oc is not None else None,
    }

    return {
        "conflicts": {
            name: {"start_date": sd, "note": note}
            for name, (sd, note) in CONFLICTS.items()
        },
        "spx":  {"rebased": _series_to_xy(spx_rebased),  "stats": spx_stats},
        "gold": {"rebased": _series_to_xy(gold_rebased), "stats": gold_stats},
        "oil":  {"rebased": _series_to_xy(oil_rebased),  "stats": oil_stats},
        "current": current,
        "summary": summary,
    }
