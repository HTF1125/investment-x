"""Historical pattern similarity search on price series.

Matches the *shape* of price movement (z-scored prices) rather than
performance magnitude, so a slow-grind-then-crash in 2008 matches a
slow-grind-then-crash in 2020 even if returns differed dramatically.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _clean_prices(prices: pd.Series) -> pd.Series:
    clean = pd.to_numeric(prices, errors="coerce")
    clean = clean.replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return clean
    return clean.sort_index()


def _zscore(segment: np.ndarray) -> np.ndarray:
    """Z-score normalize: (x - mean) / std.

    Strips both level and scale so only the *shape* remains.
    A segment that rose 5% with a dip in the middle will match one that
    rose 30% with the same dip pattern.
    """
    mean = np.mean(segment)
    std = np.std(segment)
    if std == 0:
        return np.full_like(segment, np.nan)
    return (segment - mean) / std


def _rebase_to_zero(segment: np.ndarray) -> np.ndarray:
    """Cumulative return rebased to 0 for plotting."""
    if segment[0] == 0:
        return np.full_like(segment, np.nan)
    return segment / segment[0] - 1.0


def find_similar_patterns(
    prices: pd.Series,
    query_window: int = 252,
    end_date: str | pd.Timestamp | None = None,
    top_n: int = 5,
    step: int = 21,
    min_gap: int = 126,
    metric: str = "correlation",
    forward_windows: tuple[int, ...] = (21, 63, 126, 252),
) -> dict[str, pd.DataFrame]:
    """Find historical periods whose price *shape* matches the query window.

    The matching is done on z-scored price curves (zero mean, unit std),
    which captures the trajectory/pattern of movement — not the magnitude
    of returns.  A period that drifted up then crashed sharply will match
    another drift-then-crash regardless of whether returns were +5% or +30%.

    Parameters
    ----------
    prices : pd.Series
        Daily price-level series (e.g., S&P 500 close prices).
    query_window : int
        Length of the pattern to match in trading days (default 252 = ~1 year).
    end_date : str or Timestamp or None
        End of the query window. None means the latest observation.
    top_n : int
        Number of best matches to return.
    step : int
        Stride in trading days between candidate windows (~21 = 1 month).
    min_gap : int
        Minimum gap in trading days between any two match end-dates to avoid
        overlapping matches.
    metric : str
        ``"correlation"`` (Pearson on z-scored curves — pure shape) or
        ``"euclidean"`` (Euclidean distance on z-scored curves).
    forward_windows : tuple of int
        Horizons (trading days) for computing forward returns after each match.

    Returns
    -------
    dict with two DataFrames:
        ``"summary"`` — one row per match with dates, return, similarity, and
        forward returns.
        ``"curves"`` — z-score normalized price curves for the current query
        and each match (index = relative day, columns = labels).  All curves
        are on the same scale so shapes overlay directly.
    """
    clean = _clean_prices(prices)
    if len(clean) < 2 * query_window:
        raise ValueError(
            f"Need at least {2 * query_window} observations, got {len(clean)}."
        )

    # --- locate query window ---
    if end_date is not None:
        ts = pd.Timestamp(end_date)
        idx_arr = clean.index.get_indexer([ts], method="ffill")
        end_idx = int(idx_arr[0])
        if end_idx < 0:
            raise ValueError(f"end_date {end_date} is before the start of data.")
    else:
        end_idx = len(clean) - 1

    query_start_idx = end_idx - query_window + 1
    if query_start_idx < 0:
        raise ValueError("Not enough data before end_date for query_window.")

    query_vals = clean.values[query_start_idx : end_idx + 1].astype(np.float64)
    query_z = _zscore(query_vals)

    # --- build candidate windows (vectorized) ---
    values = clean.values.astype(np.float64)
    # candidates must end before the exclusion zone around the query
    max_candidate_end = query_start_idx - min_gap
    if max_candidate_end < query_window:
        raise ValueError("Not enough historical data outside the query window.")

    search_region = values[: max_candidate_end + 1]
    all_windows = np.lib.stride_tricks.sliding_window_view(search_region, query_window)
    # subsample by step
    candidate_indices = np.arange(0, len(all_windows), step)
    candidates = all_windows[candidate_indices]  # (n_candidates, query_window)

    # --- z-score normalize all candidates (vectorized) ---
    means = candidates.mean(axis=1, keepdims=True)
    stds = candidates.std(axis=1, keepdims=True)
    valid_mask = stds.ravel() > 0  # skip constant-price windows
    normalized = np.full_like(candidates, np.nan)
    normalized[valid_mask] = (candidates[valid_mask] - means[valid_mask]) / stds[valid_mask]

    # --- compute similarity on z-scored shapes ---
    if metric == "correlation":
        # Pearson on z-scored data = dot product / N  (already zero-mean, unit-var)
        # But we still standardize to unit L2 norm for the dot-product shortcut.
        q = query_z - query_z.mean()
        q_l2 = np.sqrt(np.sum(q**2))
        if q_l2 == 0:
            raise ValueError("Query window has zero variance (constant prices).")
        q_unit = q / q_l2

        c = normalized - np.nanmean(normalized, axis=1, keepdims=True)
        c_l2 = np.sqrt(np.nansum(c**2, axis=1, keepdims=True))
        c_l2[c_l2 == 0] = np.nan
        c_unit = c / c_l2

        scores = c_unit @ q_unit  # Pearson correlation
    elif metric == "euclidean":
        diffs = normalized - query_z[np.newaxis, :]
        distances = np.sqrt(np.nansum(diffs**2, axis=1))
        scores = -distances  # negate so higher = more similar
    else:
        raise ValueError(f"Unknown metric '{metric}'. Use 'correlation' or 'euclidean'.")

    # --- greedy top-N with non-overlap ---
    sorted_order = np.argsort(-scores)
    selected = []
    selected_end_positions: list[int] = []

    for idx in sorted_order:
        if np.isnan(scores[idx]) or not valid_mask[idx]:
            continue
        original_start = int(candidate_indices[idx])
        candidate_end = original_start + query_window - 1
        if any(abs(candidate_end - prev) < min_gap for prev in selected_end_positions):
            continue
        selected.append((idx, original_start))
        selected_end_positions.append(candidate_end)
        if len(selected) >= top_n:
            break

    # --- build summary ---
    rows = []
    for rank, (idx, start_pos) in enumerate(selected, 1):
        end_pos = start_pos + query_window - 1
        total_return = float(values[end_pos] / values[start_pos] - 1.0)
        sim = float(scores[idx])
        if metric == "euclidean":
            sim = -sim  # report as positive distance

        row: dict = {
            "rank": rank,
            "start_date": clean.index[start_pos],
            "end_date": clean.index[end_pos],
            "total_return": total_return,
            "similarity": sim,
        }

        for fw in forward_windows:
            fwd_end = end_pos + fw
            if fwd_end < len(values):
                row[f"fwd_{fw}d"] = float(values[fwd_end] / values[end_pos] - 1.0)
            else:
                row[f"fwd_{fw}d"] = np.nan
        rows.append(row)

    if rows:
        summary = pd.DataFrame(rows).set_index("rank")
    else:
        cols = ["start_date", "end_date", "total_return", "similarity"] + [
            f"fwd_{fw}d" for fw in forward_windows
        ]
        summary = pd.DataFrame(columns=cols)
        summary.index.name = "rank"

    # --- build curves (z-scored for shape overlay) ---
    curves: dict[str, pd.Series] = {}
    curves["Current"] = pd.Series(query_z, index=range(query_window), dtype=float)
    for rank, (idx, start_pos) in enumerate(selected, 1):
        seg = values[start_pos : start_pos + query_window]
        z = _zscore(seg)
        label = f"#{rank} ({clean.index[start_pos].strftime('%Y-%m')})"
        curves[label] = pd.Series(z, index=range(query_window), dtype=float)

    curves_df = pd.DataFrame(curves)
    curves_df.index.name = "relative_day"

    return {"summary": summary, "curves": curves_df}
