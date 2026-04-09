"""Dynamic composition of single-metric regimes into multi-axis composites.

Lets a user pick 2+ single-metric regimes (any axis or phase regime) and
get a composite regime computed on the fly. The composite uses joint state
assignment: at each timestep, take H_Dominant from each input regime and
combine them. The result is rendered through the same JSONB shape as a
normal regime snapshot.

Example
-------
    >>> from ix.core.regimes.compose import compose_regimes
    >>> snapshot = compose_regimes(["growth", "inflation"])
    >>> snapshot["meta"]["display_name"]
    'Growth × Inflation (custom)'
    >>> snapshot["meta"]["states"]
    ['Expansion+Falling', 'Expansion+Rising', 'Contraction+Falling', 'Contraction+Rising']

Composability rules
-------------------
* Any 1D regime (category="axis" or category="phase") can be composed.
  Pre-built composites (category="composite") are NOT composable — they
  emerge automatically from selecting their constituent axes.
* At least 2 keys required
* Order is normalized (sorted) so growth+inflation == inflation+growth
* Joint states are mechanically named from the cartesian product of
  the input regimes' states (e.g. "Expansion+Falling"). The composer
  has no prior knowledge of any "named" combinations like Goldilocks —
  every combination is treated identically.
* When state name collisions exist (e.g. credit and growth both have a
  state called "Expansion"), names are disambiguated with the regime key
  prefix (e.g. "credit:Expansion+growth:Expansion")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from itertools import product

import numpy as np
import pandas as pd

from .base import Regime
from .compute import (
    DEFAULT_ASSET_TICKERS,
    compute_asset_analytics,
    _safe_float,
    _series_to_list,
    _dates_to_list,
)
from .registry import get_regime, RegimeRegistration

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────
# Joint state build (extracted for reuse by validator)
# ─────────────────────────────────────────────────────────────────────


@dataclass
class JointStateBuild:
    """Output of joint-state computation across multiple 1D regime DFs.

    Returned by :func:`build_joint_states` and consumed by both
    :func:`compose_regimes` (full snapshot rendering) and
    :func:`ix.core.regimes.validate.validate_composition` (walk-forward
    backtest, only ``composite_df`` + ``composite_states`` are needed).
    """

    composite_df: pd.DataFrame
    composite_states: list[str]
    state_map: dict[tuple[str, ...], str]
    joint_combos: list[tuple[str, ...]]
    color_map: dict[str, str]
    state_descriptions: dict[str, str]
    qualified_dims: list[str]
    display_name: str
    disambiguate: bool


def build_joint_states(
    built_dfs: dict[str, pd.DataFrame],
    regs: list[RegimeRegistration],
    axis_order: list[str],
) -> JointStateBuild:
    """Compute joint states from per-axis regime DataFrames.

    Pure function: takes already-built input regime DFs (any history slice)
    and returns the cartesian-product joint state series with hard +
    smoothed joint probabilities, dominant state, conviction, and streak.

    The walk-forward validator calls this on per-month-truncated DFs to
    avoid look-ahead bias; ``compose_regimes`` calls it on full-history DFs.

    Args:
        built_dfs: ``{regime_key: built_df}`` from ``Regime.build()``.
        regs: List of registrations in the same order as ``axis_order``.
        axis_order: Sorted regime keys (defines combo ordering).

    Returns:
        :class:`JointStateBuild` containing the composite DataFrame and
        all metadata derived from the joint state space.

    Raises:
        ValueError: if input regimes have no overlapping observations or
            no usable joint observations after dropna.
    """
    all_state_lists = [reg.states for reg in regs]
    joint_combos = list(product(*all_state_lists))
    disambiguate = _has_state_collision(all_state_lists)

    def _name(combo: tuple[str, ...]) -> str:
        return _join_state_name(combo, keys=axis_order, disambiguate=disambiguate)

    composite_states = [_name(c) for c in joint_combos]
    state_map = {combo: _name(combo) for combo in joint_combos}
    input_color_maps = [reg.color_map for reg in regs]
    color_map = {
        _name(combo): _auto_color_for_combo(combo, input_color_maps, idx)
        for idx, combo in enumerate(joint_combos)
    }
    qualified_dims = [_qualified_dim_name(r) for r in regs]
    state_descriptions = {
        _name(combo): _auto_description(combo, qualified_dims)
        for combo in joint_combos
    }
    display_name = " × ".join(qualified_dims) + " (custom)"

    # Common month-end index across all input regimes
    common_index = built_dfs[axis_order[0]].index
    for k in axis_order[1:]:
        common_index = common_index.intersection(built_dfs[k].index)
    if len(common_index) == 0:
        raise ValueError(
            f"Composing {axis_order} produced no overlapping observations"
        )

    composite_df = pd.DataFrame(index=common_index)

    # Joint hard + smoothed probability for each combo (independence assumed)
    for combo in joint_combos:
        joint_name = state_map[combo]
        s_prob: pd.Series | None = None
        h_prob: pd.Series | None = None
        for k, state in zip(axis_order, combo):
            df = built_dfs[k]
            s_col = f"S_P_{state}"
            h_col = f"P_{state}"
            if s_col not in df.columns or h_col not in df.columns:
                s_prob = pd.Series(0.0, index=common_index)
                h_prob = pd.Series(0.0, index=common_index)
                break
            s_series = df[s_col].reindex(common_index)
            h_series = df[h_col].reindex(common_index)
            s_prob = s_series if s_prob is None else s_prob * s_series
            h_prob = h_series if h_prob is None else h_prob * h_series
        composite_df[f"S_P_{joint_name}"] = s_prob
        composite_df[f"P_{joint_name}"] = h_prob

    # Drop rows where any joint probability is null
    s_prob_cols = [f"S_P_{s}" for s in composite_states]
    composite_df = composite_df.dropna(subset=s_prob_cols, how="any")
    if composite_df.empty:
        raise ValueError(
            f"Composing {axis_order} produced no usable joint observations"
        )

    # H_Dominant = argmax of smoothed joint probabilities
    prob_matrix = composite_df[s_prob_cols].copy()
    prob_matrix.columns = composite_states
    composite_df["H_Dominant"] = prob_matrix.idxmax(axis=1)
    composite_df["S_Dominant"] = composite_df["H_Dominant"]
    composite_df["Dominant"] = composite_df["H_Dominant"]

    # Conviction = max smoothed joint probability * 100
    composite_df["Conviction"] = prob_matrix.max(axis=1) * 100.0

    # Months_In_Regime streak
    streak: list[int] = []
    prev = None
    cnt = 0
    for v in composite_df["H_Dominant"]:
        if v == prev:
            cnt += 1
        else:
            cnt = 1
            prev = v
        streak.append(cnt)
    composite_df["Months_In_Regime"] = streak

    return JointStateBuild(
        composite_df=composite_df,
        composite_states=composite_states,
        state_map=state_map,
        joint_combos=joint_combos,
        color_map=color_map,
        state_descriptions=state_descriptions,
        qualified_dims=qualified_dims,
        display_name=display_name,
        disambiguate=disambiguate,
    )


# ─────────────────────────────────────────────────────────────────────
# State name auto-generation
# ─────────────────────────────────────────────────────────────────────


def _has_state_collision(state_lists: list[list[str]]) -> bool:
    """True if any state name appears in 2+ input regimes.

    Used to decide whether to disambiguate joint state names with regime
    key prefixes. Credit's "Expansion" (tight spreads) and growth's
    "Expansion" (GDP rising) collide and need disambiguation.
    """
    seen: set[str] = set()
    for sl in state_lists:
        for name in sl:
            if name in seen:
                return True
            seen.add(name)
    return False


def _join_state_name(
    parts: tuple[str, ...],
    keys: list[str] | None = None,
    disambiguate: bool = False,
) -> str:
    """Join state names from N regimes into a composite name.

    >>> _join_state_name(("Expansion", "Easing"))
    'Expansion+Easing'
    >>> _join_state_name(("Expansion", "Expansion"), keys=["credit", "growth"], disambiguate=True)
    'credit:Expansion+growth:Expansion'
    """
    if disambiguate and keys is not None:
        return "+".join(f"{k}:{p}" for k, p in zip(keys, parts))
    return "+".join(parts)


# Curated mixed-state palette — distinct hues that read well on the dark
# Quant Terminal dashboard background. Used for joint states that are
# neither all-positive nor all-negative so the stacked-area Probability
# History chart never collapses two mixed states into the same color band.
_MIXED_PALETTE: tuple[str, ...] = (
    "#f59e0b",  # amber
    "#6382ff",  # electric blue (matches --primary)
    "#a855f7",  # purple
    "#ec4899",  # pink
    "#06b6d4",  # cyan
    "#84cc16",  # lime
    "#f97316",  # orange
    "#14b8a6",  # teal
    "#fb7185",  # rose
    "#8b5cf6",  # violet
    "#eab308",  # yellow
    "#10b981",  # emerald
)


def _classify_part(state: str, color_map: dict[str, str]) -> int:
    """Classify a single regime state as +1 (positive/green), -1 (negative/red), or 0.

    Uses the *source regime's* registered color_map as the source of truth —
    avoids ambiguity when the same state name means different things across
    regimes (credit_trend "Tightening" = good, liquidity "Tightening" = bad).
    """
    hex_color = color_map.get(state, "").lower()
    if hex_color in ("#22c55e", "#84cc16", "#10b981", "#22d3ee"):
        return 1   # green family
    if hex_color in ("#ef5350", "#f87171", "#dc2626"):
        return -1  # red family
    return 0


def _auto_color_for_combo(
    parts: tuple[str, ...],
    color_maps: list[dict[str, str]],
    idx: int,
) -> str:
    """Distinct color for an auto-generated joint state.

    Semantic bias preserved at the extremes:
    * All input states classified as positive (green) → green
    * All classified as negative (red) → red
    * Anything mixed → distinct hue from the curated palette, indexed by
      cartesian-product position so every mixed state lands on a unique
      color band in the stacked-area Probability History chart.
    """
    classes = [
        _classify_part(part, cm) for part, cm in zip(parts, color_maps)
    ]
    if classes and all(c == 1 for c in classes):
        return "#22c55e"  # all green — best outlook
    if classes and all(c == -1 for c in classes):
        return "#ef5350"  # all red — worst outlook
    return _MIXED_PALETTE[idx % len(_MIXED_PALETTE)]


def _qualified_dim_name(reg: RegimeRegistration) -> str:
    """Disambiguated, human-readable dimension name for a 1D regime.

    Multiple regimes can share an internal dimension name (e.g. dollar_level
    and credit_level both register `dimensions=["Level"]`). When composing,
    that collision means the legend shows ambiguous "Level" / "Trend" labels
    AND the underlying composite_df columns silently overwrite each other.
    Qualifying with the regime's display_name prefix fixes both:

        dollar_level  → "Dollar Level"   (was "Level")
        credit_level  → "Credit Level"   (was "Level")
        dollar_trend  → "Dollar Trend"   (was "Trend")
        credit_trend  → "Credit Trend"   (was "Trend")
        growth        → "Growth"         (unchanged — single-word display)
        yield_curve   → "Yield Curve"    (was "YieldCurve")

    Heuristic: take the display_name up to the first " (" — that strips
    the "(Strong × Weak)" state suffix every regime registers.
    """
    return reg.display_name.split(" (")[0].strip()


def _auto_description(parts: tuple[str, ...], axis_names: list[str]) -> str:
    """Build a one-line description from axis × state combination."""
    pieces: list[str] = []
    SYMBOL = {
        "Expansion":    "↑",
        "Contraction":  "↓",
        "Rising":       "↑",
        "Falling":      "↓",
        "Easing":       "↑",
        "Tightening":   "↓",
    }
    for axis, state in zip(axis_names, parts):
        sym = SYMBOL.get(state, "")
        pieces.append(f"{axis} {sym}")
    return " · ".join(pieces)


# ─────────────────────────────────────────────────────────────────────
# Main composition entry point
# ─────────────────────────────────────────────────────────────────────


def compose_regimes(
    keys: list[str],
    params: dict | None = None,
) -> dict:
    """Compose 2+ single-metric regimes into a custom composite snapshot.

    Args:
        keys: List of regime keys to compose. Must all be 1D regimes
              (category="axis" or "phase"). Pre-built composites cannot
              be re-composed.
        params: Build params for each regime. Defaults to first regime's defaults.

    Returns:
        Snapshot dict with the same shape as ``regime_snapshot`` JSONB columns:
        ``current_state``, ``timeseries``, ``asset_analytics``, ``meta``.
        Plus a synthesized ``model`` block (display_name, states, color_map, etc.)
        for the frontend.

    Raises:
        ValueError: if fewer than 2 keys, any key is a pre-built composite,
                    or any regime fails to build.
    """
    if len(keys) < 2:
        raise ValueError(f"Need at least 2 regimes to compose, got {len(keys)}")

    # Normalize order so growth+inflation == inflation+growth
    keys = sorted(set(keys))

    # Validate all are 1D (axis or phase)
    regs: list[RegimeRegistration] = []
    for k in keys:
        try:
            r = get_regime(k)
        except KeyError as e:
            raise ValueError(f"Regime '{k}' not registered") from e
        if r.category not in ("axis", "phase"):
            raise ValueError(
                f"Cannot compose regime '{k}' (category={r.category}). "
                f"Only single-metric (axis or phase) regimes are composable."
            )
        if r.regime_class is None:
            raise ValueError(
                f"Regime '{k}' has no regime_class — cannot build for composition"
            )
        regs.append(r)

    # Build params from first regime if not provided
    if params is None:
        params = regs[0].default_params.copy()

    # ── Build each input regime's DataFrame ─────────────────────────
    built_dfs: dict[str, pd.DataFrame] = {}
    built_instances: dict[str, Regime] = {}
    for reg in regs:
        regime: Regime = reg.regime_class()
        df = regime.build(
            z_window=params.get("z_window", 96),
            sensitivity=params.get("sensitivity", 2.0),
            smooth_halflife=params.get("smooth_halflife", 2),
            confirm_months=params.get("confirm_months", 3),
        )
        if df.empty:
            raise ValueError(f"Regime '{reg.key}' built an empty DataFrame")
        built_dfs[reg.key] = df
        built_instances[reg.key] = regime

    # ── Joint state computation (extracted helper, reused by validator) ──
    # The composer is intentionally agnostic — it never assigns
    # "named" labels like Goldilocks/Reflation/etc. Every combination is
    # treated identically: states are just `axis1state+axis2state`.
    axis_order = keys
    joint = build_joint_states(built_dfs, regs, axis_order)
    composite_df = joint.composite_df
    composite_states = joint.composite_states
    state_map = joint.state_map
    joint_combos = joint.joint_combos
    color_map = joint.color_map
    state_descriptions = joint.state_descriptions
    qualified_dims = joint.qualified_dims
    axis_display_names = qualified_dims
    display_name = joint.display_name
    s_prob_cols = [f"S_P_{s}" for s in composite_states]

    # ── Multi-horizon Markov forward projections ──────────────────
    # Build a transition matrix from the historical H_Dominant sequence
    # (with Laplace smoothing), then project the latest smoothed joint
    # probability vector forward at 1, 3, 6, and 12 month horizons by
    # raising the transition matrix to the corresponding power.
    #
    # 1-step alone is uninformative for sticky regimes (the projection
    # is essentially the current distribution). Showing the full curve
    # 1M → 3M → 6M → 12M reveals the regime's natural drift toward its
    # steady-state distribution and lets the frontend show meaningful
    # delta arrows.
    dom_seq = [
        v for v in composite_df["H_Dominant"].dropna()
        if v in composite_states
    ]
    forward_probabilities: dict[str, float] | None = None
    forward_horizons: dict[int, dict[str, float]] | None = None
    if len(dom_seq) > 20:
        n = len(composite_states)
        idx = {s: i for i, s in enumerate(composite_states)}
        counts_np = np.ones((n, n), dtype=np.float64)  # Laplace +1
        for a, b in zip(dom_seq[:-1], dom_seq[1:]):
            counts_np[idx[a], idx[b]] += 1
        tmat_np = counts_np / counts_np.sum(axis=1, keepdims=True)

        last_row = composite_df.iloc[-1]
        cur_p = np.array([
            _safe_float(last_row.get(f"S_P_{s}"), 0.0) or 0.0
            for s in composite_states
        ])
        cur_total = cur_p.sum()
        if cur_total > 1e-9:
            cur_p = cur_p / cur_total

        forward_horizons = {}
        for h in (1, 3, 6, 12):
            p_h = cur_p @ np.linalg.matrix_power(tmat_np, h)
            t = p_h.sum()
            if t > 1e-9:
                p_h = p_h / t
            forward_horizons[h] = {
                s: float(p_h[i]) for i, s in enumerate(composite_states)
            }
        # Backwards compat — frontend still reads forward_probabilities
        # for the 1M projection, plus the new forward_horizons block.
        forward_probabilities = forward_horizons[1]

    # Add dimension columns for each axis (state name + Z + P)
    # so that current_state can render dimension cards.
    # The composite_df columns are written under the QUALIFIED name
    # ("Dollar Level_Z" not "Level_Z") so that composing dollar_level +
    # credit_level — both with internal dim_name="Level" — doesn't silently
    # overwrite the first axis with the second.
    for k in axis_order:
        reg = next(r for r in regs if r.key == k)
        src_dim = reg.dimensions[0] if reg.dimensions else reg.name.title()
        qual_dim = _qualified_dim_name(reg)
        src_df = built_dfs[k]
        src_z = f"{src_dim}_Z"
        src_p = f"{src_dim}_P"
        if src_z in src_df.columns:
            composite_df[f"{qual_dim}_Z"] = src_df[src_z].reindex(
                composite_df.index, method="ffill"
            )
        if src_p in src_df.columns:
            composite_df[f"{qual_dim}_P"] = src_df[src_p].reindex(
                composite_df.index, method="ffill"
            )

    # ── Asset universe = union of all input regimes ────────────────
    asset_tickers: dict[str, str] = {}
    for reg in regs:
        if reg.asset_tickers:
            asset_tickers.update(reg.asset_tickers)
    if not asset_tickers:
        asset_tickers = DEFAULT_ASSET_TICKERS

    # ── Asset analytics ────────────────────────────────────────────
    try:
        asset_analytics = compute_asset_analytics(
            composite_df,
            states=composite_states,
            tickers=asset_tickers,
        )
    except Exception as exc:
        log.warning("Compose: asset analytics failed: %s", exc)
        asset_analytics = None

    # ── Build the synthesized model metadata ───────────────────────
    # `dimensions` and `dimension_colors` use the QUALIFIED dim names
    # ("Dollar Level", "Credit Trend", "Yield Curve") so the History tab
    # legend, the Methodology tab, and the CurrentStateTab dim cards all
    # show unambiguous labels — and so dollar_level + credit_level no
    # longer collapses both color entries into a single ambiguous "Level".
    composite_key = "compose:" + "+".join(keys)
    qual_by_key = {reg.key: _qualified_dim_name(reg) for reg in regs}
    composite_dimensions = [qual_by_key[k] for k in axis_order]
    composite_dimension_colors: dict[str, str] = {}
    for reg in regs:
        qual = qual_by_key[reg.key]
        # Each 1D regime registers exactly one dimension_colors entry — pull
        # its hex value (regardless of internal key) and re-index under the
        # qualified name.
        if reg.dimension_colors:
            composite_dimension_colors[qual] = next(iter(reg.dimension_colors.values()))
    model = {
        "key": composite_key,
        "display_name": display_name,
        "description": (
            f"Custom composition of {', '.join(keys)} — joint state assignment "
            f"({len(composite_states)} states)"
        ),
        "states": composite_states,
        "dimensions": composite_dimensions,
        "has_strategy": False,
        "category": "composite",
        "color_map": color_map,
        "dimension_colors": composite_dimension_colors,
        "state_descriptions": state_descriptions,
        "default_params": params,
    }

    # ── Serialize current_state (latest row) ───────────────────────
    last = composite_df.iloc[-1]
    last_date = composite_df.index[-1]
    dom = str(last["H_Dominant"])

    # Pull top driving indicators per axis from each input regime's df.
    # We use the regime instance's authoritative `_dimension_prefixes()`
    # map (e.g. {"Level": "lv_"}) instead of guessing the first letter,
    # which is wrong for Level/Trend axes. We also use the input regime's
    # *own* H_Dominant state as the direction label so credit_level shows
    # "Tight"/"Wide" (its declared states), not a made-up "High"/"Low".
    #
    # We also build `input_states[k]` so the frontend's AxisDock can show
    # each constituent regime at the JOINT state's date instead of the
    # standalone snapshot's latest date — otherwise inflation might show
    # April values while the dim card shows March values (intersection
    # date), confusing users with mismatched numbers.
    dim_data: dict[str, dict] = {}
    input_states: dict[str, dict] = {}
    for k in axis_order:
        reg = next(r for r in regs if r.key == k)
        instance = built_instances[k]
        src_df = built_dfs[k]
        # Use the input regime's row at the composite's last common date
        # — NOT iloc[-1], which may be a later month that doesn't align
        # with the intersection-based composite_df.
        if last_date in src_df.index:
            src_last = src_df.loc[last_date]
        else:
            src_last = src_df.iloc[-1]
        dim_name = reg.dimensions[0] if reg.dimensions else reg.name.title()
        qual_dim = qual_by_key[k]
        # Pull from the qualified column we wrote into composite_df above
        z = _safe_float(last.get(f"{qual_dim}_Z"), 0.0) or 0.0

        # Direction label = the input regime's per-axis state derived
        # from the SAME smoothed probabilities that the joint state was
        # built from (argmax of S_P_<state> at last_date). Using
        # H_Dominant directly would disagree with the joint name when
        # confirmation lag desyncs the input regime's hard state from
        # its own soft probabilities.
        s_prob_pairs = [
            (s, _safe_float(src_last.get(f"S_P_{s}"), 0.0) or 0.0)
            for s in reg.states
        ]
        s_prob_pairs = [(s, pv) for s, pv in s_prob_pairs if pv > 0]
        if s_prob_pairs:
            direction, dom_prob = max(s_prob_pairs, key=lambda x: x[1])
        else:
            direction = "Positive" if z >= 0 else "Negative"
            dom_prob = 0.5

        # Probability shown should match what users see on the standalone
        # regime card at the top of the dashboard. We use the input regime's
        # smoothed dominant-state probability (S_P_<direction>) instead of
        # the raw `<dim>_P` continuous direction probability — they measure
        # different things and confuse users when they don't agree.
        p = dom_prob

        # Pull indicator components from the input regime's last row
        # using its authoritative prefix map. Skip moving-average dupes
        # that the standalone serializers also drop (e.g. g_Claims4WMA).
        prefixes = instance._dimension_prefixes()
        prefix = prefixes.get(dim_name, dim_name[0].lower() + "_")
        component_cols = [
            c for c in src_df.columns
            if c.startswith(prefix) and c != "g_Claims4WMA"
        ]
        components: list[dict] = []
        for col in component_cols:
            val = _safe_float(src_last.get(col))
            if val is not None:
                components.append({"name": col[len(prefix):], "z": val})
        # Sort by |z| descending — strongest drivers first
        components.sort(key=lambda c: abs(c["z"]), reverse=True)

        # Key dim_data by the QUALIFIED name so the frontend's
        # CurrentStateTab dim cards (which iterate model.dimensions and look
        # up state.dimensions[dim]) find the right card and don't collide
        # when composing dollar_level + credit_level.
        dim_data[qual_dim] = {
            "z": z,
            "p": p,
            "direction": direction,
            "score": int(sum(1 for c in components if c["z"] >= 0)),
            "total": len(components),
            "components": components,
        }

        # Walk back from last_date counting consecutive months where the
        # smoothed argmax stays equal to the current `direction`. This
        # gives a months-in-state count consistent with the value the
        # dim card shows (P_max at last_date), instead of the standalone
        # H_Dominant streak which can be desynced by confirmation lag.
        months_in_state = 0
        try:
            history_idx = src_df.loc[:last_date].index
            for ts in reversed(history_idx):
                row = src_df.loc[ts]
                ts_pairs = [
                    (s, _safe_float(row.get(f"S_P_{s}"), 0.0) or 0.0)
                    for s in reg.states
                ]
                ts_valid = [(s, pv) for s, pv in ts_pairs if pv > 0]
                if not ts_valid:
                    break
                top_state = max(ts_valid, key=lambda x: x[1])[0]
                if top_state == direction:
                    months_in_state += 1
                else:
                    break
        except Exception:
            months_in_state = 0

        # Per-dimension Z history for AxisDock sparkline (last 24 months)
        # plus a simple 3-month acceleration (slope of Z over the trailing
        # window, in z-units). Always populated regardless of which axes are
        # in the composition so the frontend can render Cycle Acceleration
        # for any composite, not just growth+inflation.
        dim_z_series = composite_df.get(f"{qual_dim}_Z")
        z_history: list[float] = []
        z_accel: float | None = None
        if dim_z_series is not None and not dim_z_series.dropna().empty:
            recent = dim_z_series.dropna().tail(24)
            z_history = [float(v) for v in recent.values]
            if len(recent) >= 4:
                tail = recent.tail(3)
                z_accel = float(tail.iloc[-1] - tail.iloc[0])
        dim_data[qual_dim]["history"] = z_history
        dim_data[qual_dim]["acceleration"] = z_accel

        input_states[k] = {
            "dominant": direction,
            "dominant_probability": dom_prob,
            "months_in_regime": months_in_state,
            "date": last_date.strftime("%Y-%m"),
            "conviction": dom_prob * 100.0,
            "z_history": z_history,
            "z_acceleration": z_accel,
        }

    # Probabilities map: joint state name → smoothed joint probability
    probabilities = {
        s: _safe_float(last.get(f"S_P_{s}"), 0.0) or 0.0
        for s in composite_states
    }

    # ── Regime stats for current state ──────────────────────────────
    # Frequency: how often this exact joint state has occurred since the
    # composite has data. Avg duration: average run length when it appears.
    # Both come from the historical H_Dominant column we already built.
    h_series = composite_df["H_Dominant"].dropna()
    total_months = int(len(h_series))
    cur_state_months = int((h_series == dom).sum())
    cur_state_pct = (cur_state_months / total_months * 100) if total_months > 0 else 0.0

    # Average run length: walk through H_Dominant, collect run lengths
    # for the current state, take the mean.
    run_lengths: list[int] = []
    cur_run = 0
    cur_val: str | None = None
    for v in h_series:
        if v == cur_val:
            cur_run += 1
        else:
            if cur_val == dom and cur_run > 0:
                run_lengths.append(cur_run)
            cur_val = v
            cur_run = 1
    if cur_val == dom and cur_run > 0:
        run_lengths.append(cur_run)
    avg_run_months = (sum(run_lengths) / len(run_lengths)) if run_lengths else 0.0
    n_occurrences = len(run_lengths)

    # Best/worst asset historically while in this state, and the
    # asset-level Cohen's d that gives the regime its statistical
    # backbone. All sourced from already-computed asset_analytics.
    best_asset: dict | None = None
    worst_asset: dict | None = None
    top_separation: dict | None = None
    if asset_analytics:
        per = asset_analytics.get("per_regime_stats", {}).get(dom, {})
        assets = [a for a in per.get("assets", []) if a.get("sharpe") is not None]
        if assets:
            best = max(assets, key=lambda a: a["sharpe"])
            worst = min(assets, key=lambda a: a["sharpe"])
            best_asset = {
                "ticker": best["ticker"],
                "ann_ret": best.get("ann_ret"),
                "sharpe": best.get("sharpe"),
                "win_rate": best.get("win_rate"),
                "max_dd": best.get("max_dd"),
            }
            worst_asset = {
                "ticker": worst["ticker"],
                "ann_ret": worst.get("ann_ret"),
                "sharpe": worst.get("sharpe"),
                "win_rate": worst.get("win_rate"),
                "max_dd": worst.get("max_dd"),
            }
        # Strongest regime separation across the universe (max |Cohen's d|)
        sep_map = asset_analytics.get("regime_separation", {}) or {}
        candidates = [
            (t, s) for t, s in sep_map.items()
            if s and s.get("cohens_d") is not None
        ]
        if candidates:
            best_t, best_s = max(candidates, key=lambda x: abs(x[1]["cohens_d"]))
            top_separation = {
                "ticker": best_t,
                "cohens_d": best_s.get("cohens_d"),
                "p_value": best_s.get("p_value"),
                "best_state": best_s.get("best_state"),
                "worst_state": best_s.get("worst_state"),
            }

    regime_stats = {
        "occurrences": n_occurrences,
        "months_in_state": cur_state_months,
        "total_months": total_months,
        "frequency_pct": cur_state_pct,
        "avg_run_months": avg_run_months,
        "current_run_months": int(last.get("Months_In_Regime", 1) or 1),
        "best_asset": best_asset,
        "worst_asset": worst_asset,
        "top_separation": top_separation,
    }

    # ── Decision Card ─────────────────────────────────────────────
    # Synthesizes the raw stats into a single PM-actionable verdict.
    # Mirrors the ix-regime-combiner skill's Decision Card logic so the
    # dashboard surfaces the same conclusion the offline search would.
    #
    #   verdict     RISK-ON | RISK-OFF | MIXED | NEUTRAL
    #   tilt_long   top 2 assets in current state by Sharpe
    #   tilt_short  bottom 2 assets in current state by Sharpe
    #   gates       DC1 (separation), DC2 (persistence), DC3 (conviction),
    #               DC4 (sample size)
    #   watch       which input axis the 12M Markov suggests will flip
    cur_conviction_val = _safe_float(last.get("Conviction"), 0.0) or 0.0
    decision_card: dict | None = None
    if asset_analytics:
        # Verdict: rank current state vs all states by primary target's
        # ann_ret. Top tercile = RISK-ON, bottom = RISK-OFF, middle = MIXED.
        primary_ticker: str | None = None
        sep_map_dc = asset_analytics.get("regime_separation", {}) or {}
        sep_candidates = [
            (t, s) for t, s in sep_map_dc.items()
            if s and s.get("cohens_d") is not None
        ]
        if sep_candidates:
            primary_ticker = max(
                sep_candidates, key=lambda x: abs(x[1]["cohens_d"])
            )[0]

        per_state_returns: list[tuple[str, float]] = []
        if primary_ticker:
            for st_name, st_stats in asset_analytics.get(
                "per_regime_stats", {}
            ).items():
                for asset_row in st_stats.get("assets", []):
                    if (
                        asset_row.get("ticker") == primary_ticker
                        and asset_row.get("ann_ret") is not None
                    ):
                        per_state_returns.append(
                            (st_name, float(asset_row["ann_ret"]))
                        )
                        break

        verdict = "NEUTRAL"
        if per_state_returns and len(per_state_returns) >= 2:
            ranked = sorted(per_state_returns, key=lambda x: x[1], reverse=True)
            n_states_ranked = len(ranked)
            third = max(1, n_states_ranked // 3)
            top_set = {s for s, _ in ranked[:third]}
            bot_set = {s for s, _ in ranked[-third:]}
            if dom in top_set:
                verdict = "RISK-ON"
            elif dom in bot_set:
                verdict = "RISK-OFF"
            else:
                verdict = "MIXED"

        # Tilt: best/worst assets in current state by Sharpe
        tilt_long: list[str] = []
        tilt_short: list[str] = []
        cur_per = asset_analytics.get("per_regime_stats", {}).get(dom, {})
        cur_assets = [
            a for a in cur_per.get("assets", [])
            if a.get("sharpe") is not None
        ]
        if cur_assets:
            ranked_assets = sorted(
                cur_assets, key=lambda a: a["sharpe"], reverse=True
            )
            tilt_long = [a["ticker"] for a in ranked_assets[:2]]
            tilt_short = [a["ticker"] for a in ranked_assets[-2:][::-1]]

        # DC gates
        dc1_pass = bool(
            top_separation
            and top_separation.get("cohens_d") is not None
            and abs(top_separation["cohens_d"]) >= 0.40
        )
        dc2_pass = avg_run_months >= 4.0
        dc3_pass = cur_conviction_val >= 40.0
        dc4_pass = cur_state_months >= 30

        # Watch: input axis most likely to flip per 12M Markov
        watch: list[dict] = []
        if forward_horizons and 12 in forward_horizons:
            fwd_12 = forward_horizons[12]
            cur_p_dom = probabilities.get(dom, 0.0)
            fwd_p_dom = fwd_12.get(dom, 0.0)
            # Significant decay = forward 12M probability < 70% of current
            if cur_p_dom > 0 and fwd_p_dom < cur_p_dom * 0.70:
                next_state = max(fwd_12.items(), key=lambda x: x[1])[0]
                if next_state != dom:
                    cur_parts = dom.split("+")
                    next_parts = next_state.split("+")
                    if len(cur_parts) == len(next_parts):
                        for i, (cp, npart) in enumerate(zip(cur_parts, next_parts)):
                            if cp != npart and i < len(axis_display_names):
                                watch.append({
                                    "axis": axis_display_names[i],
                                    "from": cp,
                                    "to": npart,
                                })

        decision_card = {
            "verdict": verdict,
            "primary_ticker": primary_ticker,
            "tilt_long": tilt_long,
            "tilt_short": tilt_short,
            "gates": {
                "dc1_separation": dc1_pass,
                "dc2_persistence": dc2_pass,
                "dc3_conviction": dc3_pass,
                "dc4_sample_size": dc4_pass,
            },
            "watch": watch,
        }

    current_state = {
        "date": last_date.strftime("%Y-%m"),
        "dominant": dom,
        "dominant_probability": probabilities.get(dom, 0.0),
        "confirmed": dom,
        "conviction": cur_conviction_val,
        "months_in_regime": int(last.get("Months_In_Regime", 1) or 1),
        "probabilities": probabilities,
        "forward_probabilities": forward_probabilities,
        "forward_horizons": forward_horizons,
        "decision_card": decision_card,
        "regime_stats": regime_stats,
        "dimensions": dim_data,
        "input_states": input_states,
    }

    # ── Serialize timeseries (post-2000) ───────────────────────────
    df_2000 = composite_df.loc["2000-01-01":].copy()
    dates = _dates_to_list(df_2000.index)

    composites_ts: dict = {}
    for k in axis_order:
        # Read from the QUALIFIED column we wrote into composite_df above so
        # the History tab's `ts.composites['Dollar Level_Z']` lookup keyed
        # off `model.dimensions` succeeds.
        qual_dim = qual_by_key[k]
        z_col = f"{qual_dim}_Z"
        if z_col in df_2000.columns:
            composites_ts[z_col] = _series_to_list(df_2000[z_col])

    probs: dict = {}
    smoothed_probs: dict = {}
    for s in composite_states:
        if f"P_{s}" in df_2000.columns:
            probs[s] = _series_to_list(df_2000[f"P_{s}"])
            smoothed_probs[s] = _series_to_list(df_2000[f"S_P_{s}"])

    timeseries = {
        "dates": dates,
        "composites": composites_ts,
        "probabilities": probs,
        "smoothed_probabilities": smoothed_probs,
        "dominant": (
            df_2000["S_Dominant"].fillna("").astype(str).tolist()
            if "S_Dominant" in df_2000.columns else []
        ),
        "confirmed": (
            df_2000["H_Dominant"].fillna("").astype(str).tolist()
            if "H_Dominant" in df_2000.columns else []
        ),
        "conviction": (
            _series_to_list(df_2000["Conviction"])
            if "Conviction" in df_2000.columns else []
        ),
        "indicators": {},  # composite has no individual indicators of its own
    }

    # ── Build the response payload ─────────────────────────────────
    return {
        "model": model,
        "current_state": current_state,
        "timeseries": timeseries,
        "asset_analytics": asset_analytics,
        "meta": {
            "model_name": display_name,
            "description": model["description"],
            "states": composite_states,
            "dimensions": model["dimensions"],
            "color_map": color_map,
            "dimension_colors": model["dimension_colors"],
            "methodology": {
                "composition": "joint state assignment from input regimes' H_Dominant",
                "state_naming": (
                    "mechanical 'Axis1State+Axis2State' from cartesian product "
                    "of input regimes' states"
                ),
                "asset_universe": "union of input regimes' asset_tickers",
                "input_regimes": ", ".join(keys),
            },
        },
        # Empty placeholders to match the standard snapshot shape
        "strategy": None,
    }
