"""State-distribution balance metrics for regime classifiers.

A regime that spends 95% of its time in one state and 5% in the other
has a very different actionability profile from a regime split 55/45 —
even if both pass the T1.4 spread bar. These helpers quantify how
evenly a regime (or a joint composition of regimes) distributes its
observations across declared states.

The metrics answer two distinct questions:

1. **Is the distribution balanced?** — normalized Shannon entropy,
   bounded in [0, 1]. 1.0 means every state fires with equal frequency;
   values near 0 mean one state dominates.

2. **Are the minority states tradeable?** — usable-state ratio, which
   counts how many states clear a minimum sample floor (default 30,
   matching the T1.3 bar) divided by the number of declared states.
   A regime with high entropy but 0/6 usable states is worse for a
   systematic strategy than a regime with 2/2 usable states at
   slightly lower entropy.

Both are reported. High entropy + high usable ratio = ideal.
Low entropy → concentrated; low usable ratio → the cartesian product
created orphan small-n states that can't be backtested.

Example
-------
    >>> from ix.core.regimes.balance import compute_state_balance
    >>> from ix.core.regimes import MultiDimRegimeAnalyzer
    >>> a = MultiDimRegimeAnalyzer(["cb_surprise", "vol_term"])
    >>> bal = compute_state_balance(a.joint_states(), declared_states=a.states)
    >>> print(bal.verdict, bal.entropy_normalized, bal.usable_ratio)
    skewed 0.793 0.333
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd


#: Default minimum sample size per state (matches T1.3 quality bar).
DEFAULT_SAMPLE_FLOOR: int = 30


@dataclass
class StateBalance:
    """Distribution diagnostics for a regime's observed state series.

    Attributes
    ----------
    n_total: int
        Total number of classified observations.
    n_declared: int
        Number of declared states (from the regime's ``states`` list).
    n_observed: int
        Number of declared states actually seen in the history.
    counts: dict[str, int]
        Observations per declared state (includes 0s for unseen states).
    frequencies: dict[str, float]
        Share of total observations per declared state. Sums to 1.0
        across observed states.
    entropy_normalized: float
        Shannon entropy divided by log(n_declared), in [0, 1]. 1.0
        means perfectly uniform; 0.0 means all mass on one state.
    effective_states: float
        ``exp(shannon_entropy)`` — equivalent count of uniformly-weighted
        states that would produce the observed entropy. Always ≤
        ``n_declared``.
    sample_floor: int
        The n-per-state threshold used for ``n_usable`` / ``usable_ratio``.
    n_usable: int
        Count of declared states with ≥ ``sample_floor`` observations.
    usable_ratio: float
        ``n_usable / n_declared`` — fraction of the cartesian product
        that has enough observations to survive a T1.3-style check.
    min_count: int
    max_count: int
    min_max_ratio: float
        ``min_count / max_count`` — cheap concentration heuristic.
    verdict: str
        One-word summary ∈ {``balanced``, ``skewed``, ``concentrated``,
        ``degenerate``}. See :func:`compute_state_balance` for the
        classification rules.
    """

    n_total: int
    n_declared: int
    n_observed: int
    counts: dict[str, int]
    frequencies: dict[str, float]
    entropy_normalized: float
    effective_states: float
    sample_floor: int
    n_usable: int
    usable_ratio: float
    min_count: int
    max_count: int
    min_max_ratio: float
    verdict: str

    def summary(self) -> str:
        """Compact one-line summary for terminal display."""
        return (
            f"n={self.n_total}  entropy={self.entropy_normalized:.2f}  "
            f"eff_states={self.effective_states:.1f}/{self.n_declared}  "
            f"usable={self.n_usable}/{self.n_declared}  "
            f"min/max={self.min_max_ratio:.2f}  verdict={self.verdict}"
        )

    def detail(self) -> str:
        """Multi-line detail with per-state counts and frequencies."""
        lines = [
            f"State balance — {self.verdict}",
            f"  n_total            : {self.n_total}",
            f"  n_declared         : {self.n_declared}",
            f"  n_observed         : {self.n_observed}",
            f"  entropy_normalized : {self.entropy_normalized:.3f}  (1.0 = uniform)",
            f"  effective_states   : {self.effective_states:.2f}  (of {self.n_declared})",
            f"  usable (n ≥ {self.sample_floor})    : {self.n_usable}/{self.n_declared}  "
            f"({100 * self.usable_ratio:.0f}%)",
            f"  min / max counts   : {self.min_count} / {self.max_count}",
            f"  min/max ratio      : {self.min_max_ratio:.3f}",
            "",
            "  Per-state counts:",
        ]
        for st, n in self.counts.items():
            freq = self.frequencies.get(st, 0.0)
            mark = "" if n >= self.sample_floor else "  ← below floor"
            lines.append(f"    {st:32s}  n={n:4d}  ({100*freq:5.1f}%){mark}")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────


def compute_state_balance(
    states_series: pd.Series,
    declared_states: list[str],
    sample_floor: int = DEFAULT_SAMPLE_FLOOR,
) -> StateBalance:
    """Compute distribution metrics for a regime's observed state series.

    Parameters
    ----------
    states_series:
        Time-indexed series of regime state labels (e.g. ``Dominant``
        from a regime's ``build()`` output, or ``MultiDimRegimeAnalyzer.
        joint_states()``). NaNs are dropped automatically.
    declared_states:
        The list of states the regime/composition DECLARES it can produce.
        States in this list that never fire contribute ``count=0`` and
        pull down the entropy. States in the series that are NOT declared
        are treated as noise and excluded.
    sample_floor:
        Minimum observations per state for the state to count as
        "usable". Defaults to 30, matching the T1.3 quality bar.

    Returns
    -------
    :class:`StateBalance` with entropy, usable-state ratio, per-state
    counts, and a verdict.

    Verdict rules
    -------------
    - **degenerate**    — only one state ever observed (n_observed < 2)
    - **balanced**      — entropy ≥ 0.85 AND usable_ratio = 1.0
    - **skewed**        — entropy ≥ 0.60, OR usable_ratio ≥ 2/3
    - **concentrated**  — entropy < 0.60 AND usable_ratio < 2/3
    """
    s = states_series.dropna()
    declared = list(declared_states)
    declared_set = set(declared)

    # Filter to only declared states — ignore any noise / legacy labels
    valid = s[s.isin(declared_set)]
    total = int(len(valid))

    counts_obs = valid.value_counts().to_dict() if total > 0 else {}
    counts: dict[str, int] = {st: int(counts_obs.get(st, 0)) for st in declared}
    freqs: dict[str, float] = (
        {st: counts[st] / total for st in declared} if total > 0
        else {st: 0.0 for st in declared}
    )

    n_observed = sum(1 for n in counts.values() if n > 0)
    n_declared = len(declared)

    # Shannon entropy over non-zero probabilities only (avoid log 0)
    if total == 0 or n_observed < 2:
        entropy_nats = 0.0
        entropy_norm = 0.0
        effective = float(n_observed)
    else:
        probs = np.array([p for p in freqs.values() if p > 0.0], dtype=float)
        entropy_nats = float(-(probs * np.log(probs)).sum())
        max_entropy = float(np.log(n_declared)) if n_declared > 1 else 1.0
        entropy_norm = entropy_nats / max_entropy if max_entropy > 0 else 0.0
        effective = float(np.exp(entropy_nats))

    # Usable-state count (T1.3 floor)
    n_usable = sum(1 for n in counts.values() if n >= sample_floor)
    usable_ratio = n_usable / n_declared if n_declared > 0 else 0.0

    # Min / max counts — useful concentration heuristic
    counts_list = list(counts.values())
    min_count = int(min(counts_list)) if counts_list else 0
    max_count = int(max(counts_list)) if counts_list else 0
    min_max_ratio = (min_count / max_count) if max_count > 0 else 0.0

    # Verdict
    if n_observed < 2:
        verdict = "degenerate"
    elif entropy_norm >= 0.85 and usable_ratio >= 0.999:
        verdict = "balanced"
    elif entropy_norm >= 0.60 or usable_ratio >= 2 / 3:
        verdict = "skewed"
    else:
        verdict = "concentrated"

    return StateBalance(
        n_total=total,
        n_declared=n_declared,
        n_observed=n_observed,
        counts=counts,
        frequencies=freqs,
        entropy_normalized=round(entropy_norm, 4),
        effective_states=round(effective, 3),
        sample_floor=sample_floor,
        n_usable=n_usable,
        usable_ratio=round(usable_ratio, 4),
        min_count=min_count,
        max_count=max_count,
        min_max_ratio=round(min_max_ratio, 4),
        verdict=verdict,
    )


def state_balance_dict(balance: StateBalance) -> dict:
    """Serialize a StateBalance into a JSON-safe dict for JSONB snapshots."""
    return {
        "n_total": balance.n_total,
        "n_declared": balance.n_declared,
        "n_observed": balance.n_observed,
        "counts": dict(balance.counts),
        "frequencies": {k: round(v, 6) for k, v in balance.frequencies.items()},
        "entropy_normalized": balance.entropy_normalized,
        "effective_states": balance.effective_states,
        "sample_floor": balance.sample_floor,
        "n_usable": balance.n_usable,
        "usable_ratio": balance.usable_ratio,
        "min_count": balance.min_count,
        "max_count": balance.max_count,
        "min_max_ratio": balance.min_max_ratio,
        "verdict": balance.verdict,
    }
