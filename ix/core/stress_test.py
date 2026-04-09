"""Stress test engine — auto-compute historical crash & recovery analysis.

Given any target index, finds:
  1. Single-day drops exceeding a threshold (circuit-breaker-level events)
  2. Two-day cumulative drops exceeding a threshold
  3. Forward returns at standard horizons after each event
  4. Recovery curves rebased to T0=100
"""

import numpy as np
import pandas as pd

from ix.db.query import Series
from ix.core.macro.config import TARGET_INDICES
from ix.common import get_logger

logger = get_logger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

CB_HORIZONS = [1, 2, 3, 5, 10, 20, 30, 60, 90]
CB_HORIZON_LABELS = [f"+{h}T" for h in CB_HORIZONS]

CRASH_HORIZONS = [1, 2, 3, 5, 10, 20, 40, 60, 90]
CRASH_HORIZON_LABELS = [f"+{h}T" for h in CRASH_HORIZONS]

RECOVERY_WINDOW = 60  # trading days before & after event

# Thresholds (per-day or cumulative)
SINGLE_DAY_THRESHOLD = -0.03   # -3% single-day drop
TWO_DAY_THRESHOLD = -0.07      # -7% two-day cumulative drop

# Minimum gap between events (trading days) to avoid clustering
MIN_EVENT_GAP = 5


def _forward_returns(
    prices: pd.Series, event_idx: int, horizons: list[int]
) -> dict[str, float | None]:
    """Compute forward returns from an event index."""
    result = {}
    t0_price = prices.iloc[event_idx]
    for h in horizons:
        label = f"+{h}T"
        target_idx = event_idx + h
        if target_idx < len(prices):
            result[label] = round(
                float(prices.iloc[target_idx] / t0_price - 1) * 100, 1
            )
        else:
            result[label] = None
    return result


def _recovery_curve(
    prices: pd.Series, event_idx: int, window: int = RECOVERY_WINDOW
) -> dict:
    """Compute rebased recovery curve around an event."""
    start = max(0, event_idx - window)
    end = min(len(prices), event_idx + window + 1)

    t0_price = prices.iloc[event_idx]
    x_vals = list(range(start - event_idx, end - event_idx))
    y_vals = [round(float(prices.iloc[i] / t0_price) * 100, 2) for i in range(start, end)]

    return {"x": x_vals, "y": y_vals}


def _filter_clustered_events(
    event_indices: list[int], min_gap: int = MIN_EVENT_GAP
) -> list[int]:
    """Keep only events that are at least min_gap apart, keeping the earliest."""
    if not event_indices:
        return []
    filtered = [event_indices[0]]
    for idx in event_indices[1:]:
        if idx - filtered[-1] >= min_gap:
            filtered.append(idx)
    return filtered


def _classify_cause(date: pd.Timestamp) -> str:
    """Heuristic cause label based on date proximity to known macro events."""
    y, m = date.year, date.month

    known = [
        (1997, 11, 1998, 6, "Asian Financial Crisis"),
        (1998, 7, 1999, 2, "EM Contagion / LTCM"),
        (2000, 3, 2000, 5, "Dotcom Bubble"),
        (2000, 9, 2001, 4, "Dotcom Aftershock"),
        (2001, 9, 2001, 10, "9/11 Terror"),
        (2002, 6, 2002, 10, "Corporate Scandals"),
        (2007, 7, 2009, 3, "Global Financial Crisis"),
        (2010, 4, 2010, 7, "European Debt Crisis I"),
        (2011, 7, 2011, 10, "US Downgrade / EU Crisis II"),
        (2015, 6, 2016, 2, "China Slowdown / CNY Deval"),
        (2018, 1, 2018, 3, "Volmageddon"),
        (2018, 10, 2018, 12, "Fed Tightening / Trade War"),
        (2020, 2, 2020, 3, "COVID-19 Pandemic"),
        (2022, 1, 2022, 10, "Fed Rate Hike Cycle"),
        (2024, 7, 2024, 8, "Yen Carry Unwind"),
        (2025, 3, 2025, 5, "Trump Tariff Shock"),
        (2026, 2, 2026, 4, "Iran / Middle East Escalation"),
    ]
    for y1, m1, y2, m2, label in known:
        start = pd.Timestamp(y1, m1, 1)
        end = pd.Timestamp(y2, m2, 28)
        if start <= date <= end:
            return label
    return "Market Stress"


