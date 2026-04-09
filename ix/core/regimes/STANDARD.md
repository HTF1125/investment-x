# Standard for a Good 1D Regime

*A production regime subclass under `ix/core/regimes/` is not "done" until it meets every mandatory bar in this document. This file is the single source of truth — the bar that `ix-regime-builder` enforces and that code review checks against.*

---

## 1. Philosophy — what a "good" 1D regime actually is

A regime is **not** a forecast. It is a **conditional return distribution** — a partitioning of history into states where forward returns of a specific target asset are statistically different.

A regime is valuable when all four are true:

1. **Parsimonious** — one dimension, 2–4 states, ≤8 indicators. If you need more axes to explain it, it's a composite, not a 1D regime.
2. **Orthogonal** — its signal is residual to the 9 axes already registered. Adding it expands the information set; it doesn't re-skin an existing one.
3. **Actionable** — the forward-return gap between best and worst state is economically meaningful *after* walk-forward validation, not just in-sample.
4. **Robust** — the gap survives permutation tests, subsample splits, indicator drop-one, and horizon perturbations. Not just lucky.

The 4-gate Decision Card (D1 Separation, D2 Persistence, D3 Conviction, D4 Sample) is the *runtime* version of this standard. This document is the *build-time* version — stricter, with more checks.

---

## 2. Mandatory structural bars (build-time)

Every new regime MUST satisfy these before it can be registered. No exceptions.

### S1. One dimension, one concept
- `dimensions = ["X"]` — exactly one entry.
- `states = [...]` — 2, 3, or 4 entries. Default to 2 unless the asymmetry is empirically justified.
- The dimension name is a *noun* (e.g. `"Liquidity"`, not `"IsLiquid"`).
- States are *present-tense descriptors* (`"Easing"`, `"Rising"`, `"Wide"`), never imperative (`"Buy"`, `"Sell"`).

### S2. Indicator discipline
- Minimum **3** indicators per dimension. Below 3 and the composite is not a composite.
- Maximum **8** indicators per dimension. Above 8 the marginal indicator is noise.
- Every indicator must be z-scored using one of the canonical helpers in `base.py`:
  - `zscore(s, window)` — rolling standardization (default)
  - `zscore_ism(s, window)` — anchored at 50 (ISM threshold)
  - `zscore_anchored(s, anchor, window)` — anchored at structural baseline (CPI @ 2.5%, etc.)
  - `zscore_roc(s, window, use_pct)` — z-score of rate-of-change
- Prefixes match the dimension: a `"Growth"` dimension uses `g_*`, a `"Liquidity"` dimension uses `l_*`. Monitor-only indicators (displayed but excluded from composite) use `m_*`.
- Every indicator must have a comment explaining:
  1. What it measures (e.g. "3-month Treasury bill yield")
  2. Why it belongs in this dimension (not a different one)
  3. Its sign — does raising it raise or lower the composite? If the raw series is *negatively* correlated with the dimension, invert at load time (`zscore(-s, window)`).

### S3. Publication lag must be respected
- Economic data (CPI, payrolls, GDP) must carry a realistic `lag=1` or `lag=2` in `load_series(code, lag=N)`.
- Market data (yields, spreads, FX) uses `lag=0`.
- Weekly/daily data is always resampled to month-end via `load_series` (automatic).
- **No look-ahead.** If the `_load_indicators` method returns a value for month M that could not have been known at the end of month M, the regime is rejected.

### S4. No hard-rule violations
Check against `CLAUDE.md` project rules before registering:
- Do NOT invert VIX, FCI, put/call at the raw-series level. They are contrarian — encode the inversion in the state→return *target mapping*, not in the indicator sign.
- Do NOT use Global M2 (zero IC, pure noise).
- Do NOT equal-weight indicators that have been shown to have different IC. If you have IC estimates, weight by them inside `_load_indicators` via the multiplier trick.
- Walk-forward or expanding-window backtests only. No full-sample optimization.

### S5. Orthogonality to existing axes
- Before building, compute the 60-month rolling Pearson correlation of the new composite z-score against each of the 9 existing axis composite z-scores.
- **Max |ρ| ≤ 0.60** against any single existing axis.
- **Max |ρ| ≤ 0.75** against the best 3-axis linear combination of existing axes (residual IC check).
- If either bar fails, the regime is a skin of something you already have — reject.

---

## 3. Mandatory empirical bars (validation)

After the class compiles and loads data cleanly, it must pass these in `ix/core/regimes/validate.py::validate_composition`:

### Tier 1 — "not broken" (7 checks, all must pass)

