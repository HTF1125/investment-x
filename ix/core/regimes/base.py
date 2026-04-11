"""Probabilistic regime classification framework.

Every regime follows the same pipeline:

    Load indicators → z-score → composite per dimension → sigmoid probability
    → state probabilities → confirmation filter → EMA smoothing

Subclasses define *which* indicators, *how* dimensions combine into states,
and optional post-composite guards. The base class provides the full pipeline
so regime objects are pure analytics — no Streamlit, no UI.

Indicator prefix convention
---------------------------
Keys returned by ``_load_indicators`` determine which dimension they belong to:

    g_  → Growth      (GrowthRegime)
    i_  → Inflation   (InflationRegime)
    l_  → Liquidity   (LiquidityRegime)
    m_  → monitor-only (excluded from composites, kept for display)
"""

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np
import pandas as pd


def load_series(code: str, lag: int = 0) -> pd.Series:
    """Load a DB series → month-end, optional publication lag.

    Shared by all regime subclasses so the helper lives once.
    """
    from ix.db.query import Series as DbSeries

    raw = DbSeries(code)
    if raw.empty:
        return pd.Series(dtype=float)
    s = raw.resample("ME").last()
    return s.shift(lag) if lag else s

# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers — canonical implementations used by all regimes
# ─────────────────────────────────────────────────────────────────────────────

#: Level vs rate-of-change blend weights.
#: Heavy ROC weighting matches Hedgeye / 42 Macro: regime classification
#: responds primarily to the *direction* of change, not the absolute level.
LW: float = 0.25  # level weight
RW: float = 0.75  # ROC weight


def zscore(s: pd.Series, window: int = 36, min_p: int = 12) -> pd.Series:
    """Rolling z-score."""
    mu = s.rolling(window, min_periods=min_p).mean()
    sig = s.rolling(window, min_periods=min_p).std()
    return (s - mu) / sig.clip(lower=1e-9)


def zscore_ism(s: pd.Series, window: int = 36, min_p: int = 12) -> pd.Series:
    """Z-score anchored at 50 (ISM expansion/contraction threshold).

    Standard zscore uses a rolling mean which is distorted by COVID-era spikes.
    By anchoring to 50 we correctly score ISM = 53 as positive (expansion) and
    ISM = 48 as negative (contraction).
    """
    deviation = s - 50
    sig = deviation.rolling(window, min_periods=min_p).std()
    return deviation / sig.clip(lower=1e-9)


def zscore_anchored(
    s: pd.Series, anchor: float, window: int = 36, min_p: int = 12
) -> pd.Series:
    """Z-score anchored to a structural baseline (e.g., 2.5% for inflation, 50 for ISM).

    Standard rolling z-score drifts with the series — a value at the historical
    mean reads as z=0 even if the historical mean was abnormal (e.g., 2021-22
    inflation spike pulled the rolling mean to ~4% so today's 3% reads as
    "below average").

    Anchoring to a fixed reference (e.g., Fed inflation target = 2.5%) means a
    reading AT the anchor is z=0 regardless of recent history. The standard
    deviation is still rolling so the scale stays comparable to other indicators.
    """
    deviation = s - anchor
    sig = deviation.rolling(window, min_periods=min_p).std()
    return deviation / sig.clip(lower=1e-9)


def zscore_roc(
    s: pd.Series, window: int = 36, use_pct: bool = True
) -> pd.Series:
    """Z-score of rate-of-change (captures acceleration / deceleration).

    ``use_pct=True`` → 12-month year-over-year percentage change.
    ``use_pct=False`` → 3-month absolute momentum (diff).
    """
    roc = s.pct_change(12) if use_pct else s.diff(3)
    return zscore(roc, window)


def sigmoid(z: pd.Series | float, sensitivity: float = 1.0) -> pd.Series | float:
    """Map z-score → probability (0–1) via logistic function."""
    return 1.0 / (1.0 + np.exp(-z * sensitivity))


