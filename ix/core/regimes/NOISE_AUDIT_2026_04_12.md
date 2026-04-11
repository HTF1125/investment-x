# Regime Noise Audit — 2026-04-12

Follow-up to the halflife-refactor sweep (see `scripts/_archive/`). The
refactor flagged two regimes whose label flip rate couldn't be tamed by
smoothing alone. Per-indicator analysis identified the structural root
causes below — fixing them is an indicator-sourcing problem, not a
smoothing problem.

## `growth` — single-indicator composite

| indicator        | role              | flips/yr | notes                        |
|------------------|-------------------|----------|------------------------------|
| g_CLIDiffusion   | composite (sole)  | 2.41     | entire growth signal         |
| g_Claims4WMA     | excluded          | 0.55     | in `_exclude_from_composite` |
| m_ISMServices    | monitor-only      | 3.36     | `m_` prefix, not composited  |

**Finding.** After exclusions, the Growth composite z-score is driven by a
single indicator (`g_CLIDiffusion`). With no cross-indicator averaging, the
composite inherits the full flip rate of its sole input. This is why the
old confirmation filter was doing real work on this regime — it was
the only thing preventing single-indicator label noise from leaking into
`H_Dominant`.

**Recommended fix.** Add at least 2 more `g_*` indicators to the Growth
regime (candidates: `g_ISMManu`, `g_PayrollsYoY`, `g_IndProd`, `g_RetailSales`).
Until this is done, `growth` will remain noisier at `halflife=2` than the
old default — the `hl=2` override in registry.py is a holding pattern.

## `liquidity_impulse` — RRP is noise, not signal

| indicator   | flips/yr | std  | corr(Impulse_Z) |
|-------------|----------|------|-----------------|
| li_TGA      | 4.38     | 1.56 | 0.81            |
| li_RRP      | 3.77     | 1.46 | **0.17**        |
| li_NetLiq   | 1.97     | 1.31 | 0.46            |
| Impulse_Z   | **5.01** | —    | —               |

**Finding.** The composite z-score (5.01 flips/yr) is *worse* than any of
its three constituents. `li_RRP` has a 0.17 correlation with the composite,
meaning its contribution is effectively decorrelated noise. When the mean
pools three signals and one is orthogonal to the aggregate direction, the
mean wobbles more than any single input.

**Recommended fix.** Either (a) drop `li_RRP` from the composite — likely
pushing Impulse_Z flips/yr below 2.0, or (b) replace it with a better TGA /
balance-sheet-adjacent indicator. Possibly `li_BankReserves` or the
3-month delta of net liquidity. Until fixed, `halflife=4` in registry.py is
a holding pattern and `vol_term × liquidity_impulse` composites will carry
unusable tail states.

## Next steps

Both regimes should go through `/ix-regime-builder` for an indicator
selection refresh. Neither change is blocking for the halflife refactor —
production flip rates are bounded, just higher than target. Flag for the
next research sprint.