| # | Check | Threshold | Why |
|---|---|---|---|
| **T1.1** | **Coverage** | ≥ 85% of months since inception have a labeled state | No regime = no signal |
| **T1.2** | **Persistence** | Median run length ≥ 4 months | Sub-4mo flips cannot be traded at monthly rebalancing |
| **T1.3** | **Sample size per state** | Every state ≥ 30 months of history | Under-sampled states produce fragile statistics |
| **T1.4** | **Vol-normalized spread** | \|best − worst state annualized fwd return\| ÷ target_vol ≥ **0.25** (i.e. Sharpe delta ≥ 0.25) | Raw-percentage bars punish low-vol targets (TLT) and flatter high-vol targets (WTI). Vol-normalized = fair comparison across universes. See §3.1 for rationale. |
| **T1.5** | **Welch's t-test** | p-value (best vs worst state fwd returns) < 0.05 | The gap is statistically distinguishable from noise |
| **T1.6** | **Sign consistency** | Best-state mean fwd return > worst-state mean fwd return in BOTH the pre-2010 and post-2010 subsamples | Not a one-era artifact |
| **T1.7** | **Parameter sensitivity** | ``audit_regime_sensitivity()`` verdict ∈ {``robust``, ``sensitive``} — verdict ``fragile`` is an automatic fail | A regime whose spread flips sign or collapses to half under ±25% parameter perturbation is overfit. See §3.1. |

### Tier 2 — "robust to luck" (5 checks, all must pass)

| # | Check | Threshold | Why |
|---|---|---|---|
| **T2.1** | **Permutation test** | 1000-trial state-label shuffle — real spread ranks in top 1% (p < 0.01) | The gap is not a random partitioning of months |
| **T2.2** | **Cohen's d** | \|d\| ≥ 0.30 between best and worst state forward returns | The effect size is meaningful, not just statistically significant |
| **T2.3** | **Drop-one robustness** | Removing any single indicator from `_load_indicators` keeps T1.4 passing | No single indicator is load-bearing |
| **T2.4** | **Horizon robustness** | T1.4 passes at 3m, 6m, AND 12m forward horizons (or for phase regimes, at the declared locked horizon ± 3 months) | The signal isn't tuned to one specific window |
| **T2.5** | **Conviction gate** | At least 30% of months have Conviction ≥ 40 | If conviction is chronically low, the regime never fires |

### Tier 3 — "adds value" (aspirational, at least 2 of 4 should pass)

| # | Check | Target | Why |
|---|---|---|---|
| **T3.1** | **Drawdown avoidance** | Regime's "bad" state captures > 60% of worst-quartile forward-return months | The signal actually warns about drawdowns |
| **T3.2** | **Orthogonality IC lift** | Residual IC vs existing 9 axes > 0.05 | It adds predictive power on top of what you already have |
| **T3.3** | **Transition IC** | First-month-in-new-state IC ≥ full-sample IC × 0.8 | Signal isn't all from stale continuation |
| **T3.4** | **Cross-asset generality** | T1.4 passes for ≥ 2 assets in the declared `asset_tickers` universe | The signal isn't married to one ticker |

### 3.1 Why T1.4 is vol-normalized and T1.7 exists