# ─────────────────────────────────────────────────────────────────────────────
# Base regime class
# ─────────────────────────────────────────────────────────────────────────────


class Regime(ABC):
    """Abstract base for probabilistic regime classification.

    Subclasses must define:

    * ``name`` — human-readable label (e.g. ``"Macro"``).
    * ``dimensions`` — list of dimension names (e.g. ``["Growth", "Inflation"]``).
    * ``states`` — list of regime state names (e.g. ``["Goldilocks", …]``).
    * ``_load_indicators`` — fetch & z-score all indicators.
    * ``_state_probabilities`` — map dimension probabilities → state probabilities.

    Optionally override:

    * ``_dimension_prefixes`` — override the default first-letter prefix map.
    * ``_exclude_from_composite`` — keep an indicator for display but drop it
      from the dimension composite (e.g. a monitor-only nowcast column).
    """

    # ── Subclass must set ────────────────────────────────────────────────
    name: str
    dimensions: list[str]
    states: list[str]

    # ── Abstract ─────────────────────────────────────────────────────────

    @abstractmethod
    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        """Return z-scored indicator series keyed by prefixed name.

        Convention:
            g_InitialClaims, i_CPI3MAnn, l_HY_OAS  → model indicators
            m_VIX, m_ISMServices                    → monitor-only (excluded)
        """

    @abstractmethod
    def _state_probabilities(
        self, dim_probs: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:
        """Compute state probabilities from dimension probabilities.

        Args:
            dim_probs: ``{DimensionName: probability_series}`` for each dimension.

        Returns:
            ``{"P_StateName": probability_series}`` for each state.
        """

    # ── Optional hooks ───────────────────────────────────────────────────

    def _exclude_from_composite(self) -> set[str]:
        """Column names that match a dimension prefix but should be excluded.

        Override in subclasses to keep indicators for display while excluding
        them from the composite z-score (e.g. ``g_Claims4WMA``).
        """
        return set()

    # ── Public API ───────────────────────────────────────────────────────

    def regime_states(
        self,
        z_window: int = 36,
        sensitivity: float = 1.0,
        smooth_halflife: int = 4,
        exclude: set[str] | None = None,
    ) -> pd.Series:
        """Return the regime state as a text time series.

        Returns:
            ``pd.Series`` with ``DatetimeIndex`` and string values
            (e.g. ``"Goldilocks"``, ``"Easing"``).
        """
        df = self.build(z_window, sensitivity, smooth_halflife, exclude=exclude)
        if "Dominant" not in df.columns:
            return pd.Series(dtype=str, name=self.name)
        return df["Dominant"].dropna().rename(self.name)

    def build(
        self,
        z_window: int = 36,
        sensitivity: float = 1.0,
        smooth_halflife: int = 4,
        exclude: set[str] | None = None,
    ) -> pd.DataFrame:
        """Run the full regime classification pipeline.

        Args:
            exclude: Optional runtime set of indicator column names to drop
                from the composite (in addition to ``_exclude_from_composite``).
                Used by the composition validator to remove indicators that are
                also part of the forward-return target (e.g. drop ``i_WTI`` when
                validating the inflation regime against WTI). Indicators are
                still loaded so they appear in the ``g_*``/``i_*``/... columns,
                but they do not contribute to the dimension's composite z-score.

        Returns a monthly DataFrame containing:

        * Individual indicator z-scores (``g_*``, ``i_*``, ``l_*``, ``m_*``).
        * Composite z-scores per dimension (``{Dim}_Z``).
        * Sigmoid probabilities per dimension (``{Dim}_P``).
        * State probabilities (``P_{State}``) and smoothed (``S_P_{State}``).
        * ``Dominant`` — argmax of the smoothed state probabilities.
        * ``Conviction`` score (0–100).
        * Score / Total counts per dimension.
        """
        # 1. Load indicators
        indicators = self._load_indicators(z_window)
        df = pd.DataFrame(indicators).dropna(how="all")

        # 2. Composite z per dimension
        prefixes = self._dimension_prefixes()
        exclude = self._exclude_from_composite() | (exclude or set())
        for dim in self.dimensions:
            prefix = prefixes[dim]
            parts = [
                df[c]
                for c in df.columns
                if c.startswith(prefix) and c not in exclude
            ]
            if parts:
                # mean(axis=1) skips NaN per-indicator — if 2 of 3 published,
                # the composite is the mean of those 2. Then ffill so the last
                # known composite carries forward into months where no indicators
                # have published yet. This ensures every regime always has a
                # current state, even if its data lags by a month.
                df[f"{dim}_Z"] = pd.concat(parts, axis=1).mean(axis=1).ffill()

        # 3. Sigmoid probabilities per dimension
        dim_probs: dict[str, pd.Series] = {}
        for dim in self.dimensions:
            z_col = f"{dim}_Z"
            if z_col in df.columns:
                df[f"{dim}_P"] = sigmoid(df[z_col].ffill(), sensitivity)
                dim_probs[dim] = df[f"{dim}_P"]

        # 4. State probabilities
        prob_cols = [f"P_{s}" for s in self.states]
        if dim_probs:
            state_probs = self._state_probabilities(dim_probs)
            for col_name, series in state_probs.items():
                df[col_name] = series

        if not all(c in df.columns for c in prob_cols):
            return df.sort_index()

        # 5. EMA smoothing on state probabilities
        if smooth_halflife > 1:
            for col in prob_cols:
                df[f"S_{col}"] = df[col].ewm(halflife=smooth_halflife).mean()
            s_cols = [f"S_{c}" for c in prob_cols]
            sums = df[s_cols].sum(axis=1).clip(lower=1e-9)
            for c in s_cols:
                df[c] = df[c] / sums
        else:
            for col in prob_cols:
                df[f"S_{col}"] = df[col]

        # 6. Dominant state = argmax of smoothed probabilities.
        #    NA-safe: compute idxmax only on rows with a non-NA probability
        #    so pandas ≥ 2.1 doesn't warn (and eventually raise) on all-NA rows.
        s_cols = [f"S_P_{s}" for s in self.states]
        s_prob_df = df[s_cols]
        valid_s = s_prob_df.dropna(how="all")
        if not valid_s.empty:
            df["Dominant"] = (
                valid_s.idxmax(axis=1)
                .str.replace("S_P_", "", regex=False)
                .reindex(df.index)
            )

        # Conviction: 0 at uniform baseline, 100 at full certainty
        n_states = len(self.states)
        baseline = 1.0 / n_states
        df["Conviction"] = (
            (df[s_cols].max(axis=1) - baseline) / (1.0 - baseline) * 100
        ).clip(0, 100)

        # Regime streak counter
        if "Dominant" in df.columns:
            dom = df["Dominant"].ffill()
            streak, prev, streaks = 0, None, []
            for v in dom:
                streak = 1 if v != prev else streak + 1
                prev = v
                streaks.append(streak)
            df["Months_In_Regime"] = streaks

        # Score / Total per dimension (count of positive indicators)
        for dim in self.dimensions:
            prefix = prefixes[dim]
            ind_cols = [
                c for c in df.columns
                if c.startswith(prefix) and c not in exclude
            ]
            if ind_cols:
                df[f"{dim}_Score"] = (df[ind_cols] > 0).sum(axis=1)
                df[f"{dim}_Total"] = len(ind_cols)

        return df.sort_index()

    # ── Internal helpers ─────────────────────────────────────────────────

    def _dimension_prefixes(self) -> dict[str, str]:
        """Map dimension name → indicator prefix (default: first letter + _)."""
        return {dim: dim[0].lower() + "_" for dim in self.dimensions}
