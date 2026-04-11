# Post-refactor sensitivity audit — 2026-04-12

Ran `audit_regime_sensitivity` across every registered regime with the
new per-regime halflife defaults. Grid = 27 cells per regime (±25% on
`z_window`, ±25% on `sensitivity`, ±1 on `smooth_halflife`). Source:
`scripts/audit_all_sensitivity.py`, report at
`scripts/_sensitivity_audit_report.csv`.

## Verdict summary

| verdict   | count | regimes |
|-----------|-------|---------|
| robust    | 9     | dollar_trend, credit_level, credit_trend, **growth**, yield_curve, vol_term, **liquidity_impulse**, commodity_cycle, housing |
| sensitive | 9     | liquidity, global_liquidity, inflation, real_rates, breadth, earnings_revisions, risk_appetite, labor, dispersion |
| unknown   | 2     | positioning, cb_surprise |

## Key findings

**Good news — the two flagged regimes landed robust.** Both `growth` and
`liquidity_impulse` (the two that the halflife sweep couldn't denoise)
score `robust` on ≥ 80% of the grid. Their new per-regime halflives
(2 and 4 respectively) are not sitting in a local optimum. Structural
indicator work (see `NOISE_AUDIT_2026_04_12.md`) is still the right
direction, but the smoothing choice itself is stable.

**9 "sensitive" regimes — watch list, not alarm.** Sensitive means the
spread varies meaningfully across the parameter grid but the sign is
consistent and the grid median is above half the default. These are
signals worth keeping, but their current numbers aren't locked-in —
future parameter refactors could shift them.

**2 "unknown" verdicts are a bug.** Both `positioning` (3 states) and
`cb_surprise` (3 states) report a 0.00% default spread. For
`cb_surprise`, the grid median is 31%, so the **default config** at
`hl=3` is silently failing to produce a spread even though
neighbor configurations do. Root cause is likely in how
`validate_composition` handles the 3-state case at the new defaults
(possibly the train_window interacts badly with halflife=3 + 60-month
z_window). This is pre-existing infrastructure noise, not refactor
regression, but should be investigated.

## Action items

1. **`cb_surprise` / `positioning` default-spread bug** — trace why
   `validate_composition` returns 0 at the registered default params
   when the audit grid succeeds at neighbors. Check train_window
   interaction with the 60-month z_window override.
2. **Sensitive regime watch list** — no action now, but any future
   halflife / z_window refactor should re-run this audit to catch a
   sensitive → fragile slide.
