"""Rolling Information Coefficient (IC) computation for adaptive indicator weighting.

Computes Spearman rank correlation between each indicator's z-score and
forward equity returns over a rolling window. Used to dynamically reweight
composites instead of relying on fixed IC weights.

Key design decisions:
  - 104-week (2-year) rolling window: long enough for stability, short enough
    to adapt to structural breaks (e.g., QE regime vs QT regime).
  - Minimum 52 overlapping observations required for a valid IC estimate.
  - IC values are EMA-smoothed (halflife=13 weeks) to prevent week-to-week
    noise from whipping the composite weights.
  - Weights are proportional to |IC| with sign preservation. Indicators with
    |IC| < min_ic_threshold are excluded from the composite to avoid noise.
"""

import numpy as np
import pandas as pd
from scipy.stats import spearmanr


def compute_rolling_ic(
    indicator_z: pd.Series,
    target_px: pd.Series,
    fwd_weeks: int = 13,
    rolling_window: int = 104,
    min_obs: int = 52,
) -> pd.Series:
    """Compute rolling Spearman IC between an indicator z-score and forward returns.

    Args:
        indicator_z: Normalized indicator z-score (weekly).
        target_px: Target index price series (weekly).
        fwd_weeks: Forward return horizon (default 13 weeks = 1 quarter).
        rolling_window: Lookback window for IC computation.
        min_obs: Minimum observations required for a valid IC.

    Returns:
        Series of rolling IC values indexed by date.
    """
    if indicator_z.empty or target_px.empty:
        return pd.Series(dtype=float, name="ic")

    # Forward log returns
    fwd_ret = np.log(target_px).diff(fwd_weeks).shift(-fwd_weeks)

    df = pd.DataFrame({"z": indicator_z, "fwd": fwd_ret}).dropna()
    if len(df) < min_obs:
        return pd.Series(dtype=float, name="ic")

    ic_values = []
    ic_dates = []

    for i in range(rolling_window, len(df)):
        window = df.iloc[i - rolling_window : i]
        valid = window.dropna()
        if len(valid) < min_obs:
            continue
        corr, _ = spearmanr(valid["z"], valid["fwd"])
        if not np.isnan(corr):
            ic_values.append(corr)
            ic_dates.append(df.index[i])

    if not ic_values:
        return pd.Series(dtype=float, name="ic")

    ic = pd.Series(ic_values, index=pd.DatetimeIndex(ic_dates), name="ic")
    return ic


def compute_adaptive_weights(
    normalized_indicators: dict,
    target_px: pd.Series,
    fwd_weeks: int = 13,
    rolling_window: int = 104,
    min_obs: int = 52,
    ic_ema_halflife: int = 13,
    min_ic_threshold: float = 0.03,
) -> tuple[dict, pd.DataFrame]:
    """Compute adaptive IC-based weights for all indicators in an axis.

    Returns time-varying weights that adapt to each indicator's recent
    predictive power instead of using fixed weights.

    Args:
        normalized_indicators: Dict of {name: z-scored pd.Series}.
        target_px: Target index price series.
        fwd_weeks: Forward return horizon.
        rolling_window: IC rolling window.
        min_obs: Minimum observations for IC.
        ic_ema_halflife: EMA smoothing for IC series.
        min_ic_threshold: Minimum |IC| to include in composite.

    Returns:
        Tuple of (current_weights_dict, ic_history_df).
        - current_weights: {name: float} weights for the most recent date
        - ic_history: DataFrame of all indicator IC histories
    """
    ic_series = {}

    for name, z in normalized_indicators.items():
        if z.empty or len(z.dropna()) < min_obs:
            continue
        ic = compute_rolling_ic(z, target_px, fwd_weeks, rolling_window, min_obs)
        if not ic.empty:
            # EMA smooth to reduce noise
            ic_smooth = ic.ewm(halflife=ic_ema_halflife, min_periods=4).mean()
            ic_series[name] = ic_smooth

    if not ic_series:
        return {}, pd.DataFrame()

    ic_df = pd.concat(ic_series, axis=1).sort_index()

    # Current weights: proportional to smoothed |IC|, preserving sign
    latest = ic_df.iloc[-1].dropna()
    if latest.empty:
        return {}, ic_df

    # Filter by threshold
    active = latest[latest.abs() >= min_ic_threshold]
    if active.empty:
        return {}, ic_df

    # Normalize: weight = signed IC, normalized so |weights| sum to 1
    total_abs = active.abs().sum()
    if total_abs > 0:
        weights = (active / total_abs).to_dict()
    else:
        weights = {}

    return weights, ic_df


def compute_axis_ic_report(
    normalized_indicators: dict,
    target_px: pd.Series,
    axis_name: str,
    fwd_weeks: int = 13,
    rolling_window: int = 104,
) -> pd.DataFrame:
    """Generate an IC report for all indicators in an axis.

    Returns a DataFrame with columns: name, current_ic, mean_ic, std_ic,
    pct_positive, weight (for ranking and analysis).
    """
    rows = []
    for name, z in normalized_indicators.items():
        if z.empty or len(z.dropna()) < 52:
            continue
        ic = compute_rolling_ic(z, target_px, fwd_weeks, rolling_window)
        if ic.empty:
            continue
        ic_smooth = ic.ewm(halflife=13, min_periods=4).mean()
        rows.append({
            "axis": axis_name,
            "name": name,
            "current_ic": float(ic_smooth.iloc[-1]) if not ic_smooth.empty else 0,
            "mean_ic": float(ic.mean()),
            "std_ic": float(ic.std()),
            "pct_positive": float((ic > 0).mean() * 100),
            "n_obs": len(ic),
        })

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).sort_values("current_ic", key=abs, ascending=False)
    return df.reset_index(drop=True)
