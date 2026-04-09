"""Parameter sensitivity audit for registered regimes.

Sweeps the 4 core regime build parameters (``z_window``, ``sensitivity``,
``smooth_halflife``, ``confirm_months``) around each regime's registered
defaults and measures how much the walk-forward forward-return spread
changes. A **fragile** regime whose Tier-1 spread collapses under small
parameter perturbations has almost certainly been overfit to the default
tuning and should be treated as a research prototype, not production.

The audit runs :func:`ix.core.regimes.validate.validate_composition` for
every grid point, so every measurement is walk-forward and carries no
look-ahead bias.

Example
-------
    >>> from ix.core.regimes.sensitivity import audit_regime_sensitivity
    >>> result = audit_regime_sensitivity(
    ...     "growth",
    ...     target="SPY US EQUITY:PX_LAST",
    ...     horizon_months=3,
    ... )
    >>> print(result.summary())
    growth → SPY US EQUITY:PX_LAST @ 3M
      default spread : 5.07%
      grid median    : 4.83%
      grid min/max   : 3.12% / 5.71%
      grid std       : 0.58pp
      fragile cells  : 3 / 16  (19%)
      verdict        : robust

Fragility verdict
-----------------
* **robust**    — ≥ 80% of grid cells hit ≥ 80% of the default spread AND
                  no grid cell flips sign vs the default.
* **sensitive** — the spread stays positive everywhere but ≥ 20% of cells
                  fall below 80% of the default.
* **fragile**   — at least one grid cell flips sign OR the grid median is
                  below half the default spread. Treat as unreliable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product
from typing import Optional, Sequence

import numpy as np
import pandas as pd

from .registry import get_regime
from .validate import validate_composition


# ─────────────────────────────────────────────────────────────────────
# Result container
# ─────────────────────────────────────────────────────────────────────


@dataclass
class SensitivityAuditResult:
    """Parameter-sensitivity audit output for a single regime + target.

    The ``grid`` DataFrame has one row per ``(z_window, sensitivity,
    smooth_halflife, confirm_months)`` combination and columns for the
    walk-forward spread, Cohen's d, Welch p, and best/worst state names.
    Grid points where the validator failed are recorded with ``NaN``.
    """

    regime_key: str
    target: str
    horizon_months: int
    default_params: dict
    default_spread: Optional[float]
    grid: pd.DataFrame = field(default_factory=pd.DataFrame)
    verdict: str = "unknown"

    # ── Derived stats ────────────────────────────────────────────────

    @property
    def n_total(self) -> int:
        return int(len(self.grid))

    @property
    def n_ok(self) -> int:
        if "spread" not in self.grid.columns:
            return 0
        return int(self.grid["spread"].notna().sum())

    @property
    def grid_median_spread(self) -> Optional[float]:
        if "spread" not in self.grid.columns or self.grid["spread"].dropna().empty:
            return None
        return float(self.grid["spread"].median())

    @property
    def grid_min_spread(self) -> Optional[float]:
        if "spread" not in self.grid.columns or self.grid["spread"].dropna().empty:
            return None
        return float(self.grid["spread"].min())

    @property
    def grid_max_spread(self) -> Optional[float]:
        if "spread" not in self.grid.columns or self.grid["spread"].dropna().empty:
            return None
        return float(self.grid["spread"].max())

    @property
    def grid_std_spread(self) -> Optional[float]:
        if "spread" not in self.grid.columns or self.grid["spread"].dropna().empty:
            return None
        return float(self.grid["spread"].std(ddof=0))

    @property
    def fragile_cells(self) -> int:
        """Number of grid cells whose spread is below 80% of the default."""
        if self.default_spread is None or self.default_spread <= 0:
            return 0
        threshold = 0.8 * self.default_spread
        return int((self.grid["spread"] < threshold).sum())

    @property
    def sign_flips(self) -> int:
        """Grid cells whose spread has the opposite sign from the default."""
        if self.default_spread is None or self.default_spread == 0:
            return 0
        default_sign = np.sign(self.default_spread)
        return int(((np.sign(self.grid["spread"]) * default_sign) < 0).sum())

    def summary(self) -> str:
        """Human-readable one-screen summary of the audit."""
        lines = [
            f"{self.regime_key} → {self.target} @ {self.horizon_months}M",
            f"  default spread : {self.format_pct(self.default_spread)}",
            f"  grid median    : {self.format_pct(self.grid_median_spread)}",
            f"  grid min/max   : {self.format_pct(self.grid_min_spread)} / "
            f"{self.format_pct(self.grid_max_spread)}",
            f"  grid std       : {self.format_pp(self.grid_std_spread)}",
            f"  fragile cells  : {self.fragile_cells} / {self.n_total}  "
            f"({self.format_ratio(self.fragile_cells, self.n_total)})",
            f"  sign flips     : {self.sign_flips} / {self.n_total}",
            f"  grid coverage  : {self.n_ok} / {self.n_total} cells succeeded",
            f"  verdict        : {self.verdict}",
        ]
        return "\n".join(lines)

    @staticmethod
    def format_pct(v: Optional[float]) -> str:
        """Format a decimal fraction as a percentage string (e.g. 0.085 → "8.50%")."""
        return "n/a" if v is None or not np.isfinite(v) else f"{v * 100:.2f}%"

    @staticmethod
    def format_pp(v: Optional[float]) -> str:
        """Format a decimal fraction as percentage-points (e.g. 0.006 → "0.60pp")."""
        return "n/a" if v is None or not np.isfinite(v) else f"{v * 100:.2f}pp"

    @staticmethod
    def format_ratio(num: int, den: int) -> str:
        """Format ``num / den`` as a percentage string (e.g. 4 / 16 → "25%")."""
        if den == 0:
            return "0%"
        return f"{100 * num / den:.0f}%"


# ─────────────────────────────────────────────────────────────────────
# Grid construction
# ─────────────────────────────────────────────────────────────────────


def _default_grid(defaults: dict, fraction: float = 0.25) -> dict[str, list]:
    """Build a ±fraction grid around each of the 4 core build params.

    The ``z_window`` and ``smooth_halflife`` params are integers; the grid
    rounds to the nearest integer and deduplicates. ``sensitivity`` is a
    float; the grid uses 3 points (low / mid / high). ``confirm_months``
    uses 3 integer points (mid-1 / mid / mid+1 or a wider step if the
    default is large).
    """
    z = int(defaults.get("z_window", 96))
    s = float(defaults.get("sensitivity", 2.0))
    h = int(defaults.get("smooth_halflife", 2))
    c = int(defaults.get("confirm_months", 3))

    z_grid = sorted({max(12, int(round(z * (1 - fraction)))), z,
                     int(round(z * (1 + fraction)))})
    s_grid = sorted({round(s * (1 - fraction), 3), round(s, 3),
                     round(s * (1 + fraction), 3)})
    h_grid = sorted({max(1, h - 1), h, h + 1})
    c_grid = sorted({max(1, c - 1), c, c + 1})

    return {
        "z_window": z_grid,
        "sensitivity": s_grid,
        "smooth_halflife": h_grid,
        "confirm_months": c_grid,
    }


# ─────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────


def audit_regime_sensitivity(
    regime_key: str,
    target: str,
    horizon_months: int,
    *,
    fraction: float = 0.25,
    grid_override: Optional[dict[str, Sequence]] = None,
    train_window: int = 120,
    exclude_indicators: Optional[set[str]] = None,
    quiet: bool = True,
) -> SensitivityAuditResult:
    """Run a parameter-sensitivity audit for a single regime vs a target.

    Sweeps the 4 core build parameters around the regime's registered
    defaults (by default ±25% on ``z_window`` and ``sensitivity``, ±1 on
    the integer smoothing/confirmation counts) and runs
    :func:`validate_composition` at every grid point. The walk-forward
    forward-return spread is recorded per cell and summarized into a
    verdict.

    Args:
        regime_key: Registered regime key (must be a 1D axis or phase
            regime — composites are rejected upstream by the validator).
        target: DB code for the forward-return target (e.g.
            ``"SPY US EQUITY:PX_LAST"``).
        horizon_months: Forward-return horizon.
        fraction: Fractional perturbation applied to ``z_window`` and
            ``sensitivity``. Default 0.25 (±25%). Smoothing and
            confirmation counts use ±1 step regardless of this value.
        grid_override: Replace the automatic grid with an explicit
            ``{param: [values]}`` dict. Any missing param falls back to
            the registered default.
        train_window: Walk-forward warmup window passed through to
            :func:`validate_composition`. Default 120 months.
        exclude_indicators: Indicators to drop from the regime composite
            when the target is one of its own classifiers (e.g. drop
            ``i_WTI`` when auditing the inflation regime against WTI).
        quiet: Suppress per-cell warnings/prints. Default True.

    Returns:
        :class:`SensitivityAuditResult` with a full grid DataFrame and a
        verdict string (``"robust"``, ``"sensitive"``, ``"fragile"``).
    """
    reg = get_regime(regime_key)
    defaults = dict(reg.default_params) if reg.default_params else {}

    # ── Build param grid ─────────────────────────────────────────────
    grid_spec = _default_grid(defaults, fraction=fraction)
    if grid_override:
        for k, v in grid_override.items():
            grid_spec[k] = list(v)

    combos = list(product(
        grid_spec["z_window"],
        grid_spec["sensitivity"],
        grid_spec["smooth_halflife"],
        grid_spec["confirm_months"],
    ))

    # ── Default-params baseline ──────────────────────────────────────
    default_result = None
    try:
        default_result = validate_composition(
            [regime_key],
            target,
            horizon_months,
            train_window=train_window,
            params=defaults,
            exclude_indicators=exclude_indicators,
        )
    except Exception as exc:
        if not quiet:
            print(f"[{regime_key}] default params failed: {exc}")

    default_spread = default_result.spread if default_result else None

    # ── Grid sweep ───────────────────────────────────────────────────
    rows: list[dict] = []
    for z, s, h, c in combos:
        params = dict(defaults)
        params.update(
            z_window=int(z),
            sensitivity=float(s),
            smooth_halflife=int(h),
            confirm_months=int(c),
        )
        row: dict = {
            "z_window": int(z),
            "sensitivity": float(s),
            "smooth_halflife": int(h),
            "confirm_months": int(c),
            "spread": np.nan,
            "cohens_d": np.nan,
            "welch_p": np.nan,
            "best_state": None,
            "worst_state": None,
        }
        try:
            res = validate_composition(
                [regime_key],
                target,
                horizon_months,
                train_window=train_window,
                params=params,
                exclude_indicators=exclude_indicators,
            )
            row["spread"] = res.spread if res.spread is not None else np.nan
            row["cohens_d"] = res.cohens_d if res.cohens_d is not None else np.nan
            row["welch_p"] = res.welch_p if res.welch_p is not None else np.nan
            row["best_state"] = res.best_state
            row["worst_state"] = res.worst_state
        except Exception as exc:
            if not quiet:
                print(f"[{regime_key}] {params} failed: {exc}")
        rows.append(row)

    grid_df = pd.DataFrame(rows)

    # ── Verdict ──────────────────────────────────────────────────────
    verdict = _verdict(default_spread, grid_df)

    return SensitivityAuditResult(
        regime_key=regime_key,
        target=target,
        horizon_months=horizon_months,
        default_params=defaults,
        default_spread=default_spread,
        grid=grid_df,
        verdict=verdict,
    )


# ─────────────────────────────────────────────────────────────────────
# Verdict classifier
# ─────────────────────────────────────────────────────────────────────


def _verdict(default_spread: Optional[float], grid: pd.DataFrame) -> str:
    """Classify an audit as robust / sensitive / fragile."""
    if default_spread is None or not np.isfinite(default_spread):
        return "unknown"
    if grid.empty or "spread" not in grid.columns:
        return "unknown"
    spreads = grid["spread"].dropna()
    if spreads.empty:
        return "unknown"

    default_sign = np.sign(default_spread)
    sign_flips = int(((np.sign(spreads) * default_sign) < 0).sum())
    median = float(spreads.median())

    # Fragile: sign instability OR the grid median collapses below half
    # the default spread's magnitude.
    if sign_flips > 0:
        return "fragile"
    if abs(median) < 0.5 * abs(default_spread):
        return "fragile"

    # Robust: ≥ 80% of grid cells hit ≥ 80% of the default spread
    threshold = 0.8 * default_spread
    hit_rate = float((spreads >= threshold).mean()) if default_spread > 0 \
        else float((spreads <= threshold).mean())
    if hit_rate >= 0.80:
        return "robust"
    return "sensitive"
