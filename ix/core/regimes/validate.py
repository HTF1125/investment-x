"""Walk-forward validation for multi-axis regime compositions.

Each 1D regime in :mod:`ix.core.regimes` is empirically validated against a
single asset/horizon at registration time. The composer in
:mod:`ix.core.regimes.compose` joins them into multi-axis composites under
a silent independence assumption — but no validator has ever scored these
joint compositions on out-of-sample forward returns.

This module fills that gap. :func:`validate_composition` takes a list of
regime keys, a target asset, and a horizon, then returns the same family of
metrics used to validate single 1D regimes (per-state OOS forward returns,
spread, Cohen's d, Welch p, subsample stability) plus a KL divergence that
exposes how wrong the independence assumption is for the chosen combination.

Walk-forward correctness
------------------------
The regime pipeline is fully *causal*: rolling z-scores, EMA smoothing, and
the N-month confirmation filter all only reference past observations. As a
result, the H_Dominant value at month *t* in a full-history build IS exactly
the decision that would have been made at month *t* with only data ≤ *t*.
We do NOT need to truncate-and-rebuild per month.

What we DO need:

* **Publication lag**: the decision at month-end *t* can only be acted on at
  *t + data_lag_months* (default 1 month for typical macro data release
  cadence). The validator shifts H_Dominant forward by ``data_lag_months``
  before aligning with forward returns.
* **Target/indicator decoupling**: if the target asset is one of the regime's
  own constituent indicators (e.g. inflation regime → WTI), the relevant
  indicator must be dropped from the composite. The validator passes
  ``exclude_indicators`` through to ``Regime.build(exclude=...)``.
* **Warmup**: skip the first ``train_window`` months where rolling z-scores
  haven't accumulated enough history.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from .balance import StateBalance, compute_state_balance
from .compose import build_joint_states
from .compute import _compute_regime_separation, _load_asset_prices
from .registry import get_regime

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Result container
# ─────────────────────────────────────────────────────────────────────


@dataclass
class CompositionValidationResult:
    """Walk-forward validation output for a multi-axis regime composition.

    All return numbers are *annualized* monthly returns expressed as decimals
    (e.g. 0.08 = 8%/yr). ``spread`` is the difference between the best and
    worst state's annualized forward return.
    """

    # Inputs
    keys: list[str]
    target: str
    horizon_months: int
    n_observations: int
    n_states: int

    # Per-state out-of-sample stats
    per_state: dict[str, dict] = field(default_factory=dict)

    # Headline regime-separation metrics (best vs worst)
    spread: Optional[float] = None
    cohens_d: Optional[float] = None
    welch_p: Optional[float] = None
    best_state: Optional[str] = None
    worst_state: Optional[str] = None

    # Vol-normalized spread (Sharpe delta between best and worst state).
    # T1.4 bar is ``spread / target_vol_ann >= 0.25``. See STANDARD.md §3.1.
    target_vol_ann: Optional[float] = None
    vol_normalized_spread: Optional[float] = None

    # State-distribution balance — how evenly the (joint) regime's
    # observations spread across declared states. See balance.py.
    state_balance: Optional["StateBalance"] = None

    # Independence audit: KL(empirical || independent product)
    kl_divergence: Optional[float] = None

    # Subsample stability (split at midpoint)
    subsample_first_spread: Optional[float] = None
    subsample_second_spread: Optional[float] = None
    subsample_sign_consistent: Optional[bool] = None

    # Diagnostics
    warning: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────


def validate_composition(
    keys: list[str],
    target: str,
    horizon_months: int,
    train_window: int = 120,
    params: dict | None = None,
    exclude_indicators: set[str] | None = None,
    data_lag_months: int = 1,
) -> CompositionValidationResult:
    """Walk-forward validation of a multi-axis regime composition.

    Args:
        keys: One or more registered regime keys (axis or phase). Single-key
            calls are valid and used as a regression baseline against the
            registered Tier-1 numbers.
        target: DB code for the target asset (e.g.
            ``"SPY US EQUITY:PX_LAST"``).
        horizon_months: Forward-return horizon in months (typically 1, 3, 6, 12).
        train_window: Months to skip at start of history (rolling z-score
            warmup). Default 120 (10 years).
        params: Build params for ``Regime.build()``. Defaults to first
            regime's registered defaults.
        exclude_indicators: Indicator column names to drop from each
            regime's composite — used when the target asset is one of the
            regime's own classifiers (e.g. drop ``i_WTI`` when validating
            against WTI). Same set is applied to all input regimes.
        data_lag_months: Publication lag — the regime decision at month-end
            *t* can only be acted on at *t + lag*. Default 1.

    Returns:
        :class:`CompositionValidationResult` with per-state stats, spread,
        Cohen's d, Welch p, KL divergence vs independence, and subsample
        stability.
    """
    if not keys:
        raise ValueError("keys must contain at least one regime")

    # Sort for deterministic axis order (matches compose_regimes convention)
    keys = sorted(set(keys))

    # ── Resolve registrations + build params ────────────────────────
    regs = [get_regime(k) for k in keys]
    if params is None:
        params = regs[0].default_params.copy()

    # ── Build each regime once on full history (causal pipeline) ────
    built_dfs: dict[str, pd.DataFrame] = {}
    for reg in regs:
        if reg.regime_class is None:
            raise ValueError(
                f"Regime '{reg.key}' has no regime_class — cannot validate"
            )
        regime = reg.regime_class()
        df = regime.build(
            z_window=params.get("z_window", 96),
            sensitivity=params.get("sensitivity", 2.0),
            smooth_halflife=params.get("smooth_halflife", 2),
            confirm_months=params.get("confirm_months", 3),
            exclude=exclude_indicators,
        )
        if df.empty:
            raise ValueError(f"Regime '{reg.key}' built an empty DataFrame")
        built_dfs[reg.key] = df

    # ── Joint states (single regime → trivial passthrough) ─────────
    if len(keys) == 1:
        df = built_dfs[keys[0]]
        states = list(regs[0].states)
        composite_df = df.copy()
        # Normalize column names so the rest of the pipeline is uniform
        if "H_Dominant" not in composite_df.columns:
            raise ValueError(f"Regime '{keys[0]}' produced no H_Dominant column")
    else:
        joint = build_joint_states(built_dfs, regs, axis_order=keys)
        composite_df = joint.composite_df
        states = joint.composite_states

    # ── Load target asset ───────────────────────────────────────────
    prices = _load_asset_prices({"target": target})
    if prices.empty or "target" not in prices.columns:
        raise ValueError(f"Could not load target series '{target}'")

    target_px = prices["target"].dropna()

    # Forward H-month total return, expressed as monthly index aligned to t
    # (i.e. the value at t is the return realized over [t, t+H])
    fwd_ret = target_px.pct_change(horizon_months).shift(-horizon_months)

    # ── Align regime decision with forward return ───────────────────
    # Decision at month-end t is acted on at t + data_lag_months.
    # We shift H_Dominant forward by lag so the value at month T represents
    # the regime that was *actionable* on T, then align with fwd_ret which
    # at T measures the return [T, T+H].
    h_dom = composite_df["H_Dominant"].copy()
    if data_lag_months > 0:
        h_dom = h_dom.shift(data_lag_months)

    # Drop training warmup
    if train_window > 0 and len(h_dom) > train_window:
        h_dom = h_dom.iloc[train_window:]

    aligned = pd.DataFrame({"regime": h_dom, "target": fwd_ret}).dropna()
    aligned = aligned[aligned["regime"].isin(states)]

    if aligned.empty:
        return CompositionValidationResult(
            keys=keys,
            target=target,
            horizon_months=horizon_months,
            n_observations=0,
            n_states=len(states),
            warning="No aligned observations after warmup + dropna",
        )

    # ── Reuse compute._compute_regime_separation for Cohen's d/Welch ──
    sep = _compute_regime_separation(
        aligned=aligned,
        asset_cols=["target"],
        states=states,
    )["target"]

    # ── Per-state aggregate stats (annualized) ──────────────────────
    # NB: forward returns are already H-month total returns, so annualizing
    # means multiplying by (12 / H) for the mean and by sqrt(12 / H) for vol.
    ann_factor = 12.0 / horizon_months
    per_state: dict[str, dict] = {}
    for s in states:
        rs = aligned.loc[aligned["regime"] == s, "target"].dropna()
        n = len(rs)
        if n < 3:
            per_state[s] = {
                "mean_ann": None, "vol_ann": None, "sharpe": None, "n": n,
            }
            continue
        mean_ann = float(rs.mean()) * ann_factor
        # Forward returns are autocorrelated (overlapping H-month windows),
        # so realized vol UNDERSTATES true vol; report it as a comparison
        # number, not a precise risk measure.
        vol_ann = float(rs.std()) * float(np.sqrt(ann_factor))
        sharpe = mean_ann / vol_ann if vol_ann > 1e-9 else None
        per_state[s] = {
            "mean_ann": mean_ann,
            "vol_ann": vol_ann,
            "sharpe": sharpe,
            "n": n,
        }

    # Spread (annualized): best - worst forward return
    spread: Optional[float] = None
    if sep["best_state"] and sep["worst_state"]:
        best = per_state.get(sep["best_state"], {})
        worst = per_state.get(sep["worst_state"], {})
        if best.get("mean_ann") is not None and worst.get("mean_ann") is not None:
            spread = best["mean_ann"] - worst["mean_ann"]

    # ── Vol-normalized spread (T1.4 bar = Sharpe delta ≥ 0.25) ──────
    # Compute the target's own annualized vol over the same aligned window
    # using non-overlapping monthly log returns, so WTI's 35%-vol spread
    # is directly comparable to TLT's 12%-vol spread. See STANDARD.md §3.1.
    target_vol_ann: Optional[float] = None
    vol_normalized_spread: Optional[float] = None
    try:
        target_monthly_idx = aligned.index
        tgt_px = target_px.reindex(target_monthly_idx).ffill()
        monthly_rets = tgt_px.pct_change().dropna()
        if len(monthly_rets) >= 12:
            target_vol_ann = float(monthly_rets.std(ddof=0)) * float(np.sqrt(12.0))
            if spread is not None and target_vol_ann and target_vol_ann > 1e-9:
                vol_normalized_spread = float(spread / target_vol_ann)
    except Exception:
        # Vol estimation is best-effort — never block the validator on it.
        target_vol_ann = None
        vol_normalized_spread = None

    # ── Subsample stability ─────────────────────────────────────────
    first_spread, second_spread, sign_consistent = _subsample_stability(
        aligned, states, ann_factor
    )

    # ── KL divergence vs independence (only for multi-axis) ─────────
    kl_div: Optional[float] = None
    if len(keys) >= 2:
        kl_div = _kl_vs_independence(built_dfs, regs, axis_order=keys)

    # ── State-distribution balance ──────────────────────────────────
    # How evenly does the (joint) regime spread observations across its
    # declared states? Computed on the aligned+labeled series (after
    # warmup skip + data-lag shift) so it reflects the history actually
    # used in the spread measurement.
    try:
        balance = compute_state_balance(aligned["regime"], states)
    except Exception:
        balance = None

    return CompositionValidationResult(
        keys=keys,
        target=target,
        horizon_months=horizon_months,
        n_observations=int(len(aligned)),
        n_states=len(states),
        per_state=per_state,
        spread=spread,
        cohens_d=sep["cohens_d"],
        welch_p=sep["p_value"],
        best_state=sep["best_state"],
        worst_state=sep["worst_state"],
        target_vol_ann=target_vol_ann,
        vol_normalized_spread=vol_normalized_spread,
        state_balance=balance,
        kl_divergence=kl_div,
        subsample_first_spread=first_spread,
        subsample_second_spread=second_spread,
        subsample_sign_consistent=sign_consistent,
    )


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _subsample_stability(
    aligned: pd.DataFrame,
    states: list[str],
    ann_factor: float,
) -> tuple[Optional[float], Optional[float], Optional[bool]]:
    """Split history at midpoint, recompute spread on each half.

    Returns ``(first_half_spread, second_half_spread, signs_agree)``.
    Signs agree → the regime separation is stable across eras (good).
    """
    n = len(aligned)
    if n < 60:
        return None, None, None

    mid = n // 2
    first = aligned.iloc[:mid]
    second = aligned.iloc[mid:]

    def _spread(df: pd.DataFrame) -> Optional[float]:
        means: dict[str, float] = {}
        for s in states:
            r = df.loc[df["regime"] == s, "target"].dropna()
            if len(r) >= 3:
                means[s] = float(r.mean())
        if len(means) < 2:
            return None
        return (max(means.values()) - min(means.values())) * ann_factor

    s1 = _spread(first)
    s2 = _spread(second)
    if s1 is None or s2 is None:
        return s1, s2, None
    return s1, s2, bool((s1 >= 0) == (s2 >= 0))


def _kl_vs_independence(
    built_dfs: dict[str, pd.DataFrame],
    regs: list,
    axis_order: list[str],
) -> Optional[float]:
    """KL divergence between empirical joint state distribution and the
    distribution that would be implied by axis independence.

    Large KL → axes are NOT independent → ``compose_regimes``'s product-of-
    marginals joint probability is meaningfully wrong for this combination
    and a copula or empirical-joint approach would do better.

    Computed on the H_Dominant (hard) state sequence of each input regime,
    aligned on the common index. Smoothing constant 1e-9 prevents log(0).
    """
    common = built_dfs[axis_order[0]].index
    for k in axis_order[1:]:
        common = common.intersection(built_dfs[k].index)
    if len(common) < 60:
        return None

    # Per-axis dominant state series, aligned
    cols: dict[str, pd.Series] = {}
    for k in axis_order:
        s = built_dfs[k]["H_Dominant"].reindex(common).dropna()
        if s.empty:
            return None
        cols[k] = s
    aligned_idx = cols[axis_order[0]].index
    for k in axis_order[1:]:
        aligned_idx = aligned_idx.intersection(cols[k].index)
    if len(aligned_idx) < 60:
        return None

    # Empirical joint distribution: count tuples
    tuples = list(zip(*[cols[k].reindex(aligned_idx).values for k in axis_order]))
    n_total = len(tuples)
    joint_counts: dict[tuple, int] = {}
    for t in tuples:
        joint_counts[t] = joint_counts.get(t, 0) + 1
    p_emp = {t: c / n_total for t, c in joint_counts.items()}

    # Marginal distributions per axis
    marginals: list[dict[str, float]] = []
    for k in axis_order:
        vals = cols[k].reindex(aligned_idx).values
        m: dict[str, float] = {}
        for v in vals:
            m[v] = m.get(v, 0.0) + 1.0
        marginals.append({s: c / n_total for s, c in m.items()})

    # KL(p_emp || p_indep)
    eps = 1e-12
    kl = 0.0
    for combo, p in p_emp.items():
        q = 1.0
        for axis_state, marg in zip(combo, marginals):
            q *= marg.get(axis_state, eps)
        if q < eps:
            q = eps
        kl += p * np.log(p / q)
    return float(kl)