def compute_stress_test(target_name: str) -> dict:
    """Compute full stress test for a target index.

    Returns a dict ready to be serialized as JSON for the frontend.
    """
    if target_name not in TARGET_INDICES:
        raise ValueError(f"Unknown target: {target_name}")

    target = TARGET_INDICES[target_name]
    px = Series(target.ticker)  # daily prices

    if px.empty or len(px) < 100:
        raise ValueError(f"Insufficient price data for {target_name}")

    # Compute daily returns
    daily_ret = px.pct_change().dropna()

    # ── 1. Single-day crash events ──────────────────────────────────────────

    crash_mask = daily_ret <= SINGLE_DAY_THRESHOLD
    crash_indices = sorted(daily_ret.index[crash_mask])

    # Map back to positional indices in px
    px_index_list = px.index.tolist()
    cb_pos_indices = []
    for dt in crash_indices:
        if dt in px.index:
            cb_pos_indices.append(px_index_list.index(dt))

    cb_pos_indices = _filter_clustered_events(cb_pos_indices, min_gap=MIN_EVENT_GAP)

    # Sort by severity (most negative first) and keep top 30
    cb_pos_indices.sort(key=lambda i: px.iloc[i] / px.iloc[i - 1] - 1 if i > 0 else 0)
    cb_pos_indices = cb_pos_indices[:30]
    cb_pos_indices.sort()  # re-sort chronologically

    cb_events = []
    for pos in cb_pos_indices:
        if pos < 1:
            continue
        date = px.index[pos]
        day_ret = float(px.iloc[pos] / px.iloc[pos - 1] - 1) * 100
        fwd = _forward_returns(px, pos, CB_HORIZONS)
        cb_events.append({
            "date": date.strftime("%Y-%m-%d"),
            "cause": _classify_cause(date),
            "causeKo": "",
            "initialReturn": round(day_ret, 2),
            "returns": fwd,
        })

    # Mark the most recent event as current if within last 30 days
    if cb_events:
        last = pd.Timestamp(cb_events[-1]["date"])
        if (pd.Timestamp.now() - last).days <= 30:
            cb_events[-1]["isCurrent"] = True

    # Compute CB averages (excl. current)
    cb_avg = {}
    non_current = [e for e in cb_events if not e.get("isCurrent")]
    for label in CB_HORIZON_LABELS:
        vals = [e["returns"][label] for e in non_current if e["returns"].get(label) is not None]
        cb_avg[label] = round(sum(vals) / len(vals), 1) if vals else 0

    # ── 2. Two-day cumulative crash events ──────────────────────────────────

    two_day_ret = daily_ret + daily_ret.shift(-1)
    crash2_mask = two_day_ret <= TWO_DAY_THRESHOLD
    crash2_indices = sorted(daily_ret.index[crash2_mask])

    crash2_pos_indices = []
    for dt in crash2_indices:
        if dt in px.index:
            pos = px_index_list.index(dt)
            if pos > 0:
                crash2_pos_indices.append(pos)

    crash2_pos_indices = _filter_clustered_events(crash2_pos_indices, min_gap=MIN_EVENT_GAP)

    # Sort by severity and keep top 30
    crash2_pos_indices.sort(
        key=lambda i: (px.iloc[min(i + 1, len(px) - 1)] / px.iloc[i - 1] - 1)
        if i > 0 else 0
    )
    crash2_pos_indices = crash2_pos_indices[:30]
    crash2_pos_indices.sort()

    crash_events = []
    for pos in crash2_pos_indices:
        if pos < 1 or pos + 1 >= len(px):
            continue
        date = px.index[pos]
        # Two-day return: from close before day1 to close of day2
        two_d = float(px.iloc[pos + 1] / px.iloc[pos - 1] - 1) * 100
        # Forward returns from end of day2
        fwd = _forward_returns(px, pos + 1, CRASH_HORIZONS)

        ev = {
            "date": date.strftime("%Y-%m-%d"),
            "cause": _classify_cause(date),
            "causeKo": "",
            "initialReturn": round(two_d, 2),
            "returns": fwd,
        }

        # Highlight GFC events
        if 2007 <= date.year <= 2009:
            ev["highlight"] = "warn"

        crash_events.append(ev)

    # Mark most recent as current
    if crash_events:
        last = pd.Timestamp(crash_events[-1]["date"])
        if (pd.Timestamp.now() - last).days <= 30:
            crash_events[-1]["isCurrent"] = True

    # Crash averages
    crash_avg = {}
    non_current_crash = [e for e in crash_events if not e.get("isCurrent")]
    for label in CRASH_HORIZON_LABELS:
        vals = [e["returns"][label] for e in non_current_crash if e["returns"].get(label) is not None]
        crash_avg[label] = round(sum(vals) / len(vals), 1) if vals else 0

    # ── 3. Recovery curves (for single-day events) ──────────────────────────

    recovery_curves = {}
    for ev in cb_events:
        dt = pd.Timestamp(ev["date"])
        if dt in px.index:
            pos = px_index_list.index(dt)
            recovery_curves[ev["date"]] = _recovery_curve(px, pos)

    # ── 4. Auto-generate insights ───────────────────────────────────────────

    positive_t1 = sum(
        1 for e in cb_events
        if not e.get("isCurrent") and (e["returns"].get("+1T") or 0) > 0
    )
    total_non_current = len(non_current)

    insights_positive = []
    insights_caution = []

    if total_non_current > 0:
        bounce_rate = positive_t1 / total_non_current * 100
        insights_positive.append(
            f"{positive_t1}/{total_non_current} ({bounce_rate:.0f}%) of crash events "
            f"saw a positive next-day bounce"
        )

    avg_t60 = cb_avg.get("+60T", 0)
    if avg_t60 > 0:
        insights_positive.append(
            f"Average +60T forward return: {avg_t60:+.1f}% after single-day crashes"
        )

    avg_t90_crash = crash_avg.get("+90T", 0)
    if avg_t90_crash != 0:
        insights_positive.append(
            f"Average +90T forward return: {avg_t90_crash:+.1f}% after 2-day crashes"
        )

    # Check for current event
    current_cb = [e for e in cb_events if e.get("isCurrent")]
    if current_cb:
        ev = current_cb[0]
        t1 = ev["returns"].get("+1T")
        if t1 is not None and t1 > 0:
            insights_positive.append(
                f"Latest event ({ev['date']}): {t1:+.1f}% next-day bounce"
            )

    # Caution: check if any GFC-like events had prolonged declines
    gfc_events = [e for e in crash_events if e.get("highlight") == "warn"]
    if gfc_events:
        gfc_neg = sum(
            1 for e in gfc_events
            if (e["returns"].get("+20T") or 0) < 0
        )
        if gfc_neg > 0:
            insights_caution.append(
                f"{gfc_neg} GFC-era events saw negative +20T returns — "
                f"systemic crises can override mean-reversion patterns"
            )

    # Current event drop context
    current_event = None
    if current_cb:
        ev = current_cb[0]
        current_event = {
            "date": ev["date"],
            "drop": ev["initialReturn"],
            "dropLabel": f"Single-day drop on {ev['date']}",
        }
    elif crash_events and crash_events[-1].get("isCurrent"):
        ev = crash_events[-1]
        current_event = {
            "date": ev["date"],
            "drop": ev["initialReturn"],
            "dropLabel": f"2-day cumulative drop from {ev['date']}",
        }

    # Valuation context (generic)
    valuation = [
        f"{target_name} analyzed over {len(px):,} trading days "
        f"({px.index[0].strftime('%Y-%m-%d')} to {px.index[-1].strftime('%Y-%m-%d')})",
        f"{len(cb_events)} single-day crash events detected (threshold: {SINGLE_DAY_THRESHOLD*100:.0f}%)",
        f"{len(crash_events)} two-day crash events detected (threshold: {TWO_DAY_THRESHOLD*100:.0f}%)",
    ]

    return {
        "target_name": target_name,
        "label": target_name,
        "source": "Auto-computed",
        "sourceDate": pd.Timestamp.now().strftime("%Y.%m.%d"),
        "cbHorizons": CB_HORIZON_LABELS,
        "cbEvents": cb_events,
        "cbAvg": cb_avg,
        "crashHorizons": CRASH_HORIZON_LABELS,
        "crashEvents": crash_events,
        "crashAvg": crash_avg,
        "recoveryCurves": recovery_curves,
        "insights": {
            "positive": insights_positive,
            "caution": insights_caution,
        },
        "valuation": valuation,
        "currentEvent": current_event,
    }
