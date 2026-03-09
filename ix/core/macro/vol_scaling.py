"""Volatility scaling overlay for the macro allocation strategy.

Scales allocation tilts inversely to realized volatility, so the strategy
takes smaller positions when markets are turbulent and larger positions
when markets are calm. This is a standard risk parity / vol-targeting
technique used by most institutional macro funds.

Key design decisions:
  - Target vol is set to the long-run average (full-sample median vol)
    rather than a fixed number, so it adapts to each target index.
  - Scaling is applied multiplicatively to the *tilt* (deviation from
    base weight), not the absolute allocation. This preserves the
    [10%, 90%] allocation bounds.
  - A floor of 0.5x and cap of 1.5x prevents extreme scaling that
    could override the regime signal.
  - Uses 26-week (6-month) realized vol, not shorter windows, because
    the allocation signal is also medium-term (13-week forward).
"""

import numpy as np
import pandas as pd


def compute_realized_vol(
    target_px: pd.Series,
    window: int = 26,
) -> pd.Series:
    """Compute annualized realized volatility from weekly log returns.

    Args:
        target_px: Weekly target index price series.
        window: Rolling window in weeks (default 26 = 6 months).

    Returns:
        Annualized realized volatility series.
    """
    if target_px.empty or len(target_px) < window + 1:
        return pd.Series(dtype=float, name="realized_vol")

    log_ret = np.log(target_px).diff().dropna()
    rvol = log_ret.rolling(window, min_periods=max(window // 2, 13)).std() * np.sqrt(52)
    rvol.name = "realized_vol"
    return rvol.dropna()


def compute_vol_scalar(
    realized_vol: pd.Series,
    target_vol: float | None = None,
    floor: float = 0.5,
    cap: float = 1.5,
) -> pd.Series:
    """Compute volatility scaling factor: target_vol / realized_vol.

    When realized vol > target vol, scalar < 1 → reduce tilt.
    When realized vol < target vol, scalar > 1 → increase tilt.

    Args:
        realized_vol: Annualized realized volatility series.
        target_vol: Target volatility level. If None, uses the
            full-sample median as the target (adaptive).
        floor: Minimum scaling factor (default 0.5x).
        cap: Maximum scaling factor (default 1.5x).

    Returns:
        Scaling factor series clipped to [floor, cap].
    """
    if realized_vol.empty:
        return pd.Series(dtype=float, name="vol_scalar")

    if target_vol is None:
        target_vol = float(realized_vol.median())

    if target_vol <= 0:
        return pd.Series(1.0, index=realized_vol.index, name="vol_scalar")

    scalar = target_vol / realized_vol.replace(0, np.nan)
    scalar = scalar.clip(floor, cap).fillna(1.0)
    scalar.name = "vol_scalar"
    return scalar


def apply_vol_scaling(
    allocation: pd.Series,
    target_px: pd.Series,
    base_weight: float = 0.50,
    vol_window: int = 26,
    target_vol: float | None = None,
    floor: float = 0.5,
    cap: float = 1.5,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """Apply volatility scaling to an existing allocation signal.

    Scales the *tilt* (allocation - base_weight) by the vol scalar,
    then re-adds the base weight and clips to [10%, 90%].

    This means:
      - When vol is high: tilts are compressed → allocation moves toward 50%
      - When vol is low: tilts are amplified → allocation moves further from 50%

    Args:
        allocation: Raw allocation signal (0.10 to 0.90).
        target_px: Target index price series (weekly).
        base_weight: Baseline allocation (default 0.50).
        vol_window: Realized vol window in weeks.
        target_vol: Target vol level (None = adaptive median).
        floor: Minimum vol scalar.
        cap: Maximum vol scalar.

    Returns:
        Tuple of (scaled_allocation, realized_vol, vol_scalar).
    """
    if allocation.empty or target_px.empty:
        empty = pd.Series(dtype=float)
        return empty, empty, empty

    rvol = compute_realized_vol(target_px, vol_window)
    scalar = compute_vol_scalar(rvol, target_vol, floor, cap)

    # Align to allocation index
    scalar_aligned = scalar.reindex(allocation.index).ffill().fillna(1.0)

    # Scale the tilt, not the absolute allocation
    tilt = allocation - base_weight
    scaled_tilt = tilt * scalar_aligned
    scaled_alloc = (base_weight + scaled_tilt).clip(0.10, 0.90)
    scaled_alloc.name = "allocation_vol_scaled"

    return scaled_alloc, rvol, scalar_aligned
