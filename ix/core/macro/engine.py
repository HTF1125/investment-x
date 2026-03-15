"""Computation engine for the macro outlook model.

All functions are pure numpy/pandas -- no UI, no Plotly, no Streamlit.
They transform raw indicator data into z-scores, composite signals,
regime probabilities, liquidity phases, and allocation weights.
"""

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

from ix.core.macro.config import (
    REGIME_NAMES,
    REGIME_CENTROIDS,
    REGIME_RETURN_ASSUMPTIONS,
    LIQUIDITY_PHASES,
)
from ix.core.macro.rolling_ic import compute_adaptive_weights
from ix.core.macro.vol_scaling import apply_vol_scaling


# ==============================================================================
# TREND SIGNAL
# ==============================================================================


def compute_trend_signal(target_px: pd.Series, sma_weeks: int = 40) -> pd.Series:
    """Binary trend signal: 1.0 if price > SMA, 0.0 otherwise.

    The 40-week (~200-day) SMA is the most widely used trend filter.
    Above SMA = uptrend = risk-on.  Below SMA = downtrend = risk-off.
    """
    px = _coerce_series(target_px, "target_px")
    if px.empty or sma_weeks < 1:
        return pd.Series(dtype=float, name="trend")
    sma = px.rolling(sma_weeks, min_periods=sma_weeks).mean()
    trend = (px > sma).astype(float)
    trend.name = "trend"
    return trend.dropna()


def compute_sma(target_px: pd.Series, sma_weeks: int = 40) -> pd.Series:
    """Simple moving average of target price for visualisation."""
    px = _coerce_series(target_px, "target_px")
    if px.empty or sma_weeks < 1:
        return pd.Series(dtype=float, name="sma_40w")
    sma = px.rolling(sma_weeks, min_periods=sma_weeks).mean()
    sma.name = "sma_40w"
    return sma.dropna()


# ==============================================================================
# BINARY REGIME ALLOCATION
# ==============================================================================


def compute_binary_allocation(
    trend_signal: pd.Series,
    macro_composite: pd.Series,
    risk_on: float = 0.90,
    neutral: float = 0.50,
    risk_off: float = 0.10,
) -> pd.Series:
    """Binary regime switching allocation.

    Research shows real alpha comes from drawdown avoidance via binary
    regime switching, not continuous tilts (~<1% alpha).

    Rules:
      - Both trend AND macro bullish  -> risk_on  (90%)
      - Mixed signals                 -> neutral  (50%)
      - Both bearish                  -> risk_off (10%)
    """
    trend = _coerce_series(trend_signal, "trend")
    macro = _coerce_series(macro_composite, "macro")
    if trend.empty or macro.empty:
        return pd.Series(dtype=float, name="binary_allocation")

    df = pd.DataFrame({"trend": trend, "macro": macro}).dropna()
    if df.empty:
        return pd.Series(dtype=float, name="binary_allocation")

    trend_bull = df["trend"] > 0.5
    macro_bull = df["macro"] > 0

    alloc = pd.Series(neutral, index=df.index, name="binary_allocation")
    alloc[trend_bull & macro_bull] = risk_on
    alloc[~trend_bull & ~macro_bull] = risk_off
    return alloc


# ==============================================================================
# EMPIRICAL REGIME RETURNS
# ==============================================================================


def compute_empirical_regime_returns(
    probs: pd.DataFrame,
    target_px: pd.Series,
    fwd_weeks: int = 13,
) -> dict:
    """Compute empirical annualized returns per dominant regime for a target index.

    Falls back to REGIME_RETURN_ASSUMPTIONS when insufficient data (<26 weeks).
    """
    regimes = dominant_regime(probs)
    px = _coerce_series(target_px, "target_px")
    if regimes.empty or px.empty:
        return dict(REGIME_RETURN_ASSUMPTIONS)

    wr = np.log(px).diff().dropna()
    df = pd.DataFrame({"regime": regimes, "ret": wr}).dropna()

    result = {}
    for r in REGIME_NAMES:
        sub = df[df["regime"] == r]["ret"]
        if len(sub) >= 26:
            result[r] = float(sub.mean() * 52)
        else:
            result[r] = REGIME_RETURN_ASSUMPTIONS.get(r, 0.0)
    return result


# ==============================================================================
# NORMALIZATION
# ==============================================================================