**Vol-normalized spread (T1.4).** The previous bar was a fixed 5% annualized spread, which silently penalized low-vol targets (TLT, IEF, BIL) and rewarded high-vol targets (WTI, XME, oil-linked) for the same underlying signal quality. A ``YieldCurveTrendRegime`` shelved at 3.89% TLT spread was strictly *better* than a 5% WTI spread on every other metric (Cohen's d, Welch p, sign consistency) — but the raw-percentage threshold didn't see it.

Vol normalization divides the spread by the target asset's annualized volatility over the same walk-forward test window, yielding a **Sharpe delta** between the best and worst states. The 0.25 floor is calibrated so that a WTI-anchored regime needs ≈ 8–10% raw spread (WTI vol ≈ 35%) while a TLT-anchored regime needs only ≈ 3% raw spread (TLT vol ≈ 12%). Same information content, same bar.

**Parameter sensitivity (T1.7).** A regime that posts a great spread at its declared defaults but collapses under ±25% perturbation of ``(z_window, sensitivity, smooth_halflife, confirm_months)`` has been tuned to a local minimum, not to a structural signal. The ``audit_regime_sensitivity()`` utility in ``ix.core.regimes.sensitivity`` sweeps a 3–4 value grid around each parameter and returns one of three verdicts:

- **robust** — ≥ 80% of grid cells maintain ≥ 80% of the default spread AND no sign flips.
- **sensitive** — no sign flips but ≥ 20% of cells fall below 80% of default. Shipping is allowed; the description field must disclose the sensitivity.
- **fragile** — at least one grid cell flips sign OR the grid median collapses below half the default spread. **Automatic T1.7 fail**.

The audit runs ``validate_composition`` at every grid point, so all measurements are walk-forward and carry no look-ahead bias. Run it via ``audit_regime_sensitivity(regime_key, target, horizon_months)`` and attach the verdict + summary to the regime's ship report.

---

## 4. Target asset — "locked" convention

Every regime declares one **primary target asset** at a specific **horizon**. This is the asset the empirical validation is scored against, and it must be chosen BEFORE running any backtests. Retargeting after the fact to chase p-values is explicitly forbidden.

Selection heuristic:

| Regime type | Target asset | Horizon |
|---|---|---|
| Growth / earnings / labor | SPY | 3m |
| Inflation / commodities | WTI (CL1) or DBC | 6m |
| Liquidity / credit / dollar | HYG or EEM | 6m |
| Real rates / yield curve | GLD or SPY | 12m |
| Volatility / breadth / positioning (contrarian) | SPY | 3m |
| Policy / CB surprise | SPY | 1–3m |

The target and horizon are stored in the registration `description` field as machine-parseable metadata: `"Target: SPY 3M fwd"`. This is what the Decision Card reads.

---

## 5. Documentation bars

Every regime class file must include:

1. **Module docstring** covering:
   - Thesis (1 paragraph — *why* this is a regime, not just a feature)
   - State list with plain-English meaning of each
   - Indicator list with source and inversion notes
   - Target asset and horizon (locked)
   - Empirical results table (Tier 1/2/3 scores)
   - Source citations (academic / strategist papers)
2. **Class-level docstring** with one-line summary.
3. **Indicator-level inline comments** explaining what each `_load` call measures.
4. **A registration entry in `registry.py`** with:
   - `description` — quant-research voice, includes target + horizon
   - `color_map` — uses the steel palette CSS var values
   - `state_descriptions` — tooltip text, 1 sentence per state
   - `asset_tickers` — universe relevant to the signal (not the default macro basket if the signal has a specific asset profile)

---

## 6. Runtime bars (checked by the Decision Card)

These are the 4 gates that fire at runtime in the UI — they're the *operational* version of Tier 1/2:

| Gate | Check | Threshold |
|---|---|---|
| **D1 Separation** | \|Cohen's d\| between best and worst state fwd returns | ≥ 0.40 |
| **D2 Persistence** | Average run length across history | ≥ 4 months |
| **D3 Conviction** | Current dominant-state smoothed probability × 100 | ≥ 40 |
| **D4 Sample Size** | Months of history in the current state | ≥ 30 |

Gates can fail at runtime without the regime being "bad" — a regime built correctly can still temporarily lose conviction. The gates tell the user: *"this signal currently is / is not strong enough to tilt on."*

---

## 7. Rejection criteria

A regime is rejected (not registered, not exposed) if any of the following is true:

- Violates any S1–S5 structural bar
- Fails any Tier 1 check
- Fails 2+ Tier 2 checks
- Has `max |ρ| > 0.75` against the best 3-axis combination of existing axes (redundant)
- Cannot be documented — if you can't write the module docstring, you don't understand the signal well enough to ship it

Rejected regimes go in `ix/core/regimes/_drafts/` with a `REJECTED.md` explaining why, so the lessons accumulate.

---

## 8. Maintenance bars

Once shipped, each regime gets:

- **Quarterly re-validation** — re-run Tier 1 and Tier 2 on the last 5 years. If Tier 1 drops below 4/6 or Tier 2 below 3/5, flag as "degraded" in the registry.
- **Annual orthogonality re-check** — recompute correlation to the other registered axes; if it creeps above 0.75 against any combination, investigate (usually new data sources drifting the signal).
- **Immediate review** if the underlying data feed changes methodology (FRED revisions, Bloomberg code rename, collector API break).

---

## 9. Summary — the 8 hard bars

If you remember nothing else:

1. ✅ **One dimension, 2–4 states, 3–8 z-scored indicators**
2. ✅ **Publication lag respected, no look-ahead**
3. ✅ **`max |ρ| ≤ 0.60` against every existing axis**
4. ✅ **Locked target asset + horizon, chosen before backtest**
5. ✅ **Tier 1: 6/6 pass** (coverage, persistence, sample, spread, p-value, sign consistency)
6. ✅ **Tier 2: 5/5 pass** (permutation, Cohen's d, drop-one, horizon, conviction)
7. ✅ **Registered with color_map, state_descriptions, asset_tickers, steel palette**
8. ✅ **Module docstring with thesis, states, indicators, target, results, sources**
