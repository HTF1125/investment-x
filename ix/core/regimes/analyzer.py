"""Multi-dimensional regime analyzer.

Thin class wrapper around :func:`compose_regimes` that lazily builds a
composite from 2+ registered 1D regimes and exposes analytical helpers:

* joint state time series (latest + history)
* state frequencies and average durations
* empirical transition matrix (1-step)
* conditional performance of an arbitrary return series per joint state

The heavy lifting lives in :mod:`compose` (which already computes the joint
state, joint probabilities, forward projections, and snapshot rendering).
This class is just an ergonomic entry point for notebooks, scripts, and
Streamlit apps that want to ask questions about a multi-axis regime
without re-deriving the composition by hand.

Example
-------
    >>> from ix.core.regimes import MultiDimRegimeAnalyzer
    >>> a = MultiDimRegimeAnalyzer(["growth", "inflation", "liquidity"])
    >>> a.current_state()
    'Expansion+Falling+Easing'
    >>> a.state_frequencies().head()
    Expansion+Falling+Easing     0.28
    Expansion+Rising+Easing      0.19
    ...
    >>> a.transition_matrix().round(2)            # 1-step transitions
    >>> a.conditional_performance(spy_monthly_rets)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd

from .compose import build_joint_states, compose_regimes
from .registry import RegimeRegistration, get_regime


@dataclass
class _Built:
    composite_df: pd.DataFrame
    composite_states: list[str]
    joint_combos: list[tuple[str, ...]]
    axis_keys: list[str]
    regs: list[RegimeRegistration]
    display_name: str


class MultiDimRegimeAnalyzer:
    """Analyze a composite of 2+ registered 1D regimes.

    The analyzer normalizes the key order (so ``["growth", "inflation"]``
    and ``["inflation", "growth"]`` produce the same composite), validates
    that each key is a 1D regime (``category`` ∈ {``axis``, ``phase``}),
    and builds the composite lazily the first time any method is called.

    Parameters
    ----------
    keys:
        Registered 1D regime keys to compose. Must contain at least 2.
    params:
        Optional build params shared by every input regime. Defaults to the
        first regime's ``default_params``. Supported keys: ``z_window``,
        ``sensitivity``, ``smooth_halflife``, ``confirm_months``.
    """

    def __init__(self, keys: list[str], params: Optional[dict] = None) -> None:
        if len(keys) < 2:
            raise ValueError(
                f"Need at least 2 regimes to analyze, got {len(keys)}"
            )
        self.keys: list[str] = sorted(set(keys))
        self.params: Optional[dict] = params
        self._built: Optional[_Built] = None
        self._snapshot: Optional[dict] = None

    # ── Lazy build ───────────────────────────────────────────────────

    def _ensure_built(self) -> _Built:
        if self._built is not None:
            return self._built

        regs: list[RegimeRegistration] = []
        for k in self.keys:
            r = get_regime(k)
            if r.category not in ("axis", "phase"):
                raise ValueError(
                    f"Regime '{k}' is category={r.category!r}; only 1D "
                    f"'axis' or 'phase' regimes can be analyzed jointly."
                )
            if r.regime_class is None:
                raise ValueError(
                    f"Regime '{k}' has no regime_class — cannot build."
                )
            regs.append(r)

        params = self.params if self.params is not None else regs[0].default_params.copy()

        built_dfs: dict[str, pd.DataFrame] = {}
        for reg in regs:
            regime = reg.regime_class()  # type: ignore[misc]
            df = regime.build(
                z_window=params.get("z_window", 96),
                sensitivity=params.get("sensitivity", 2.0),
                smooth_halflife=params.get("smooth_halflife", 2),
                confirm_months=params.get("confirm_months", 3),
            )
            if df.empty:
                raise ValueError(f"Regime '{reg.key}' built an empty DataFrame")
            built_dfs[reg.key] = df

        joint = build_joint_states(built_dfs, regs, self.keys)
        self._built = _Built(
            composite_df=joint.composite_df,
            composite_states=joint.composite_states,
            joint_combos=joint.joint_combos,
            axis_keys=self.keys,
            regs=regs,
            display_name=joint.display_name,
        )
        return self._built

    # ── Public properties ────────────────────────────────────────────

    @property
    def display_name(self) -> str:
        return self._ensure_built().display_name

    @property
    def states(self) -> list[str]:
        """Cartesian-product joint state names in build order."""
        return list(self._ensure_built().composite_states)

    @property
    def composite_df(self) -> pd.DataFrame:
        """Raw joint-state DataFrame produced by :func:`build_joint_states`."""
        return self._ensure_built().composite_df

    # ── State timeseries ─────────────────────────────────────────────

    def joint_states(self, *, use_confirmed: bool = True) -> pd.Series:
        """Return the dominant joint state as a labelled time series.

        Args:
            use_confirmed: If ``True`` (default), use the confirmation-filtered
                labels (``H_Dominant``). If ``False``, use the raw smoothed
                labels (``S_Dominant``) — reacts earlier, more whipsaw.
        """
        df = self.composite_df
        col = "H_Dominant" if use_confirmed and "H_Dominant" in df.columns else "S_Dominant"
        if col not in df.columns:
            raise RuntimeError(
                f"composite_df is missing '{col}' — joint build may have failed."
            )
        out = df[col].dropna()
        out.name = "joint_state"
        return out

    def current_state(self, *, use_confirmed: bool = True) -> Optional[str]:
        """Latest joint state label, or ``None`` if the series is empty."""
        s = self.joint_states(use_confirmed=use_confirmed)
        return None if s.empty else str(s.iloc[-1])

    def state_balance(
        self,
        *,
        use_confirmed: bool = True,
        sample_floor: int = 30,
    ):
        """Distribution diagnostics for the joint states.

        Returns a :class:`ix.core.regimes.balance.StateBalance` with:

        * ``entropy_normalized`` — Shannon entropy / log(n_declared),
          in [0, 1]. 1.0 = perfectly uniform; near 0 = concentrated on
          one state.
        * ``effective_states`` — ``exp(entropy)`` equivalent uniform count.
        * ``usable_ratio`` — fraction of declared joint states whose
          observation count clears ``sample_floor`` (default 30 = T1.3).
        * ``counts`` / ``frequencies`` — per-state observations.
        * ``verdict`` — one of ``balanced`` / ``skewed`` / ``concentrated``
          / ``degenerate``.

        A cartesian composition with low usable_ratio means most of the
        joint state space is orphaned with too few observations to trust
        (e.g. ``cb_surprise × vol_term`` posts ``entropy ≈ 0.79`` but
        ``usable_ratio = 0.33`` because 4 of 6 joint states fall below
        the T1.3 floor — the cb_surprise tails collapse under
        multiplication).
        """
        from .balance import compute_state_balance
        return compute_state_balance(
            self.joint_states(use_confirmed=use_confirmed),
            self.states,
            sample_floor=sample_floor,
        )

    # ── Distributional stats ─────────────────────────────────────────

    def state_frequencies(self, *, use_confirmed: bool = True) -> pd.Series:
        """Proportion of time each joint state has been active.

        Index is the full set of joint states (zero entries included so every
        combination is visible). Sums to 1.0 over the observed history.
        """
        s = self.joint_states(use_confirmed=use_confirmed)
        counts = s.value_counts()
        total = float(counts.sum())
        if total == 0:
            return pd.Series(0.0, index=self.states, name="frequency")
        freq = (counts / total).reindex(self.states, fill_value=0.0)
        freq.name = "frequency"
        return freq

    def state_durations(self, *, use_confirmed: bool = True) -> pd.DataFrame:
        """Descriptive stats of consecutive-run lengths per joint state.

        Returns a DataFrame indexed by joint state with columns ``count``
        (number of distinct runs), ``mean`` (avg run length in periods),
        ``median``, ``min``, ``max``, and ``total`` (total periods in state).
        Run lengths are measured in the composite_df's native frequency
        (monthly for the built-in regimes).
        """
        s = self.joint_states(use_confirmed=use_confirmed)
        if s.empty:
            return pd.DataFrame(
                columns=["count", "mean", "median", "min", "max", "total"],
                index=self.states,
            )

        runs: dict[str, list[int]] = {st: [] for st in self.states}
        current_state = s.iloc[0]
        current_len = 1
        for val in s.iloc[1:]:
            if val == current_state:
                current_len += 1
            else:
                runs.setdefault(current_state, []).append(current_len)
                current_state = val
                current_len = 1
        runs.setdefault(current_state, []).append(current_len)

        rows = []
        for st in self.states:
            lengths = runs.get(st, [])
            if lengths:
                rows.append({
                    "count": len(lengths),
                    "mean": float(np.mean(lengths)),
                    "median": float(np.median(lengths)),
                    "min": int(np.min(lengths)),
                    "max": int(np.max(lengths)),
                    "total": int(np.sum(lengths)),
                })
            else:
                rows.append({
                    "count": 0, "mean": 0.0, "median": 0.0,
                    "min": 0, "max": 0, "total": 0,
                })
        return pd.DataFrame(rows, index=self.states)

    def transition_matrix(self, *, use_confirmed: bool = True) -> pd.DataFrame:
        """Empirical 1-step transition matrix P(next | current).

        Rows are the current joint state, columns are the next period's
        joint state. Rows sum to 1.0 when the state has been observed; an
        unobserved row is all zeros.
        """
        s = self.joint_states(use_confirmed=use_confirmed)
        if len(s) < 2:
            return pd.DataFrame(0.0, index=self.states, columns=self.states)

        cur = s.iloc[:-1].values
        nxt = s.iloc[1:].values
        mat = pd.DataFrame(0.0, index=self.states, columns=self.states)
        for c, n in zip(cur, nxt):
            if c in mat.index and n in mat.columns:
                mat.at[c, n] += 1.0

        row_sums = mat.sum(axis=1)
        nonzero = row_sums > 0
        mat.loc[nonzero] = mat.loc[nonzero].div(row_sums[nonzero], axis=0)
        return mat

    # ── Conditional performance ──────────────────────────────────────

    def conditional_performance(
        self,
        returns: pd.Series,
        *,
        diagnostic: bool = False,
        use_confirmed: bool = True,
        periods_per_year: int = 12,
    ) -> pd.DataFrame:
        """Aggregate a return series by joint state — DIAGNOSTIC ONLY.

        .. warning::
           This method classifies states and measures forward returns on the
           **same** history. It is NOT a backtest and is NOT walk-forward
           safe — state labels at time ``t`` were fitted using data including
           and after ``t``, so the Sharpe/CAGR numbers carry look-ahead bias.

           Use this for **exploration and sanity checks only** ("does the
           joint state ordering look sensible?"). For anything strategy-
           related, use :func:`ix.core.regimes.validate.validate_composition`
           which runs a walk-forward re-fit at every timestamp with no
           look-ahead contamination.

           To acknowledge this and silence the ``ValueError``, pass
           ``diagnostic=True`` explicitly.

        Args:
            returns: Asset returns series (any frequency) indexed by datetime.
                Should already be aligned to the composite's frequency
                (monthly for the built-in regimes). The analyzer inner-joins
                on index dates.
            diagnostic: Must be set to ``True`` to run the method. This is a
                speed bump, not a lock — it forces the caller to acknowledge
                they understand the in-sample contamination before looking
                at the numbers.
            use_confirmed: Use ``H_Dominant`` (confirmed) vs ``S_Dominant``
                (raw smoothed) for the state column.
            periods_per_year: Annualization factor. Defaults to 12 (monthly).

        Returns:
            DataFrame indexed by joint state with columns:

            * ``n``:       number of observations in that state
            * ``freq``:    share of total observations
            * ``mean``:    mean per-period return
            * ``std``:     per-period standard deviation
            * ``cagr``:    annualized geometric return
            * ``vol``:     annualized volatility
            * ``sharpe``:  annualized Sharpe (zero RF), 0 if std == 0
            * ``hit``:     proportion of positive returns
            * ``cum``:     cumulative compounded return while in state

        Raises:
            ValueError: if ``diagnostic`` is not set to ``True``.
        """
        if not diagnostic:
            raise ValueError(
                "conditional_performance() is DIAGNOSTIC ONLY — it carries "
                "look-ahead bias because states are fitted on the same "
                "history used to measure forward returns. For strategy "
                "validation use ix.core.regimes.validate.validate_composition "
                "instead. If you understand this and want a sanity-check "
                "read, call with diagnostic=True."
            )
        state_s = self.joint_states(use_confirmed=use_confirmed)
        if returns.empty or state_s.empty:
            return pd.DataFrame(
                columns=["n", "freq", "mean", "std", "cagr", "vol", "sharpe", "hit", "cum"],
                index=self.states,
            )

        joined = pd.concat(
            [returns.rename("ret"), state_s.rename("state")],
            axis=1,
            join="inner",
        ).dropna()
        if joined.empty:
            return pd.DataFrame(
                columns=["n", "freq", "mean", "std", "cagr", "vol", "sharpe", "hit", "cum"],
                index=self.states,
            )

        total_n = float(len(joined))
        rows = []
        for st in self.states:
            bucket = joined.loc[joined["state"] == st, "ret"]
            n = int(len(bucket))
            if n == 0:
                rows.append({
                    "n": 0, "freq": 0.0, "mean": 0.0, "std": 0.0,
                    "cagr": 0.0, "vol": 0.0, "sharpe": 0.0, "hit": 0.0, "cum": 0.0,
                })
                continue
            mean = float(bucket.mean())
            std = float(bucket.std(ddof=0))
            cum = float((1.0 + bucket).prod() - 1.0)
            cagr = (
                float((1.0 + mean) ** periods_per_year - 1.0)
                if np.isfinite(mean) else 0.0
            )
            vol = std * float(np.sqrt(periods_per_year))
            sharpe = (mean * periods_per_year) / vol if vol > 0 else 0.0
            hit = float((bucket > 0).mean())
            rows.append({
                "n": n,
                "freq": n / total_n,
                "mean": mean,
                "std": std,
                "cagr": cagr,
                "vol": vol,
                "sharpe": sharpe,
                "hit": hit,
                "cum": cum,
            })
        return pd.DataFrame(rows, index=self.states)

    # ── Snapshot passthrough ─────────────────────────────────────────

    def snapshot(self) -> dict:
        """Full composition snapshot via :func:`compose_regimes`.

        Matches the JSONB shape used by ``/api/regimes/compose`` responses.
        Cached after the first call.
        """
        if self._snapshot is None:
            self._snapshot = compose_regimes(self.keys, params=self.params)
        return self._snapshot