def _coerce_series(raw: pd.Series | pd.DataFrame | None, name: str | None = None) -> pd.Series:
    """Return a clean numeric Series with a sorted DatetimeIndex."""
    if raw is None:
        return pd.Series(dtype=float, name=name)
    if isinstance(raw, pd.DataFrame):
        if raw.shape[1] != 1:
            raise ValueError("Expected a single-column Series-like input.")
        raw = raw.iloc[:, 0]
    series = raw.copy()
    series = pd.to_numeric(series, errors="coerce")
    series = series.replace([np.inf, -np.inf], np.nan).dropna()
    if series.empty:
        return pd.Series(dtype=float, name=name or getattr(raw, "name", None))
    idx = pd.to_datetime(series.index, errors="coerce")
    series = series.loc[~idx.isna()].copy()
    series.index = idx[~idx.isna()]
    series = series.sort_index()
    series.name = name or series.name
    return series


def rolling_zscore(s: pd.Series, window: int = 78) -> pd.Series:
    """Rolling z-score using median and MAD (robust to outliers).

    Uses median absolute deviation instead of standard deviation to be
    resistant to extreme values common in macro data.

    Args:
        s: Input time series.
        window: Lookback window in periods.

    Returns:
        Z-scored series (NaN for insufficient history).
    """
    series = _coerce_series(s, getattr(s, "name", None))
    if series.empty or window < 2:
        return pd.Series(dtype=float, name=getattr(s, "name", None))
    min_p = min(len(series), max(window // 2, min(30, window)))
    median = series.rolling(window, min_periods=min_p).median()
    mad = series.sub(median).abs().rolling(window, min_periods=min_p).median()
    scaled_mad = (mad * 1.4826).replace(0, np.nan)
    z = series.sub(median).div(scaled_mad)
    z = z.replace([np.inf, -np.inf], np.nan).dropna()
    z.name = getattr(s, "name", None)
    return z


def _get_loader_meta(name, loaders):
    """Get (invert, pub_lag_weeks, monthly) for a named indicator.

    Scans the loader list for metadata about a specific indicator.
    """
    for n, _fn, _nf, _nw, inv, lag, monthly in loaders:
        if n == name:
            return inv, lag, monthly
    return False, 0, False


def normalize_indicator(
    raw: pd.Series, name: str, loaders, z_window: int = 78
) -> pd.Series:
    """Normalize a raw indicator to rolling z-score with publication lag and inversion.

    Args:
        raw: Raw indicator values.
        name: Indicator name (must match a loader entry).
        loaders: The loader list to look up metadata from.
        z_window: Base z-score window. Reduced for monthly series.

    Returns:
        Clipped z-score series in [-3, 3].
    """
    s = _coerce_series(raw, name)
    if s.empty:
        return s
    invert, lag, monthly = _get_loader_meta(name, loaders)
    if lag > 0:
        s = s.shift(lag).dropna()
        if s.empty:
            return s
    window = max(z_window // 4, 24) if monthly else z_window
    z = rolling_zscore(s, window=window)
    if invert:
        z = -z
    z = z.clip(-3, 3)
    z.name = name
    return z


def _ffill_limit(name: str, loaders) -> int:
    """Limit stale forward-fills so dead indicators do not pollute composites."""
    _invert, _lag, monthly = _get_loader_meta(name, loaders)
    return 8 if monthly else 3


def build_axis_composite(
    raw_data: dict,
    loaders,
    z_window: int = 78,
    weights: dict | None = None,
    ema_halflife: int = 4,
) -> tuple:
    """Normalize all indicators and combine into a single composite score.

    Each indicator is individually z-scored, then combined via equal
    weighting (default) or IC-based weighting (if weights dict provided),
    then smoothed with an EMA.

    Args:
        raw_data: Dict of {name: raw_series}.
        loaders: The loader definition list.
        z_window: Base z-score window.
        weights: Optional dict of {name: signed_weight}. When provided,
            only indicators in this dict are included, and the composite
            is the weighted mean (weight signs handle direction). Indicators
            not in this dict are still normalized for display but excluded
            from the composite.
        ema_halflife: EMA halflife for composite smoothing.

    Returns:
        Tuple of (normalized_dict, composite_series).
    """
    normalized = {}
    for name, raw in raw_data.items():
        try:
            z = normalize_indicator(raw, name, loaders, z_window)
            if len(z.dropna()) > 52:
                normalized[name] = z
        except Exception:
            logger.debug("Failed to normalize indicator '%s'", name, exc_info=True)

    if not normalized:
        return {}, pd.Series(dtype=float)

    df = pd.concat([z.rename(n) for n, z in normalized.items()], axis=1).sort_index()
    for col in df.columns:
        df[col] = df[col].ffill(limit=_ffill_limit(col, loaders))

    if weights:
        # IC-weighted composite: only use indicators in the weights dict
        active = [c for c in df.columns if c in weights]
        if not active:
            return normalized, pd.Series(dtype=float)
        w = pd.Series({c: weights[c] for c in active})
        min_active = min(2, len(active))
        valid_mask = df[active].notna().sum(axis=1) >= min_active
        composite = (df[active] * w).sum(axis=1).div(w.abs().sum())
        composite = composite.where(valid_mask).dropna()
    else:
        # Equal-weight composite (original behavior)
        valid_mask = df.notna().sum(axis=1) >= min(3, len(normalized))
        composite = df.mean(axis=1).where(valid_mask).dropna()

    composite = composite.ewm(halflife=ema_halflife, min_periods=ema_halflife).mean()
    return normalized, composite


# ==============================================================================
# ADAPTIVE IC-WEIGHTED COMPOSITE
# ==============================================================================


def build_adaptive_composite(
    raw_data: dict,
    loaders,
    target_px: pd.Series,
    z_window: int = 78,
    ema_halflife: int = 4,
    fwd_weeks: int = 13,
    ic_rolling_window: int = 104,
    min_ic_threshold: float = 0.03,
) -> tuple:
    """Build a composite using rolling IC-adaptive weights.

    Like build_axis_composite, but weights are dynamically computed from
    each indicator's recent Spearman IC with forward returns, instead of
    fixed weights. Falls back to equal-weight if no indicator passes
    the IC threshold.

    Args:
        raw_data: Dict of {name: raw_series}.
        loaders: Loader definitions for normalization metadata.
        target_px: Target index price (for IC computation).
        z_window: Base z-score window.
        ema_halflife: EMA halflife for composite smoothing.
        fwd_weeks: Forward return horizon for IC.
        ic_rolling_window: Rolling window for IC computation.
        min_ic_threshold: Minimum |IC| to include indicator.

    Returns:
        Tuple of (normalized_dict, composite_series, adaptive_weights, ic_history).
    """
    from ix.core.macro.engine import normalize_indicator, _ffill_limit

    # Step 1: Normalize all indicators (same as build_axis_composite)
    normalized = {}
    for name, raw in raw_data.items():
        try:
            z = normalize_indicator(raw, name, loaders, z_window)
            if len(z.dropna()) > 52:
                normalized[name] = z
        except Exception:
            logger.debug("Failed to normalize indicator '%s'", name, exc_info=True)

    if not normalized:
        return {}, pd.Series(dtype=float), {}, pd.DataFrame()

    # Step 2: Compute adaptive weights from rolling IC
    weights, ic_history = compute_adaptive_weights(
        normalized, target_px, fwd_weeks, ic_rolling_window,
        min_obs=52, ic_ema_halflife=13, min_ic_threshold=min_ic_threshold,
    )

    # Step 3: Build composite (fall back to equal-weight if no IC weights)
    df = pd.concat([z.rename(n) for n, z in normalized.items()], axis=1).sort_index()
    for col in df.columns:
        df[col] = df[col].ffill(limit=_ffill_limit(col, loaders))

    if weights:
        active = [c for c in df.columns if c in weights]
        if active:
            w = pd.Series({c: weights[c] for c in active})
            min_active = min(2, len(active))
            valid_mask = df[active].notna().sum(axis=1) >= min_active
            composite = (df[active] * w).sum(axis=1).div(w.abs().sum())
            composite = composite.where(valid_mask).dropna()
        else:
            valid_mask = df.notna().sum(axis=1) >= min(3, len(normalized))
            composite = df.mean(axis=1).where(valid_mask).dropna()
    else:
        valid_mask = df.notna().sum(axis=1) >= min(3, len(normalized))
        composite = df.mean(axis=1).where(valid_mask).dropna()

    composite = composite.ewm(halflife=ema_halflife, min_periods=ema_halflife).mean()
    return normalized, composite, weights, ic_history


def compute_vol_scaled_allocation(
    allocation: pd.Series,
    target_px: pd.Series,
    base_weight: float = 0.50,
    vol_window: int = 26,
) -> tuple:
    """Apply volatility scaling to allocation signal.

    Wrapper around vol_scaling.apply_vol_scaling for pipeline integration.

    Returns:
        Tuple of (scaled_allocation, realized_vol, vol_scalar).
    """
    return apply_vol_scaling(
        allocation, target_px, base_weight, vol_window,
    )


# ==============================================================================
# HORIZON 2: BAYESIAN REGIME PROBABILITIES
# ==============================================================================


def compute_regime_probabilities(
    growth_z: pd.Series,
    inflation_z: pd.Series,
    temperature: float = 1.0,
    ema_span: int = 8,
) -> pd.DataFrame:
    """Compute Bayesian regime probabilities via softmax over distance to centroids.

    Places the current (growth, inflation) state in 2D space, computes
    Euclidean distance to each regime centroid, and applies softmax to
    get probability distribution.

    Args:
        growth_z: Growth composite z-score.
        inflation_z: Inflation composite z-score.
        temperature: Softmax temperature (lower = sharper).
        ema_span: EMA smoothing span to prevent week-to-week jumps.

    Returns:
        DataFrame with columns for each regime probability (sum to 1.0).
    """
    temp = max(float(temperature), 1e-6)
    span = max(int(ema_span), 1)
    df = pd.DataFrame(
        {"g": _coerce_series(growth_z, "g"), "i": _coerce_series(inflation_z, "i")}
    ).dropna()
    if df.empty:
        return pd.DataFrame(columns=REGIME_NAMES)

    scores = pd.DataFrame(index=df.index, columns=REGIME_NAMES, dtype=float)
    for regime, centroid in REGIME_CENTROIDS.items():
        dist = np.sqrt((df["g"] - centroid[0]) ** 2 + (df["i"] - centroid[1]) ** 2)
        scores[regime] = -dist / temp

    scores = scores.sub(scores.max(axis=1), axis=0)
    probs = np.exp(scores)

    # Normalize to probabilities
    row_sums = probs.sum(axis=1).replace(0, np.nan)
    probs = probs.div(row_sums, axis=0)

    # EMA smoothing
    probs = probs.ewm(span=span, min_periods=min(4, span)).mean()

    # Re-normalize after smoothing
    row_sums = probs.sum(axis=1).replace(0, np.nan)
    probs = probs.div(row_sums, axis=0)

    return probs.dropna(how="all")


def dominant_regime(probs: pd.DataFrame) -> pd.Series:
    """Return the regime with highest probability at each time step."""
    if probs.empty:
        return pd.Series(dtype=str)
    clean = probs.dropna(how="all")
    if clean.empty:
        return pd.Series(dtype=str)
    return clean.idxmax(axis=1)


def compute_transition_matrix(probs: pd.DataFrame) -> pd.DataFrame:
    """Compute empirical regime transition probabilities from dominant regime series.

    Counts transitions between consecutive dominant regimes and normalizes
    each row to get conditional transition probabilities.
    """
    regimes = dominant_regime(probs)
    matrix = pd.DataFrame(0.0, index=REGIME_NAMES, columns=REGIME_NAMES)
    for curr, nxt in zip(regimes.iloc[:-1], regimes.iloc[1:]):
        if curr in REGIME_NAMES and nxt in REGIME_NAMES:
            matrix.loc[curr, nxt] += 1
    for regime in REGIME_NAMES:
        if matrix.loc[regime].sum() == 0:
            matrix.loc[regime, regime] = 1.0
    row_sums = matrix.sum(axis=1).replace(0, 1)
    return matrix.div(row_sums, axis=0)


def project_probabilities(
    current_probs: np.ndarray,
    trans_matrix: pd.DataFrame,
    steps: int,
) -> np.ndarray:
    """Project regime probabilities forward via transition matrix.

    P(t+n) = P(t) @ T^n

    Args:
        current_probs: Current probability vector (length 4).
        trans_matrix: Empirical transition matrix.
        steps: Number of steps (weeks) to project forward.

    Returns:
        Projected probability vector.
    """
    p = np.asarray(current_probs, dtype=float).copy()
    if p.size != len(REGIME_NAMES):
        raise ValueError(
            f"Expected probability vector of length {len(REGIME_NAMES)}."
        )
    p = np.clip(p, 0.0, None)
    if p.sum() <= 0:
        p = np.full(len(REGIME_NAMES), 1 / len(REGIME_NAMES))
    else:
        p = p / p.sum()

    T = (
        trans_matrix.reindex(index=REGIME_NAMES, columns=REGIME_NAMES, fill_value=0.0)
        .astype(float)
    )
    for regime in REGIME_NAMES:
        if T.loc[regime].sum() <= 0:
            T.loc[regime, regime] = 1.0
    T = T.div(T.sum(axis=1).replace(0, 1), axis=0).values

    for _ in range(steps):
        p = p @ T
    p = np.clip(p, 0.0, None)
    return p / p.sum() if p.sum() > 0 else np.full(len(REGIME_NAMES), 1 / len(REGIME_NAMES))


# ==============================================================================
# HORIZON 1: LIQUIDITY CYCLE
# ==============================================================================


def compute_liquidity_cycle(
    liquidity_composite: pd.Series,
    momentum_window: int = 13,
) -> pd.Series:
    """Classify liquidity cycle phase based on level and momentum.

    - Spring: level < 0, momentum > 0  (accelerating from trough)
    - Summer: level >= 0, momentum > 0  (high and rising)
    - Fall:   level >= 0, momentum <= 0  (decelerating from peak)
    - Winter: level < 0, momentum <= 0   (low and falling)

    Args:
        liquidity_composite: Liquidity composite z-score series.
        momentum_window: Window for computing momentum (diff).

    Returns:
        Series of phase labels.
    """
    level = _coerce_series(liquidity_composite, "liquidity")
    if level.empty:
        return pd.Series(dtype=object)
    momentum = level.diff(momentum_window)
    df = pd.DataFrame({"level": level, "mom": momentum}).dropna()

    conditions = [
        (df["level"] < 0) & (df["mom"] > 0),
        (df["level"] >= 0) & (df["mom"] > 0),
        (df["level"] >= 0) & (df["mom"] <= 0),
        (df["level"] < 0) & (df["mom"] <= 0),
    ]
    return pd.Series(
        np.select(conditions, LIQUIDITY_PHASES, default="Unknown"),
        index=df.index,
    )


# ==============================================================================
# HORIZON 3: TACTICAL SCORE
# ==============================================================================


def compute_tactical_score(tactical_composite: pd.Series) -> pd.Series:
    """Convert tactical composite z-score to a [-2, +2] score.

    No additional smoothing or filtering — the composite is already
    EMA-smoothed (halflife=4) in build_axis_composite. Adding more
    smoothing here would create excessive lag for a short-term signal.

    Importantly, we do NOT apply momentum confirmation or dead-zone
    filtering because many tactical indicators are contrarian. Those
    filters kill the signal at turning points — exactly when contrarian
    indicators are most predictive (e.g. VIX spike reversal).
    """
    return _coerce_series(tactical_composite, "tactical_score").clip(-2, 2)


# ==============================================================================
# COMBINED ALLOCATION MODEL
# ==============================================================================


def compute_allocation(
    regime_probs: pd.DataFrame,
    liquidity_composite: pd.Series,
    tactical_score: pd.Series,
    regime_weight: float = 0.40,
    liquidity_weight: float = 0.30,
    tactical_weight: float = 0.30,
    base_weight: float = 0.50,
    regime_returns: dict | None = None,
) -> pd.Series:
    """Three-horizon blended allocation.

    allocation = base_weight
                 + regime_weight * expected_return_tilt      (max ±20%)
                 + liquidity_weight * tanh(liq_z * 0.8) * 0.18  (max ±18%)
                 + tactical_weight * tanh(tac * 0.8) * 0.20  (max ±20%)

    Uses tanh mapping for liquidity and tactical to saturate at extremes
    while providing meaningful tilts at moderate z-scores. The steeper
    slope (0.8) ensures a z-score of ±1.0 produces ~±12-13% tilt,
    giving the strategy enough leverage to generate alpha.

    The final allocation is clipped to [10%, 90%].

    Args:
        regime_probs: DataFrame of regime probabilities.
        liquidity_composite: Liquidity composite z-score series (continuous).
        tactical_score: Series of tactical scores in [-2, +2].
        regime_weight: Weight for the regime signal (default 0.40).
        liquidity_weight: Weight for the liquidity cycle (default 0.30).
        tactical_weight: Weight for the tactical tilt (default 0.30).
        base_weight: Baseline equity allocation (default 50%).
        regime_returns: Optional dict of per-regime annualized returns.
            Uses empirical target-specific returns instead of generic assumptions.

    Returns:
        Allocation weight series in [0.10, 0.90].
    """
    regime_weight = max(float(regime_weight), 0.0)
    liquidity_weight = max(float(liquidity_weight), 0.0)
    tactical_weight = max(float(tactical_weight), 0.0)
    total_weight = regime_weight + liquidity_weight + tactical_weight
    if total_weight > 0:
        regime_weight /= total_weight
        liquidity_weight /= total_weight
        tactical_weight /= total_weight

    idx = pd.Index([])
    for obj in (regime_probs, liquidity_composite, tactical_score):
        if obj is not None and len(getattr(obj, "index", [])) > 0:
            idx = obj.index if idx.empty else idx.union(obj.index)
    if idx.empty:
        return pd.Series(dtype=float, name="allocation")
    idx = pd.DatetimeIndex(pd.to_datetime(idx)).sort_values()

    liq = pd.Series(0.0, index=idx)
    if liquidity_composite is not None and not liquidity_composite.empty:
        liq = _coerce_series(liquidity_composite, "liquidity").reindex(idx).ffill().fillna(0)
    tac = pd.Series(0.0, index=idx)
    if tactical_score is not None and not tactical_score.empty:
        tac = _coerce_series(tactical_score, "tactical_score").reindex(idx).ffill().fillna(0)

    # 1. Regime signal: expected return from probability-weighted historical returns
    ret_assumptions = regime_returns if regime_returns else REGIME_RETURN_ASSUMPTIONS
    expected_ret = pd.Series(0.0, index=idx)
    if regime_probs is not None and not regime_probs.empty:
        aligned_probs = regime_probs.reindex(idx).ffill().fillna(0.0)
        for regime, ret in ret_assumptions.items():
            if regime in aligned_probs.columns:
                expected_ret += aligned_probs[regime] * ret
    # Scale expected return to allocation tilt: +/-20% max
    ret_tilt = expected_ret.clip(-0.20, 0.20)

    # 2. Liquidity tilt: continuous non-linear signal via tanh
    #    Steeper slope (0.8) gives meaningful tilts at moderate z-scores:
    #      z=±0.5 → tilt ≈ ±6.8%,  z=±1.0 → tilt ≈ ±11.9%,  z=±2.0 → tilt ≈ ±17.4%
    #    Max ±18% so liquidity-only alloc ranges ~32%-68% (vs old 41%-59%)
    liq_tilt = np.tanh(liq * 0.8) * 0.18

    # 3. Tactical tilt: non-linear, larger range for contrarian signals
    #    Contrarian indicators (VIX, put/call) are most predictive at extremes.
    #    Steeper slope + larger cap ensures extreme readings drive real tilts:
    #      z=±0.5 → tilt ≈ ±7.6%,  z=±1.0 → tilt ≈ ±13.3%,  z=±2.0 → tilt ≈ ±19.3%
    #    Max ±20% so tactical-only alloc ranges ~30%-70% (vs old 40%-60%)
    tac_tilt = np.tanh(tac * 0.8) * 0.20

    # Combine
    alloc = (
        base_weight
        + regime_weight * ret_tilt
        + liquidity_weight * liq_tilt
        + tactical_weight * tac_tilt
    )
    alloc = alloc.clip(0.10, 0.90)
    alloc.name = "allocation"
    return alloc.dropna()


# ==============================================================================
# FORWARD RETURN STATS
# ==============================================================================


def liquidity_phase_forward_stats(
    liq_phase: pd.Series,
    target_px: pd.Series,
    fwd_weeks: int = 13,
) -> pd.DataFrame:
    """Compute forward return statistics by liquidity phase.

    Returns DataFrame with one row per phase (Spring/Summer/Fall/Winter).
    """
    px = _coerce_series(target_px, "target_px")
    if liq_phase.empty or px.empty or fwd_weeks < 1:
        return pd.DataFrame()
    fwd_ret = np.log(px).diff(fwd_weeks).shift(-fwd_weeks).mul(100)
    df = pd.DataFrame({"phase": liq_phase, "fwd": fwd_ret}).dropna()

    rows = []
    for phase in LIQUIDITY_PHASES:
        sub = df[df["phase"] == phase]["fwd"]
        if len(sub) < 10:
            continue
        ann_factor = 52 / fwd_weeks
        rows.append(
            {
                "phase": phase,
                "mean_fwd_ret": sub.mean(),
                "median_fwd_ret": sub.median(),
                "std": sub.std(),
                "sharpe": (
                    sub.mean() / sub.std() * np.sqrt(ann_factor)
                    if sub.std() > 0
                    else 0
                ),
                "pct_positive": (sub > 0).mean() * 100,
                "n": len(sub),
            }
        )
    return pd.DataFrame(rows)


def tactical_bucket_forward_stats(
    tac_score: pd.Series,
    target_px: pd.Series,
    fwd_weeks: int = 13,
) -> pd.DataFrame:
    """Compute forward return statistics by tactical score bucket.

    Buckets: Very Bearish (<-1), Bearish (-1 to -0.3), Neutral (-0.3 to 0.3),
    Bullish (0.3 to 1), Very Bullish (>1).
    """
    px = _coerce_series(target_px, "target_px")
    score = _coerce_series(tac_score, "tactical_score")
    if score.empty or px.empty or fwd_weeks < 1:
        return pd.DataFrame()
    fwd_ret = np.log(px).diff(fwd_weeks).shift(-fwd_weeks).mul(100)
    df = pd.DataFrame({"score": score, "fwd": fwd_ret}).dropna()
    if df.empty:
        return pd.DataFrame()

    buckets = [
        ("Very Bearish", -np.inf, -1.0),
        ("Bearish", -1.0, -0.3),
        ("Neutral", -0.3, 0.3),
        ("Bullish", 0.3, 1.0),
        ("Very Bullish", 1.0, np.inf),
    ]
    rows = []
    for label, lo, hi in buckets:
        sub = df[(df["score"] > lo) & (df["score"] <= hi)]["fwd"]
        if len(sub) < 10:
            continue
        ann_factor = 52 / fwd_weeks
        rows.append(
            {
                "bucket": label,
                "mean_fwd_ret": sub.mean(),
                "median_fwd_ret": sub.median(),
                "std": sub.std(),
                "sharpe": (
                    sub.mean() / sub.std() * np.sqrt(ann_factor)
                    if sub.std() > 0
                    else 0
                ),
                "pct_positive": (sub > 0).mean() * 100,
                "n": len(sub),
            }
        )
    return pd.DataFrame(rows)


def regime_forward_return_stats(
    probs: pd.DataFrame,
    target_px: pd.Series,
    fwd_weeks: int = 26,
) -> pd.DataFrame:
    """Compute forward return statistics by dominant regime.

    For each regime, computes the mean/median forward return, standard
    deviation, Sharpe ratio, and % positive hit rate.

    Args:
        probs: Regime probability DataFrame.
        target_px: Target index price series.
        fwd_weeks: Forward return horizon in weeks.

    Returns:
        DataFrame with one row per regime.
    """
    regimes = dominant_regime(probs)
    px = _coerce_series(target_px, "target_px")
    if regimes.empty or px.empty or fwd_weeks < 1:
        return pd.DataFrame()
    fwd_ret = np.log(px).diff(fwd_weeks).shift(-fwd_weeks).mul(100)
    df = pd.DataFrame({"regime": regimes, "fwd": fwd_ret}).dropna()

    rows = []
    for r in REGIME_NAMES:
        sub = df[df["regime"] == r]["fwd"]
        if len(sub) < 10:
            continue
        ann_factor = 52 / fwd_weeks
        rows.append(
            {
                "Regime": r,
                "Mean Fwd Ret (%)": sub.mean(),
                "Median Fwd Ret (%)": sub.median(),
                "Std (%)": sub.std(),
                "Sharpe": (
                    sub.mean() / sub.std() * np.sqrt(ann_factor)
                    if sub.std() > 0
                    else 0
                ),
                "% Positive": (sub > 0).mean() * 100,
                "N": len(sub),
            }
        )
    return pd.DataFrame(rows)
