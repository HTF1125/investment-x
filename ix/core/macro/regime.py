"""Regime detection models ported from DWS.

Three independent regime classification approaches:
  - HPFilterRegime: Hodrick-Prescott filter on macro indicators (level + direction)
  - GMMRegime: Gaussian Mixture Model on asset returns
  - InflationRegime: Inflation vs short-yield grid classification

Plus generic utility functions for forward-return analysis and transition matrices
that work with any categorical state series.

All classes are pure analytics -- they accept pd.Series/pd.DataFrame inputs
and return pd.Series/pd.DataFrame outputs. No data fetching.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture
from statsmodels.tsa.filters.hp_filter import hpfilter


# ==============================================================================
# UTILITY FUNCTIONS
# ==============================================================================


def regime_forward_returns(
    states: pd.Series,
    prices: pd.Series,
    horizons: list[int] | None = None,
) -> pd.DataFrame:
    """Compute average forward returns for each regime state.

    For each horizon (in periods), calculates the forward log return from
    each observation and groups by the regime state active at that time.

    Args:
        states: Categorical state labels with DatetimeIndex.
        prices: Price series with DatetimeIndex.
        horizons: List of forward-return horizons in periods.
            Defaults to [1, 3, 6, 12].

    Returns:
        DataFrame indexed by state with one column per horizon showing
        mean annualised forward return.
    """
    if horizons is None:
        horizons = [1, 3, 6, 12]
    if states.empty or prices.empty:
        return pd.DataFrame()

    prices = prices.sort_index().dropna()
    states = states.sort_index().dropna()

    # Align on common dates via forward-fill of states onto price index
    aligned = pd.DataFrame({"price": prices})
    aligned["state"] = states.reindex(aligned.index, method="ffill")
    aligned = aligned.dropna(subset=["state"])

    rows = {}
    for h in horizons:
        fwd = np.log(aligned["price"]).diff(h).shift(-h)
        df = pd.DataFrame({"state": aligned["state"], "fwd": fwd}).dropna()
        if df.empty:
            continue
        # Infer frequency for annualisation: monthly if median gap > 20 days
        median_gap = aligned.index.to_series().diff().median()
        if hasattr(median_gap, "days") and median_gap.days > 20:
            ann_factor = 12 / h  # monthly data
        else:
            ann_factor = 52 / h  # weekly data
        rows[f"{h}p"] = df.groupby("state")["fwd"].mean() * ann_factor

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


def regime_transition_matrix(states: pd.Series) -> pd.DataFrame:
    """Compute Markov transition matrix from a categorical state series.

    Counts consecutive state transitions and normalises each row to produce
    conditional transition probabilities P(next_state | current_state).

    Args:
        states: Series of state labels (e.g. 'expansion', 'contraction').

    Returns:
        Square DataFrame where entry (i, j) = P(state_j | state_i).
    """
    states = states.dropna()
    if len(states) < 2:
        return pd.DataFrame()

    labels = sorted(states.unique())
    matrix = pd.DataFrame(0.0, index=labels, columns=labels)

    prev = states.iloc[0]
    for curr in states.iloc[1:]:
        if prev in labels and curr in labels:
            matrix.loc[prev, curr] += 1
        prev = curr

    row_sums = matrix.sum(axis=1).replace(0, 1)
    return matrix.div(row_sums, axis=0)


# ==============================================================================
# HP FILTER REGIME
# ==============================================================================


class HPFilterRegime:
    """Hodrick-Prescott filter regime detection on macro indicators.

    Decomposes a macro indicator (e.g. LEI, CLI) into trend and cycle via the
    HP filter, then classifies into four business-cycle states based on the
    trend level and its first difference:

        - expansion:   level >= 0 AND direction >= 0
        - slowdown:    level >= 0 AND direction < 0
        - recovery:    level < 0  AND direction >= 0
        - contraction: level < 0  AND direction < 0

    Args:
        series: Macro indicator series (e.g. OECD CLI deviation from 100).
        lamb: HP filter smoothing parameter.
            Standard values: 1600 (quarterly), 129600 (monthly), 6.25 (annual).
            Use 0 to skip HP filtering and classify on raw level + diff.
        min_periods: Minimum observations required before fitting starts.
        resample_freq: Resample frequency before fitting (e.g. 'M', 'W').
            None to skip resampling.
        months_offset: Publication lag offset in months.
    """

    STATE_LABELS = ["expansion", "slowdown", "recovery", "contraction"]

    def __init__(
        self,
        series: pd.Series,
        lamb: int | float = 129600,
        min_periods: int = 12,
        resample_freq: str | None = "ME",
        months_offset: int = 1,
    ) -> None:
        if not isinstance(series, pd.Series):
            raise TypeError("series must be a pd.Series")
        self.raw = series.copy().dropna()
        self.lamb = lamb
        self.min_periods = max(min_periods, 2)
        self.resample_freq = resample_freq
        self.months_offset = months_offset
        self._signals: pd.DataFrame | None = None
        self._states: pd.Series | None = None

    def fit(self) -> "HPFilterRegime":
        """Compute trend + cycle and classify into states.

        Uses an expanding window so each date only uses data available up
        to that point (no look-ahead).

        Returns:
            self, for method chaining.
        """
        data = self.raw.copy()
        if self.resample_freq:
            data = data.resample(self.resample_freq).last().dropna()
        if self.months_offset:
            data.index = data.index + pd.DateOffset(months=self.months_offset)

        results = []
        for idx in range(self.min_periods, len(data)):
            date = data.index[idx]
            window = data.iloc[: idx + 1]

            if self.lamb == 0:
                # No HP filter -- use raw level and diff
                level = window.iloc[-1]
                direction = window.diff().iloc[-1]
            else:
                cycle, trend = hpfilter(window.values, lamb=self.lamb)
                level = trend[-1]
                direction = np.diff(trend)[-1]

            results.append({"date": date, "level": level, "direction": direction})

        if not results:
            self._signals = pd.DataFrame(columns=["level", "direction"])
            self._states = pd.Series(dtype=str, name="state")
            return self

        self._signals = pd.DataFrame(results).set_index("date")
        self._states = self._signals.apply(self._classify, axis=1)
        self._states.name = "state"
        return self

    @property
    def states(self) -> pd.Series:
        """Return state labels (expansion, slowdown, recovery, contraction)."""
        if self._states is None:
            raise RuntimeError("Call .fit() before accessing states.")
        return self._states

    @property
    def signals(self) -> pd.DataFrame:
        """Return DataFrame with 'level' and 'direction' columns."""
        if self._signals is None:
            raise RuntimeError("Call .fit() before accessing signals.")
        return self._signals

    def forward_returns(
        self,
        prices: pd.Series,
        horizons: list[int] | None = None,
    ) -> pd.DataFrame:
        """Average forward returns by state.

        Args:
            prices: Price series to compute returns from.
            horizons: Forward-return horizons in periods. Defaults to [1, 3, 6, 12].

        Returns:
            DataFrame indexed by state with mean annualised forward returns.
        """
        return regime_forward_returns(self.states, prices, horizons)

    def transition_matrix(self) -> pd.DataFrame:
        """Markov transition matrix between HP filter states."""
        return regime_transition_matrix(self.states)

    @staticmethod
    def _classify(row: pd.Series) -> str:
        """Map (level, direction) to a state label."""
        if row["level"] >= 0 and row["direction"] >= 0:
            return "expansion"
        if row["level"] >= 0 and row["direction"] < 0:
            return "slowdown"
        if row["level"] < 0 and row["direction"] >= 0:
            return "recovery"
        return "contraction"


# ==============================================================================
# GMM REGIME
# ==============================================================================


class GMMRegime:
    """Gaussian Mixture Model regime detection on returns.

    Fits a GMM to return data and labels each observation as belonging to one
    of n_regimes clusters. Regimes are ordered by cluster mean return so that
    regime 0 is always the lowest-return state (risk-off) and the highest
    index is the highest-return state (risk-on).

    Args:
        returns: Return series or DataFrame. If DataFrame, all columns are
            used as features (multi-asset GMM).
        n_regimes: Number of mixture components.
        rolling_window: Rolling mean window to smooth returns before fitting.
            Set to 1 for no smoothing.
        random_state: Random seed for reproducibility.
    """

    def __init__(
        self,
        returns: pd.Series | pd.DataFrame,
        n_regimes: int = 2,
        rolling_window: int = 5,
        random_state: int = 42,
    ) -> None:
        if isinstance(returns, pd.Series):
            self.raw = returns.to_frame()
        elif isinstance(returns, pd.DataFrame):
            self.raw = returns.copy()
        else:
            raise TypeError("returns must be a pd.Series or pd.DataFrame")
        self.n_regimes = n_regimes
        self.rolling_window = max(rolling_window, 1)
        self.random_state = random_state
        self._states: pd.Series | None = None
        self._model: GaussianMixture | None = None
        self._labels: pd.Series | None = None

    def fit(self) -> "GMMRegime":
        """Fit GMM and label regimes by mean return.

        Smooths returns with a rolling mean, fits GMM, then relabels so that
        regime 0 = lowest mean return (risk-off) and regime (n-1) = highest
        mean return (risk-on).

        Returns:
            self, for method chaining.
        """
        smoothed = self.raw.rolling(self.rolling_window).mean().dropna()
        if len(smoothed) < self.n_regimes * 10:
            raise ValueError(
                f"Insufficient data: need >= {self.n_regimes * 10} observations, "
                f"got {len(smoothed)}."
            )

        X = smoothed.values
        gmm = GaussianMixture(
            n_components=self.n_regimes,
            random_state=self.random_state,
        )
        gmm.fit(X)
        raw_labels = gmm.predict(X)
        self._model = gmm

        # Order regimes by mean return (first column if multi-asset)
        cluster_means = pd.Series(
            {k: X[raw_labels == k, 0].mean() for k in range(self.n_regimes)}
        ).sort_values()
        rank_map = {old: new for new, old in enumerate(cluster_means.index)}

        ordered_labels = pd.Series(
            [rank_map[l] for l in raw_labels],
            index=smoothed.index,
            name="regime",
        )
        self._labels = ordered_labels

        # Build descriptive state names
        if self.n_regimes == 2:
            name_map = {0: "risk_off", 1: "risk_on"}
        elif self.n_regimes == 3:
            name_map = {0: "risk_off", 1: "neutral", 2: "risk_on"}
        else:
            name_map = {i: f"regime_{i}" for i in range(self.n_regimes)}

        self._states = ordered_labels.map(name_map)
        self._states.name = "state"
        return self

    @property
    def states(self) -> pd.Series:
        """Return state labels (e.g. risk_off, risk_on)."""
        if self._states is None:
            raise RuntimeError("Call .fit() before accessing states.")
        return self._states

    @property
    def labels(self) -> pd.Series:
        """Return integer regime labels (0 = lowest return cluster)."""
        if self._labels is None:
            raise RuntimeError("Call .fit() before accessing labels.")
        return self._labels

    def transition_matrix(self) -> pd.DataFrame:
        """Regime transition probabilities."""
        return regime_transition_matrix(self.states)

    def forward_returns(
        self,
        prices: pd.Series,
        horizons: list[int] | None = None,
    ) -> pd.DataFrame:
        """Average forward returns by GMM state.

        Args:
            prices: Price series to compute returns from.
            horizons: Forward-return horizons in periods.

        Returns:
            DataFrame indexed by state with mean annualised forward returns.
        """
        return regime_forward_returns(self.states, prices, horizons)

    def cluster_stats(self) -> pd.DataFrame:
        """Summary statistics for each GMM cluster.

        Returns:
            DataFrame with mean, std, and count per regime.
        """
        if self._labels is None or self._model is None:
            raise RuntimeError("Call .fit() before accessing cluster_stats.")

        smoothed = self.raw.rolling(self.rolling_window).mean().dropna()
        df = smoothed.copy()
        df["regime"] = self._labels

        rows = []
        state_names = dict(
            zip(range(self.n_regimes), self.states.unique())
        ) if self._states is not None else {}

        for regime_id in sorted(self._labels.unique()):
            sub = df[df["regime"] == regime_id].drop(columns=["regime"])
            rows.append({
                "regime": regime_id,
                "state": state_names.get(regime_id, f"regime_{regime_id}"),
                "mean": sub.iloc[:, 0].mean(),
                "std": sub.iloc[:, 0].std(),
                "count": len(sub),
            })
        return pd.DataFrame(rows).set_index("regime")


# ==============================================================================
# INFLATION REGIME
# ==============================================================================


class InflationRegime:
    """Inflation vs short-yield grid regime classification.

    Classifies each observation into a grid cell based on smoothed inflation
    and short-yield levels. Grid labels follow the DWS convention:
    inflation bins are labeled AA, A, B, C, D, DD (low to high) and
    short-yield bins are numbered 1-N (low to high).

    Example label: "B3" means inflation in bin B and short-yield in bin 3.

    Args:
        inflation: Inflation expectation or CPI series.
        short_yield: Short-end real yield or similar rate series.
        inflation_range: (min, max) for the inflation grid.
        short_yield_range: (min, max) for the short-yield grid.
        n_bins: Number of grid divisions per axis.
    """

    INFLATION_BIN_LABELS = ["AA", "A", "B", "C", "D", "DD"]

    def __init__(
        self,
        inflation: pd.Series,
        short_yield: pd.Series,
        inflation_range: tuple[float, float] = (1.0, 3.0),
        short_yield_range: tuple[float, float] = (-1.5, 0.5),
        n_bins: int = 5,
    ) -> None:
        if not isinstance(inflation, pd.Series) or not isinstance(short_yield, pd.Series):
            raise TypeError("inflation and short_yield must be pd.Series")

        self.raw_inflation = inflation.copy().dropna()
        self.raw_short_yield = short_yield.copy().dropna()
        self.n_bins = n_bins

        # Build bin edges: n_bins linearly spaced breakpoints + inf
        self.inflation_bins = np.append(
            np.linspace(inflation_range[0], inflation_range[1], n_bins),
            np.inf,
        )
        self.short_yield_bins = np.append(
            np.linspace(short_yield_range[0], short_yield_range[1], n_bins),
            np.inf,
        )

        # Ensure we have enough labels (n_bins + 1 buckets from n_bins breakpoints + inf)
        n_buckets = n_bins + 1
        if n_buckets <= len(self.INFLATION_BIN_LABELS):
            self._inf_labels = self.INFLATION_BIN_LABELS[:n_buckets]
        else:
            # Generate extended labels for large n_bins
            self._inf_labels = [f"bin_{i}" for i in range(n_buckets)]

        self._states: pd.Series | None = None

    def fit(
        self,
        inflation_window: int = 63,
        short_yield_window: int = 63,
    ) -> "InflationRegime":
        """Classify into grid cells using rolling-mean smoothed inputs.

        Args:
            inflation_window: Rolling window for smoothing inflation.
            short_yield_window: Rolling window for smoothing short yield.

        Returns:
            self, for method chaining.
        """
        combined = pd.DataFrame({
            "inflation": self.raw_inflation,
            "short_yield": self.raw_short_yield,
        }).dropna()

        if combined.empty:
            self._states = pd.Series(dtype=str, name="state")
            return self

        smoothed = combined.copy()
        smoothed["inflation"] = smoothed["inflation"].rolling(inflation_window).mean()
        smoothed["short_yield"] = smoothed["short_yield"].rolling(short_yield_window).mean()
        smoothed = smoothed.dropna()

        if smoothed.empty:
            self._states = pd.Series(dtype=str, name="state")
            return self

        self._states = smoothed.apply(self._label_row, axis=1)
        self._states.name = "state"
        return self

    @property
    def states(self) -> pd.Series:
        """Return grid labels (e.g. 'B3', 'AA1', 'DD6')."""
        if self._states is None:
            raise RuntimeError("Call .fit() before accessing states.")
        return self._states

    def forward_returns(
        self,
        prices: pd.Series,
        horizons: list[int] | None = None,
    ) -> pd.DataFrame:
        """Average forward returns by inflation-grid state.

        Args:
            prices: Price series to compute returns from.
            horizons: Forward-return horizons in periods.

        Returns:
            DataFrame indexed by grid label with mean annualised forward returns.
        """
        return regime_forward_returns(self.states, prices, horizons)

    def transition_matrix(self) -> pd.DataFrame:
        """Transition matrix between inflation grid states."""
        return regime_transition_matrix(self.states)

    def _label_row(self, row: pd.Series) -> str:
        """Map a single (inflation, short_yield) observation to a grid label."""
        inf_id = None
        for idx, edge in enumerate(self.inflation_bins):
            if row["inflation"] < edge:
                inf_id = idx
                break
        if inf_id is None:
            inf_id = len(self.inflation_bins) - 1

        sht_id = None
        for idx, edge in enumerate(self.short_yield_bins):
            if row["short_yield"] < edge:
                sht_id = idx + 1  # 1-indexed
                break
        if sht_id is None:
            sht_id = len(self.short_yield_bins)

        return self._inf_labels[inf_id] + str(sht_id)
