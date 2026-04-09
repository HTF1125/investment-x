"""Run parameter-sensitivity audit on every registered regime.

Each regime is tested against its declared (target, horizon) from the
registration description with a compact 2^4 = 16-cell grid sweep around
default params. Results are collected and written to a markdown report.

Usage:
    PYTHONPATH=. python scripts/audit_all_regimes.py
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, "D:/investment-x")

from ix.core.regimes import list_regimes
from ix.core.regimes.sensitivity import audit_regime_sensitivity


# ── Target resolution ───────────────────────────────────────────────

TARGET_CODE_MAP = {
    "SPY":       "SPY US EQUITY:PX_LAST",
    "IWM":       "IWM US EQUITY:PX_LAST",
    "EEM":       "EEM US EQUITY:PX_LAST",
    "HYG":       "HYG US EQUITY:PX_LAST",
    "TLT":       "TLT US EQUITY:PX_LAST",
    "GLD":       "GLD US EQUITY:PX_LAST",
    "DBC":       "DBC US EQUITY:PX_LAST",
    "WTI":       "CL1 Comdty:PX_LAST",
    "CL1":       "CL1 Comdty:PX_LAST",
    "GC1":       "GC1 Comdty:PX_LAST",
    "GC1 COMDTY": "GC1 Comdty:PX_LAST",
}

# Regimes whose target is one of their own constituent indicators —
# must exclude that indicator from the composite to avoid circularity.
EXCLUDE_MAP = {
    "inflation":       {"i_WTI"},
    "commodity_cycle": set(),
}

# Regimes without a parseable target in description → manual fallback.
FALLBACK_TARGETS = {
    "liquidity":  ("SPY US EQUITY:PX_LAST", 3),
    "dispersion": ("SPY US EQUITY:PX_LAST", 3),
}


def resolve_target(reg) -> tuple[str, int]:
    """Parse (target_code, horizon_months) from a regime's description."""
    if reg.key in FALLBACK_TARGETS:
        return FALLBACK_TARGETS[reg.key]
    m = re.search(r"Target:\s*([A-Z0-9_\-\. ]+?)\s+(\d+)M", reg.description)
    if not m:
        return FALLBACK_TARGETS.get(reg.key, ("SPY US EQUITY:PX_LAST", 3))
    raw_target = m.group(1).strip().rstrip(",").strip()
    horizon = int(m.group(2))
    code = TARGET_CODE_MAP.get(raw_target, raw_target)
    return code, horizon


# ── Compact grid override ───────────────────────────────────────────

def build_grid(reg) -> dict:
    """2-point grid per param around the regime's own defaults → 16 cells."""
    d = reg.default_params or {}
    z = int(d.get("z_window", 96))
    s = float(d.get("sensitivity", 2.0))
    h = int(d.get("smooth_halflife", 2))
    c = int(d.get("confirm_months", 3))
    return {
        "z_window":        sorted({max(12, int(z * 0.75)), z}),
        "sensitivity":     sorted({round(s * 0.75, 3), round(s, 3)}),
        "smooth_halflife": sorted({max(1, h - 1), h}),
        "confirm_months":  sorted({max(1, c - 1), c}),
    }


# ── Main sweep ──────────────────────────────────────────────────────

def main() -> None:
    regimes = list_regimes()
    print(f"Auditing {len(regimes)} regimes (2^4 = 16-cell grid each)")
    print("=" * 72)

    results = []
    t_total = time.time()

    for i, reg in enumerate(regimes, 1):
        target, horizon = resolve_target(reg)
        exclude = EXCLUDE_MAP.get(reg.key)
        grid = build_grid(reg)

        t0 = time.time()
        print(f"\n[{i}/{len(regimes)}] {reg.key:22s} → {target} @ {horizon}M")
        try:
            r = audit_regime_sensitivity(
                reg.key,
                target,
                horizon,
                grid_override=grid,
                exclude_indicators=exclude,
                quiet=True,
            )
            dt = time.time() - t0
            print(f"  {r.verdict:10s}  "
                  f"default={r.format_pct(r.default_spread):>7s}  "
                  f"median={r.format_pct(r.grid_median_spread):>7s}  "
                  f"min={r.format_pct(r.grid_min_spread):>7s}  "
                  f"max={r.format_pct(r.grid_max_spread):>7s}  "
                  f"fragile={r.fragile_cells}/{r.n_total}  "
                  f"flips={r.sign_flips}  "
                  f"({dt:.1f}s)")
            results.append(r)
        except Exception as exc:
            dt = time.time() - t0
            print(f"  ERROR: {exc}  ({dt:.1f}s)")
            results.append(None)

    t_total = time.time() - t_total
    print("\n" + "=" * 72)
    print(f"Total runtime: {t_total:.1f}s ({t_total / 60:.1f}m)")

    # ── Summary table ────────────────────────────────────────────────
    print("\n## Summary by verdict\n")
    by_verdict: dict[str, list[str]] = {"robust": [], "sensitive": [], "fragile": [], "unknown": []}
    for reg, r in zip(regimes, results):
        if r is None:
            by_verdict.setdefault("error", []).append(reg.key)
        else:
            by_verdict.setdefault(r.verdict, []).append(reg.key)

    for verdict in ["robust", "sensitive", "fragile", "unknown", "error"]:
        names = by_verdict.get(verdict, [])
        if names:
            print(f"  {verdict:10s} ({len(names)}): {', '.join(names)}")

    # ── Write markdown report ────────────────────────────────────────
    report_path = Path("D:/investment-x/.claude/skills/ix-rename-researchfiles")
    report_path = Path("D:/investment-x/scripts") / "audit_all_regimes_report.md"
    lines = [
        "# Regime sensitivity audit — all 19 regimes",
        "",
        "Walk-forward parameter-sensitivity sweep using `audit_regime_sensitivity`",
        "with a 2^4 = 16-cell grid around each regime's default params.",
        "",
        "| # | Regime | Target | H | Verdict | Default | Median | Min | Max | Fragile | Flips | VolNorm |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for i, (reg, r) in enumerate(zip(regimes, results), 1):
        target, horizon = resolve_target(reg)
        if r is None:
            lines.append(f"| {i} | {reg.key} | {target} | {horizon}M | ERROR | — | — | — | — | — | — | — |")
            continue
        vol_norm = ""
        try:
            # One extra single-call to get the vol-normalized headline
            from ix.core.regimes.validate import validate_composition
            vn = validate_composition(
                [reg.key], target, horizon,
                params=reg.default_params,
                exclude_indicators=EXCLUDE_MAP.get(reg.key),
            )
            if vn.vol_normalized_spread is not None:
                vol_norm = f"{vn.vol_normalized_spread:.2f}"
        except Exception:
            pass
        lines.append(
            f"| {i} | {reg.key} | {target} | {horizon}M | "
            f"**{r.verdict}** | "
            f"{r.format_pct(r.default_spread)} | "
            f"{r.format_pct(r.grid_median_spread)} | "
            f"{r.format_pct(r.grid_min_spread)} | "
            f"{r.format_pct(r.grid_max_spread)} | "
            f"{r.fragile_cells}/{r.n_total} | "
            f"{r.sign_flips} | "
            f"{vol_norm} |"
        )

    lines.append("")
    lines.append("**Fragility verdict scale** — `robust` (≥80% of grid cells ≥80% of default, no sign flips) · "
                 "`sensitive` (stable sign but ≥20% below 80% of default) · "
                 "`fragile` (sign flip or median < half default, T1.7 fail).")
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nReport written to: {report_path}")


if __name__ == "__main__":
    main()
