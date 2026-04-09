---
name: ix-regime-builder
description: Build production single-dimension (1D) Regime subclasses in ix/core/regimes/ AND wire them into the Next.js frontend so they render nicely. Each regime is exactly one axis (one dimension, 2-4 states) with a locked forward-return target. Multi-axis composites are NOT in scope — delegate combination search to ix-regime-combiner. The skill ships only when Tier 1 or Tier 2 quality bars pass and the live frontend visually verifies.
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, WebSearch, WebFetch, mcp__Claude_Preview__preview_start, mcp__Claude_Preview__preview_screenshot, mcp__Claude_Preview__preview_eval, mcp__Claude_Preview__preview_fill, mcp__Claude_Preview__preview_click, mcp__Claude_Preview__preview_console_logs, mcp__Claude_Preview__preview_logs
user-invocable: true
---

# Regime Builder — 1D ONLY

**Outcome (what success looks like):** after this skill ships a regime, a portfolio manager can open `/macro`, click the new axis tile, read the **Decision Card** on the terminal output, and within 10 seconds know: (1) what state we are in today, (2) which 3 indicators are driving it, (3) whether to lean risk-on or risk-off, and (4) what would flip the regime. If the Decision Card can't answer those four questions at the current edge, the regime is not useful regardless of Cohen's d or p-value.

**Mandate (2026-04-07):** This skill builds **only 1-dimensional axis regimes**. Every shipped regime has exactly one `dimensions = [<single>]` entry and 2-4 states. Multi-axis composites (growth × inflation, credit × dollar, etc.) are generated **on demand** by the frontend via `/api/regimes/compose`, not by hand-coded computer subclasses.

If the user asks for a "macro 4-state regime" or any 2D/3D framework: build the constituent 1D axes separately, then hand off to **`ix-regime-combiner`** to find and verify the best joint composition.

**Deliverable:** a `Regime` subclass file in `ix/core/regimes/` that subclasses `ix.core.regimes.base.Regime`, defines exactly one dimension, passes a statistical quality bar on a locked forward-return target, AND emits a Decision Card that a PM can act on.

**Stop condition:** the skill does not stop until it ships a passing 1D subclass with a clean Decision Card, or reports an honest failure with a full diagnostic. No half-measures, no "this might work" — every run ends with a verdict.

---

## What Makes a Good 1D Regime

Before writing any code, read this. It is the contract every shipped regime is measured against — not just Tier 1/2 statistical bars. A regime that clears Tier 2 but violates any of the 9 properties below is still rejected.

### Design-time properties (set before writing code)

1. **Single concept, single dimension.** Exactly one entry in `dimensions`. If you need a level + trend split for a cyclical quantity, build two regimes and link them with `phase_pair` (see "Phase-Pair Pattern" below). Do not cram level and trend into a single multi-dimension class — that was `MacroRegime` and it is retired.

2. **Orthogonal to existing regimes.** The composite's signal space must not duplicate any already-registered regime's composite. Duplication caps the joint composition lift — if your new regime is 80% HY OAS driven, composing it with `credit_level` adds nothing. **Hard design-time gate:** max |ρ(new_composite, any_existing_composite)| ≤ 0.60 over the overlapping history. A failing correlation check kills the build before scaffolding.

3. **Transmission mechanism is articulable in one sentence.** You must be able to write a single sentence explaining *why* the input indicators predict the target at the chosen horizon. "Credit spreads lead default cycles by 3–6 months, so HY OAS at t predicts HYG at t+6M" is articulable. "Liquidity predicts SPY because liquidity matters" is not. Write this sentence in the class docstring before coding anything.

4. **Signal class chosen correctly** (pick ONE during the Concept step):
   - **Level + mean reversion** (e.g. dollar, inflation, credit spreads vs structural reference) → use `zscore_anchored(s, anchor, z_window)` at a **structural reference value** (Fed target 2.5% for inflation, basis year 100 for dollar indices, 50 for ISM, 0% for commodity YoY). **Do NOT use rolling z-score over a window ≈ one cycle length** — it drifts with the cycle it's trying to measure. This is the `dollar_level` v1 failure and the `inflation` pre-anchor failure.
   - **ROC + turning point** (e.g. trend signals, momentum) → use `zscore_roc(s, z_window, use_pct=False)` or `zscore(s.diff(n), z_window)`. Match the ROC window to the signal's natural inflection time scale, **not** the target horizon. Credit spreads turn over 3 months → use 3M diff regardless of whether the target horizon is 6M or 12M.
   - **Quantity flow** (e.g. central bank balance sheets, TGA drawdown, credit impulse) → use raw levels or YoY directly. No anchoring needed — quantities don't have a structural equilibrium to mean-revert to.
   - **Phase-pair (level + trend split)** → build two sibling regimes and link via `phase_pair`. Each sibling's standalone T1.4 bar is waived; the bar applies to the joint composition instead.

5. **Standalone-vs-composition intent declared up front.** Before writing code, decide: is this regime intended to pass T1.4 standalone, or is it a phase_pair building block whose T1.4 applies to the joint? Phase-pair building blocks are legitimate — `credit_trend` alone posts only 0.21 vol-normalized spread, but `credit_level + credit_trend` jointly posts 0.94 (4× the bar). Declare intent by setting `phase_pair="sibling_key"` in the registration.

### Pipeline properties (enforced by base class + validator)

6. **Causal, walk-forward, monotonic index.** No look-ahead, no full-sample optimization, `H_Dominant` at t uses only data ≤ t − `data_lag_months`. Enforced by `validate_composition`.

7. **Tier 1 bar passes on declared target** (standalone OR composed, per intent):
   - T1.1 Coverage ≥ 85%
   - T1.2 Median run length ≥ 4 months
   - T1.3 Every state ≥ 30 observations
   - **T1.4 Vol-normalized spread ≥ 0.25 Sharpe delta** (NOT raw 5% — vol-normalization makes WTI and TLT comparable)
   - T1.5 Welch p < 0.05
   - T1.6 Subsample sign consistency across 2010 split
   - **T1.7 Parameter sensitivity verdict ∈ {robust, sensitive}** — `fragile` (any sign flip or grid median below half default) is an automatic fail

### Current-edge properties (must hold today, not just historically)

8. **Decision Card answerable at the current edge.** The regime must answer: (a) what state are we in today, (b) which 3 indicators are driving it, (c) what historical forward return does this state map to, (d) what would flip the regime. If any is unanswerable at t=now, the regime ships to `drafts/` — this is the DC2 blocker.

9. **Asset analytics coherent.** The per-regime asset performance table must show non-degenerate Sharpe spreads across the declared universe. If every asset looks the same in every state, the regime is decorative, not functional.

---

## Before Starting

Read every invocation:
- `D:/investment-x/.claude/skills/ix-regime-builder/LEARNINGS.md` (skip if missing — created on first failure/success)
- `D:/investment-x/.claude/context/research-philosophy.md` — hard rules
- `D:/investment-x/.claude/context/indicator-registry.md` — DB codes, IC weights
- `D:/investment-x/ix/core/regimes/STANDARD.md` — authoritative Tier 0/1/2/3 definitions (T1.4 vol-norm, T1.7 sensitivity)
- `D:/investment-x/ix/core/regimes/base.py` — refresh the contract (abstract methods, helper functions)
- `D:/investment-x/ix/core/regimes/fundamentals/growth.py` — canonical reference 1D subclass
- `D:/investment-x/ix/core/regimes/fundamentals/loaders.py` — shared indicator loaders for the fundamentals subpackage
- `D:/investment-x/ix/core/regimes/markets/credit.py` — canonical phase_pair sibling pattern (credit_level ↔ credit_trend)
- `D:/investment-x/ix/core/regimes/registry.py` — registration pattern (all `category="axis"`, paired regimes declare `phase_pair`)
- `D:/investment-x/ix/core/regimes/compose.py` — how 1D regimes are joined into multi-axis views (you do NOT touch this — it's the consumer)
- `D:/investment-x/ix/core/regimes/analyzer.py` — `MultiDimRegimeAnalyzer` used to validate phase-paired joint compositions
- `D:/investment-x/ix/core/regimes/sensitivity.py` — `audit_regime_sensitivity` for T1.7

## Usage

```
/ix-regime-builder "credit cycle"             # build a 1D credit cycle regime, skill picks target
/ix-regime-builder "credit cycle" --target HYG --horizon 6m
/ix-regime-builder                            # discover mode — propose a new 1D regime worth building
/ix-regime-builder list                       # show registered regimes + which Tier they passed
```

After a successful 1D ship, the skill automatically suggests:
```
Build complete. To find the best joint composition of <new_regime> with existing 1D
regimes, run: /ix-regime-combiner --target <ASSET> --horizon <H> --include <new_regime>
```

---

## The 1D Regime Contract

Every subclass MUST define:

```python
from __future__ import annotations
import pandas as pd
from .base import Regime, load_series as _load, zscore, zscore_ism, zscore_roc, LW, RW

class CreditLevelRegime(Regime):
    """One-line description.

    Target: HYG forward 6M returns
    Justification: <why this asset and horizon are the right test for this regime>
    Source: <citation>
    """

    name = "CreditLevel"
    dimensions = ["Level"]                       # EXACTLY ONE dimension — no exceptions
    states = ["Wide", "Tight"]                   # 2-4 states is typical (2 most common for axis regimes)

    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        rows: dict[str, pd.Series] = {}

        # Each indicator: LW * level z + RW * ROC z (LW=0.25, RW=0.75)
        hy = _load("BAMLH0A0HYM2")
        if not hy.empty:
            rows["lv_HY_OAS"] = (
                zscore(hy, z_window) * LW
                + zscore_roc(hy, z_window, use_pct=False) * RW
            ).rename("lv_HY_OAS")

        # ... more indicators (all sharing the same prefix) ...

        return rows

    def _dimension_prefixes(self) -> dict[str, str]:
        return {"Level": "lv_"}                  # ONE prefix → ONE dimension

    def _state_probabilities(
        self, dim_probs: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:
        lp = dim_probs["Level"]
        # Must return one entry per state, summing to 1.0 at every timestep
        return {
            "P_Wide":  1.0 - lp,
            "P_Tight": lp,
        }
```

### Mandatory checklist (every 1D subclass)
- [ ] Class attrs: `name`, `dimensions = [<exactly one>]`, `states` (2-4)
- [ ] `_load_indicators(z_window)` returns dict where every key shares the **same prefix**
- [ ] Signal class picked from the Good Regime §4 decision tree (level-anchored / ROC / quantity / phase-pair) — documented in class docstring
- [ ] Level signals over cyclical series use `zscore_anchored(s, anchor, z_window)` at a **structural reference**, not rolling `zscore`
- [ ] ISM-style bounded series use `zscore_ism` (anchored at 50)
- [ ] Empty-guard every `load_series()` call (`if x.empty: skip`)
- [ ] `.name` set on every series
- [ ] `_dimension_prefixes()` returns exactly one mapping
- [ ] `_state_probabilities` returns probabilities summing to ~1.0 derived from the **single** dimension's probability series
- [ ] Monitor-only indicators use `m_` prefix and are auto-excluded from composite
- [ ] `_exclude_from_composite()` overridden only if loading a `g_*`/`i_*`/etc. column for display that should not feed the composite z-score

### Indicator prefix convention (1D map)
| Prefix | Dimension | Used by |
|---|---|---|
| `g_` | Growth     | `GrowthRegime` |
| `i_` | Inflation  | `InflationRegime` |
| `l_` | Liquidity  | `LiquidityRegime` |
| `lv_` | Level     | `CreditLevelRegime`, `DollarLevelRegime` (level half of a level/trend pair) |
| `tr_` | Trend     | `CreditTrendRegime`, `DollarTrendRegime` (trend half of a level/trend pair) |
| `c_` / `v_` / `<new>` | new 1D concepts | new regimes — pick a unique 2-letter prefix |
| `m_` | Monitor-only | excluded from composite, kept for display |

**Note (2026-04-09):** `MacroRegime` (the 2D Growth × Inflation class) is **removed**. Shared growth/inflation indicator loaders now live as plain functions in `ix/core/regimes/fundamentals/loaders.py` (`load_growth_indicators`, `load_inflation_indicators`). Do NOT import or subclass `MacroRegime` — it does not exist. `GrowthRegime` and `InflationRegime` import the loader functions directly.

### Phase-Pair Pattern (level ↔ trend) — STILL 1D

A "level vs trend" decomposition of a cyclical quantity (credit, dollar, liquidity) is built as **two separate 1D regimes** that share an underlying signal and declare each other via the `phase_pair` field on their registrations:

```python
CreditLevelRegime  →  dimensions=["Level"], states=["Wide", "Tight"]
                      phase_pair="credit_trend"

CreditTrendRegime  →  dimensions=["Trend"], states=["Widening", "Tightening"]
                      phase_pair="credit_level"
```

`phase_pair` must be **mutual** — A points to B AND B points to A. The `test_regime_smoke.test_phase_pairs_are_mutual` test enforces this.

**Standalone T1.4 is waived for phase_pair regimes.** The `credit_trend` regime posts only 0.21 vol-normalized spread standalone (below the 0.25 bar), but `credit_level + credit_trend` composed produces 0.94 (nearly 4× the bar). For phase-paired regimes, the T1.4 bar applies to the **joint composition** instead of the standalone:

```python
from ix.core.regimes import MultiDimRegimeAnalyzer
from ix.core.regimes.validate import validate_composition

# Joint validation — the bar that counts for phase_pair regimes
r = validate_composition(
    ["credit_level", "credit_trend"],
    "HYG US EQUITY:PX_LAST",
    6,
)
assert r.vol_normalized_spread >= 0.25, "joint composition below T1.4 bar"
```

**Do NOT** ship a `CreditCycleRegime` with `dimensions=["Level", "Trend"]` — that would be a 2D class and is rejected by D9. The phase-pair pattern IS how the framework expresses level+trend cycles.

**Known phase pairs (2026-04-09):** `credit_level ↔ credit_trend`, `dollar_level ↔ dollar_trend`, `liquidity ↔ liquidity_impulse`.

---

## Asset Performance (MANDATORY for every ship)

Every shipped regime automatically gets an **Asset Performance** tab on the frontend showing per-regime mean forward returns, Sharpe, max drawdown, and win rate for a curated asset universe. This is populated automatically by `RegimeComputer.compute()` via the generic `compute_asset_analytics()` helper — you do NOT write the analytics code yourself.

### What you MUST specify

In the `RegimeRegistration`, always provide **`asset_tickers`** — a dict mapping display ticker → DB code. Pick assets whose forward returns are **most sensitive** to this specific regime signal.

| Regime concept | Recommended asset universe |
|---|---|
| Credit (level or trend) | HYG, LQD, TLT, IEF, SPY, GLD, BIL |
| Dollar (level or trend) | EEM, EFA, SPY, GLD, DBC, TLT, HYG, BIL |
| Growth                  | SPY, IWM, EEM, HYG, TLT, IEF, GLD, BIL |
| Inflation               | GLD, SLV, DBC, DBA, TIP, XLE, TLT, SPY, BIL |
| Liquidity / FCI         | SPY, HYG, LQD, TLT, GLD, BIL |
| Volatility              | SPY, IWM, HYG, TLT, GLD, BIL |

**Rules for picking assets:**
1. **Always include BIL** — risk-free proxy for Sharpe.
2. **Include at least one defensive asset** (GLD, TLT, IEF) so the worst state has a positive holding.
3. **Match the signal transmission channel** — credit regime → credit ETFs, dollar regime → EM/commodities.
4. **6-10 tickers is the sweet spot.**
5. **Avoid circularity** — don't include the regime's own input series as a target (e.g. InflationRegime should not test WTI directly).

### What the helper produces

After `compute_regime(key)` runs, the `regime_snapshot.asset_analytics` JSONB column contains `per_regime_stats`, `regime_counts`, `expected_returns`, `regime_separation`, and `tickers`. The frontend `AssetPerformanceTab` renders this as a heatmap + sorted bar chart + full stats table.

`liquidity_splits` is reserved (always `{}` for 1D regimes) — multi-axis splits are produced on demand by the compose endpoint.

### Verification after ship

Screenshot the Asset Performance tab and confirm: all declared tickers appear, all declared states appear, at least one asset has a positive Sharpe in some state, regime-selector buttons match `model.states`.

---

## Hard Rules (from research-philosophy.md)

1. Do **NOT** invert VIX/FCI/put-call/AAII bull-bear — they are CONTRARIAN and loaded as-is (high fear = bullish)
2. Do **NOT** include Global M2 or "Global Liquidity" composites — zero IC, pure noise
3. Do **NOT** use full-sample optimization — rolling-window z-scores only
4. Do **NOT** equal-weight indicators — use blend (LW=0.25 level + RW=0.75 ROC) by default, OR use `zscore_anchored` for level signals over cyclical series
5. Use rate-of-change OR anchored level — never rolling z-score over a window ≈ one cycle length (the `dollar_level` v1 failure mode)
6. Default `z_window = 96` for production, `36` for prototyping (financial-conditions regimes may use 60; yield-curve slope wants 60)
7. Publication lag MUST be respected: monthly economic series → `lag=1`, daily prices → `lag=0`
8. `dimensions` MUST have exactly one entry — multi-dimensional classes are rejected (D9)
9. Do NOT import or subclass `MacroRegime` — it was retired 2026-04-09. Shared growth/inflation loaders live in `ix/core/regimes/fundamentals/loaders.py` as free functions (D10)
10. **NEW (2026-04-09):** Do NOT double-count signals already measured by another registered regime. Max |ρ(new_composite, any_existing_composite)| ≤ 0.60 — enforced as a design-time gate during the Concept step (D11)

Violating any rule = Tier 0 disqualification.

---

## Choosing the Target (per regime concept)

The skill picks `(asset, horizon)` during the concept step and **locks it** before measurement. No retargeting after seeing results.

| Regime concept | Default target | Default horizon | Rationale |
|---|---|---|---|
| Growth                  | SPY    | 3M  | Growth slowdowns transmit to equity over a quarter |
| Inflation               | WTI / DBC | 6M  | Commodity prices reflect inflation lag |
| Credit (level or trend) | HYG    | 6M  | Credit stress predicts default cycle in months |
| Liquidity / FCI         | SPY    | 3M  | Liquidity transmits fast |
| Volatility regime       | SPY    | 1M  | Vol regimes are short-lived |
| Global growth           | ACWI   | 12M | Global cycles are long |
| Dollar (level or trend) | EEM    | 6M  | Dollar moves transmit to EM with lag |
| Sector rotation         | sector pair (e.g. XLK/XLU long-short) | 6M | Rotation horizons |

Rules:
- **Always forward returns**, never contemporaneous, never vol/Sharpe-only
- Lock target in iteration 1 — write justification in subclass docstring
- If user passes `--target` and `--horizon`, use those
- If user-supplied target makes no sense for the concept, push back once then proceed if confirmed

---

## Quality Bars

### Tier 0 — Disqualifiers (auto-reject, no exceptions)

| # | Failure |
|---|---|
| D1 | Any indicator without proper publication lag (look-ahead bias) |
| D2 | Coverage < 90% of months since 2000 |
| D3 | < 2 distinct states observed in history |
| D4 | Median months-in-regime < 2 (chattering noise) |
| D5 | Any composite `_Z` column > 30% NaN |
| D6 | Inverts VIX/FCI/put-call/AAII bull-bear |
| D7 | Includes Global M2 or "Global Liquidity" |
| D8 | Full-sample optimization detected (must be rolling/walk-forward) |
| D9 | `len(dimensions) != 1` — multi-dimensional class is rejected |
| D10 | Imports or subclasses `MacroRegime` (class was retired 2026-04-09) |
| **D11** | **Duplicate signal — max `\|ρ(new_composite, any_existing_composite)\|` > 0.60 over overlapping history. Measured in Concept step, BEFORE scaffolding.** |

Tier 0 hit = reject immediately, no file shipped, log to LEARNINGS.md.

### Tier 1 — Mandatory (skill must achieve, or report failure)

**For standalone regimes** (no `phase_pair` declared), all 7 bars must pass on the declared target.

**For phase-paired regimes** (`phase_pair="sibling_key"` declared), T1.4 is measured on the JOINT composition `validate_composition([self_key, phase_pair], target, horizon)` instead of the standalone. All other bars still apply standalone.

| # | Criterion | Threshold |
|---|---|---|
| T1.1 | Coverage since 2000 | ≥ 95% rows with valid composite |
| T1.2 | All declared states observed | ≥ 75% present in history |
| T1.3 | Median months-in-regime | ≥ 4 |
| T1.4 | **Vol-normalized forward spread** on target (best − worst, divided by target annualized vol) | ≥ **0.25 Sharpe delta** — applies to joint composition if `phase_pair` set |
| T1.5 | Welch's t-test on best vs worst forward returns | p < 0.05 |
| T1.6 | Walk-forward stability (rolling z-scores only, sign-consistent pre/post 2010 split) | pass |
| T1.7 | **Parameter sensitivity audit** via `audit_regime_sensitivity()` | verdict ∈ {`robust`, `sensitive`}; `fragile` is automatic fail |

### Tier 2 — Excellent (target — stop iterating when met)

| # | Criterion | Threshold |
|---|---|---|
| T2.1 | Forward return spread | ≥ 10% |
| T2.2 | Drawdown avoidance hit rate (worst-state cluster precedes top-decile DDs) | ≥ 60% |
| T2.3 | Sharpe spread (best regime asset vs worst) | best > 1.0, worst < 0 |
| T2.4 | OOS stability (post-2010 spread within 30% of full-sample, or stronger) | pass |
| T2.5 | Conviction mean | > 30 |
| T2.6 | Statistical significance | p < 0.05 |

---

## The Build Loop

```
1. Scope          → confirm name, target asset, horizon, single dimension — LOCK them
                    Decide: standalone regime OR phase_pair building block?
                    If phase_pair: name the sibling key and ensure it exists
                    (or commit to building it next)
2. Concept        → research framework, list ONE dimension, 2-4 states, indicator candidates with DB codes
                    Write the transmission-mechanism sentence into the draft docstring
                    Pick signal class from the Good Regime §4 decision tree
                    (level-anchored / ROC / quantity-flow / phase-pair)
3. Orthogonality  → **D11 PRE-BUILD GATE** — compute a quick-and-dirty composite
                    from the candidate indicator set, then measure rolling-60m
                    correlation against every registered regime's composite Z
                    column. If any |ρ| > 0.60 → REJECT, redesign indicator set.
                    See "Orthogonality Audit Script" below.
4. Scaffold       → write ix/core/regimes/<subpackage>/<name>.py (one dimension, one prefix)
                    Subpackage = fundamentals / flow / markets / risk (see below)
5. Build          → run regime.build() → DataFrame
6. Measure        → run validate_composition() + vol-normalized spread check
                    For phase_pair regimes, ALSO run validate_composition([self, pair])
7. Sensitivity    → **T1.7** — run audit_regime_sensitivity(). Verdict must be
                    robust or sensitive. Fragile = automatic fail.
8. Diagnose       → if any Tier 1 bar fails, map failures → fixes via Diagnosis Cookbook
9. Refine         → apply fixes, return to step 5
10. Stop iterations when:
    • Tier 1 fully met + T1.7 robust/sensitive → ship
    • Tier 1 fails after 5 iterations → save to ix/core/regimes/_drafts/, diagnostic
    • Tier 0/D11 disqualifier hit → reject immediately, no file
11. Register      → add RegimeRegistration to ix/core/regimes/registry.py with:
                    - category="axis" (mandatory — no other category for new regimes)
                    - phase_pair="sibling_key" IF this is a paired regime
                    - COMPLETE color_map (every state) + dimension_colors (the one dim)
                    - state_descriptions (every state — disambiguates shared names)
                    - asset_tickers (regime-appropriate universe)
12. Persist       → run compute_regime("<key>") — auto-populates asset_analytics
13. Frontend wire → extend ui/src/components/regimes/constants.ts with fallback
                    REGIME_COLORS, REGIME_DESCRIPTIONS, DIMENSION_COLORS entries
14. Smoke test    → run tests/test_regime_smoke.py — MUST pass all 3 tests
                    (registry non-empty, every regime builds, phase_pairs mutual)
15. Visually verify → Claude Preview screenshots of Current State, History,
                      Asset Performance, Model tabs with the new regime
                      selected (single mode). Zero console errors. Tile must
                      appear in the AxisDock with correct color/state.
16. LEARNINGS.md  → append the run report with verdict + screenshots noted,
                    INCLUDING the audit_regime_sensitivity() summary output
17. Suggest combiner → emit one-line invitation to /ix-regime-combiner with
                       the new key included for joint-search experiments
```

**Iteration budget:** 5 for the quality-bar loop (steps 5-9). Steps 11-17 are mandatory shipping steps and do NOT count against the budget.

### Subpackage placement (2026-04-09)

After the grouping refactor, new regime files live in themed subpackages:

| Subpackage | Theme | Example regimes |
|---|---|---|
| `ix/core/regimes/fundamentals/` | Growth, inflation, labor, central-bank policy | growth, inflation, labor, cb_surprise |
| `ix/core/regimes/flow/` | Liquidity, curve, real rates — plumbing signals | liquidity, liquidity_impulse, yield_curve, real_rates |
| `ix/core/regimes/markets/` | Price-based cycles — credit, dollar, commodities | credit_level, credit_trend, dollar_level, dollar_trend, commodity_cycle |
| `ix/core/regimes/risk/` | Sentiment, positioning, volatility, breadth | vol_term, breadth, earnings_revisions, positioning, risk_appetite, dispersion |

Relative imports inside a subpackage file:
```python
from ..base import Regime, load_series, zscore, zscore_anchored
```
Two dots — each subpackage is one level below `ix/core/regimes/`.

### Orthogonality Audit Script (step 3)

```python
import sys; sys.path.insert(0, "D:/investment-x")
import pandas as pd
from ix.core.regimes import list_regimes

# 1. Build candidate composite from your indicator set (rough — no sigmoid)
candidate_indicators = {
    "x_Foo": ...,   # your z-scored series
    "x_Bar": ...,
}
candidate_z = pd.concat(candidate_indicators.values(), axis=1).mean(axis=1)

# 2. For every registered regime, grab its {Dim}_Z and correlate
def _dim_z(reg) -> pd.Series:
    if reg.regime_class is None:
        return pd.Series(dtype=float)
    df = reg.regime_class().build(
        z_window=reg.default_params.get("z_window", 96),
        sensitivity=reg.default_params.get("sensitivity", 2.0),
        smooth_halflife=reg.default_params.get("smooth_halflife", 2),
        confirm_months=reg.default_params.get("confirm_months", 3),
    )
    dim = reg.dimensions[0]
    col = f"{dim}_Z"
    return df[col].dropna() if col in df.columns else pd.Series(dtype=float)

max_rho = 0.0
worst_pair = None
for reg in list_regimes():
    other_z = _dim_z(reg)
    if other_z.empty:
        continue
    joined = pd.concat([candidate_z.rename("new"), other_z.rename("old")],
                       axis=1, join="inner").dropna()
    if len(joined) < 60:
        continue
    rho = abs(joined["new"].rolling(60, min_periods=60)
              .corr(joined["old"]).abs().median())
    if rho > max_rho:
        max_rho = rho
        worst_pair = reg.key

print(f"Worst orthogonality: |ρ|={max_rho:.2f} vs {worst_pair}")
assert max_rho <= 0.60, f"D11 FAIL — candidate composite duplicates {worst_pair} (|ρ|={max_rho:.2f})"
print("D11 orthogonality gate PASSED")
```

---

## Diagnosis Cookbook (failure → fix)

| Failure | Likely cause | Fix |
|---|---|---|
| **D11 orthogonality > 0.60** | Candidate composite duplicates an existing regime | Remove overlapping indicators, pick orthogonal ones, or abandon the concept. See "Double-counting" below. |
| **Vol-normalized spread < 0.25** standalone but regime is cyclical level | Rolling z-score drifts with the cycle itself | Switch to `zscore_anchored(s, anchor, z_window)` at a structural reference value. Cycle-drift fix. |
| **Standalone spread < 0.25** on a trend/ROC regime with HY target | Mean-reversion vs continuation ambiguity at long horizons | The signal may be a phase-pair building block, not a standalone. Declare `phase_pair="<level_sibling>"` and validate the joint composition instead. See `credit_trend` case. |
| **Coverage < 95%** | Series too short / publication gaps | Swap to longer-history proxy, drop weakest indicator |
| **Chattering (persistence < 4)** | Too sensitive composite | Raise `confirm_months` to 4-6, raise `smooth_halflife` to 6-8 |
| **Forward spread low despite clean stats** | Indicators not predictive of target horizon | Compute Spearman IC of each indicator vs target separately; replace bottom-quartile IC indicators. Do NOT retarget. |
| **p > 0.05** | Sample too small or signal random | Extend pre-2000 history if data exists; check whether dimension is actually predictive of target |
| **Some states never observed** | State probability formula degenerate | Re-check `_state_probabilities`; states must sum to 1 at every timestep |
| **Composite NaN > 30%** | Window too long for short series | Shorter `z_window` (24-36) or longer warm-up |
| **T1.7 verdict = fragile** | Sign flip under ±25% parameter perturbation | Regime is overfit to default params. Drop the noisiest indicator; if it still fragile, move to `_drafts/`. |
| **T1.7 verdict = sensitive with many fragile cells** | Shipping is allowed WITH disclosure in the registration description | Document the fragility; note which params drive the sensitivity |
| **Tier 2 OOS unstable** | Overfit to one period | Drop noisiest indicator, prefer broader composites |
| **Drawdown avoidance < 60%** | Regime detects too late | Add a leading indicator (yield curve, claims, breadth) |
| **Sharpe spread fails** | Best regime asset doesn't outperform | Wrong target — re-check whether target asset actually responds to this regime |
| **Conviction mean < 30** | Sigmoid too flat | Raise `sensitivity` parameter, or sharpen indicator z-scores |
| **D9 hit (`len(dimensions) > 1`)** | Tried to build a multi-axis composite | Split into N separate 1D regimes, then use `/ix-regime-combiner` to find the best joint view |

### Three common failure modes discovered 2026-04-09 session

These are the rebuild lessons from the sensitivity audit. Each one is a pattern to recognize BEFORE spending an iteration budget:

**Failure mode A: Double-counting (liquidity v1)**
- Symptom: Regime has 5–6 indicators mixing price signals from different domains (HY OAS, DXY, yield curve, IG spreads) and still posts near-zero vol-normalized spread
- Cause: Each indicator is already captured in another registered regime. The composite is a weighted average of things that are already individually regimes — no orthogonal information remains
- Fix: Strip to indicators that are NOT measured anywhere else. For liquidity → central-bank quantities (G4 BS, Fed Net Liquidity, TGA, credit impulse). For volatility → terminal structure alone (nothing else uses it). For positioning → COT/AAII alone
- Pre-check: Run the D11 orthogonality script in step 3 — you'll catch this before writing code

**Failure mode B: Cycle drift (dollar_level v1, inflation pre-anchor)**
- Symptom: Regime uses rolling `zscore(s, window=96)` on a quantity with ~8-year natural cycles. Grid-search shows it stopped firing mid-cycle
- Cause: 96 months ≈ one full dollar/inflation cycle, so the rolling mean catches up to whatever the cycle has been doing recently. "Strong dollar" stops firing after a decade of structural strength because the rolling mean moved with it
- Fix: Switch to `zscore_anchored(s, anchor, z_window)` at a **structural reference** — basis year value, Fed target, sector-spread neutrality. The rolling std is still used for scale, but the zero point stays fixed
- Pre-check: Step 4 of the Good Regime checklist — if signal is a LEVEL of a quantity with cycles ≈ z_window length, use anchored by default

**Failure mode C: Standalone-vs-composition ambiguity (credit_trend)**
- Symptom: ROC/trend signal posts marginal standalone spread (0.15–0.25 Sharpe delta) and every parameter tweak makes it worse. No clear tuning path to get above the bar
- Cause: On long horizons (6M+), mean reversion dominates continuation. A trend signal alone can't resolve "spreads rising → forward returns down (continuation)" vs "spreads rising → capitulation near → forward returns up (reversion)"
- Fix: Declare the regime as a phase_pair building block. Its partner is the LEVEL version of the same signal. Together, the 4-state joint composition resolves the ambiguity: `Wide+Tightening` = post-capitulation recovery, `Tight+Widening` = top forming. Standalone T1.4 waived, joint T1.4 enforced instead
- Pre-check: For any trend/ROC regime at a ≥ 6M horizon, plan the phase_pair sibling upfront in step 1 (Scope)

---

## Measurement Script (drop into Bash)

Use `validate_composition` — it is the authoritative walk-forward validator and computes vol-normalized spread automatically. Do NOT hand-roll a measurement loop; inconsistencies between scripts were a source of bugs pre-2026-04.

```python
import sys; sys.path.insert(0, "D:/investment-x")
from ix.core.regimes import get_regime
from ix.core.regimes.validate import validate_composition
from ix.core.regimes.sensitivity import audit_regime_sensitivity

KEY = "<regime_key>"           # e.g. "liquidity", "dollar_level"
TARGET = "<TARGET_CODE>"       # e.g. "SPY US EQUITY:PX_LAST"
HORIZON_MONTHS = 6             # forward horizon

reg = get_regime(KEY)
assert len(reg.dimensions) == 1, f"D9: regime is not 1D ({reg.dimensions})"

# ── Standalone validation (Tier 1 bars) ────────────────────────────
r = validate_composition([KEY], TARGET, HORIZON_MONTHS, train_window=24)
print(f"""
REGIME: {KEY}  (1D: {reg.dimensions[0]})
TARGET: {TARGET} @ {HORIZON_MONTHS}M forward returns
─────────────────────────────────────────────
T1.1 Coverage            : {r.n_observations} obs  (need ≥ 24m effective)
T1.2 States observed     : {len(r.per_state)}/{len(reg.states)}
T1.3 Median persistence  : (see snapshot — n/a for validator)
T1.4 Raw spread          : {r.spread * 100:+.2f}%
     Target vol ann      : {r.target_vol_ann * 100:.2f}%
     Vol-normalized      : {r.vol_normalized_spread:+.3f}  (bar ≥ 0.25)
T1.5 Welch p             : {r.welch_p:.4f}  (bar < 0.05)
T1.6 Subsample sign      : {r.subsample_sign_consistent}
     Cohen's d           : {r.cohens_d:+.3f}  (T2.2 bar ≥ 0.30)
     Best / worst state  : {r.best_state} / {r.worst_state}
─────────────────────────────────────────────
""")

# ── If phase_pair, validate the joint composition instead ──────────
if reg.phase_pair:
    joint = validate_composition(
        [KEY, reg.phase_pair], TARGET, HORIZON_MONTHS, train_window=24
    )
    print(f"""
JOINT ({KEY} + {reg.phase_pair}) — T1.4 bar applies HERE for phase_pair
─────────────────────────────────────────────
Raw spread          : {joint.spread * 100:+.2f}%
Vol-normalized      : {joint.vol_normalized_spread:+.3f}  (bar ≥ 0.25)
Welch p             : {joint.welch_p:.4f}
Best / worst state  : {joint.best_state} / {joint.worst_state}
─────────────────────────────────────────────
""")

# ── T1.7 parameter sensitivity ─────────────────────────────────────
audit = audit_regime_sensitivity(KEY, TARGET, HORIZON_MONTHS, quiet=True)
print(audit.summary())
assert audit.verdict in ("robust", "sensitive"), \
    f"T1.7 FAIL — verdict={audit.verdict} (fragile or unknown)"
```

The skill substitutes `<regime_key>`, `<TARGET_CODE>`, and `HORIZON_MONTHS` for the candidate, runs this, and fails the iteration if any assertion fires.

---

## Diagnostic Report Format

After every iteration:

```
REGIME: <name>  (1D)
TARGET: <asset> @ <horizon> forward returns
ITERATION: 3 / 5
─────────────────────────────────────────────
Tier 0 (disqualifiers):  PASS
Tier 1 (mandatory):      6/6
Tier 2 (excellent):      4/6
─────────────────────────────────────────────
Forward return spread: +7.8%   (Bottoming +10.6% vs Weakness +2.8%)
Cohen's d:             +0.42
p-value:               0.026    (significant)
Median persistence:    5 months
Coverage:              98.2% since 2000
Drawdown avoidance:    89% (warning-state cluster)
States observed:       2/2
Conviction mean:       41.4
─────────────────────────────────────────────
VERDICT: PRODUCTION-READY (Tier 1 only)
ACTIONS:
  ✓ ix/core/regimes/dollar.py written
  ✓ Registered in registry.py _register_builtins() (category="axis")
  ✓ Snapshot persisted via compute_regime("dollar_level")
  ✓ Frontend constants.ts extended with state colors + descriptions
  ✓ Preview screenshots captured: AxisDock tile, Current State, History, Asset Performance
  ✓ Logged to LEARNINGS.md

NEXT STEP (suggested):
  /ix-regime-combiner --target EEM US EQUITY:PX_LAST --horizon 6m --include dollar_level
```

---

## Decision Card (MANDATORY final output)

**Outcome goal:** after this skill runs, a PM can look at the Decision Card for 10 seconds and know (a) where we are today, (b) why, (c) what to do, (d) what would flip it. If the card can't answer those four questions, the regime is not useful regardless of p-value.

Every successful ship (Tier 1 or Tier 2) emits this card **in addition to** the diagnostic report:

```
═══════════════════════════════════════════════════════════════
DECISION CARD — <RegimeName>   (1D: <Dimension>)
═══════════════════════════════════════════════════════════════
Today (YYYY-MM):    <State>
Conviction:         <N>%        <DECISIVE / CONTESTED>
Persistence:        <N> months in current state

Top drivers (|z| ranked):
  <indicator1>:  z=<+X.X>   (<direction interpretation>)
  <indicator2>:  z=<+X.X>   (<direction interpretation>)
  <indicator3>:  z=<+X.X>   (<direction interpretation>)

Historical read on <State>:
  <Target> <H>M forward avg:   <+X.X%>  (n=<N> occurrences)
  vs opposite state (<other>): <+X.X%>  (n=<N>)
  Sharpe spread best vs worst: <+X.X>  /  <+X.X>

VERDICT:   <RISK-ON / RISK-OFF / NEUTRAL>
TILT:      <concrete action — e.g. "overweight SPY, underweight TLT">
WATCH:     <what would flip the regime — e.g. "ISM below 48 for 2 months">

Big-drawdown catches (worst-state cluster precedes top-decile 6M DDs):
  2001 dotcom:    <CAUGHT / missed>
  2008 GFC:       <CAUGHT / missed>
  2020 COVID:     <CAUGHT / missed>
  2022 inflation: <CAUGHT / missed>
  Score:          <K>/4
═══════════════════════════════════════════════════════════════
```

### Computation (appended to the measurement script)

```python
# ── Decision Card fields ──────────────────────────────────────────
latest_state = joined.iloc[-1]["state"]
latest_date  = joined.index[-1]
latest_row   = df.loc[latest_date]

# Conviction: smoothed dominant probability at the current edge
s_dom_col = f"S_P_{latest_state}"
conviction_now = float(latest_row.get(s_dom_col, 0.0)) * 100
decisive = "DECISIVE" if conviction_now >= 60 else "CONTESTED"

# Persistence at the current edge: walk back counting same-state months
current_persistence = 0
for ts in reversed(df.index):
    if df.loc[ts, state_col] == latest_state:
        current_persistence += 1
    else:
        break

# Top 3 drivers at current date (|z| ranked, excluding monitor-only)
dim = regime.dimensions[0]
prefix = regime._dimension_prefixes()[dim]
driver_cols = [c for c in df.columns if c.startswith(prefix) and not c.startswith("m_")]
driver_vals = [(c[len(prefix):], float(latest_row[c]))
               for c in driver_cols if pd.notna(latest_row[c])]
driver_vals.sort(key=lambda kv: abs(kv[1]), reverse=True)
top_drivers = driver_vals[:3]

# Per-state counts and means
state_stats = {
    s: {"n": int((joined.state == s).sum()),
        "mean": float(joined[joined.state == s]["fwd_ret"].mean())
               if (joined.state == s).any() else float('nan')}
    for s in regime.states
}

# Drawdown catches: did the worst state cluster around top-decile DDs
# for each crisis window?
crisis_windows = {
    "2001 dotcom":   ("2001-03-01", "2002-10-31"),
    "2008 GFC":      ("2008-01-01", "2009-06-30"),
    "2020 COVID":    ("2020-01-01", "2020-06-30"),
    "2022 inflation":("2022-01-01", "2022-12-31"),
}
catches: dict[str, bool] = {}
for name, (s, e) in crisis_windows.items():
    window = df.loc[s:e, state_col] if s in df.index or True else pd.Series(dtype=object)
    try:
        window = df[state_col].loc[s:e]
        catches[name] = bool((window == worst_state).any())
    except Exception:
        catches[name] = False
catch_score = sum(catches.values())

# Verdict: map latest state to risk-on/off by comparing its historical
# forward return to the cross-state median
state_means = {s: state_stats[s]["mean"] for s in regime.states}
median_ret = float(np.median([v for v in state_means.values() if not np.isnan(v)]))
latest_mean = state_means.get(latest_state, 0.0)
if latest_mean > median_ret + 2:
    verdict = "RISK-ON"
elif latest_mean < median_ret - 2:
    verdict = "RISK-OFF"
else:
    verdict = "NEUTRAL"

# ── Print the card ────────────────────────────────────────────────
print(f"""
═══════════════════════════════════════════════════════════════
DECISION CARD — {regime.name}   (1D: {dim})
═══════════════════════════════════════════════════════════════
Today ({latest_date.strftime('%Y-%m')}):   {latest_state}
Conviction:         {conviction_now:.0f}%        {decisive}
Persistence:        {current_persistence} months in current state

Top drivers (|z| ranked):
""")
for name, z in top_drivers:
    arrow = "↑" if z > 0 else "↓"
    print(f"  {name:<20} z={z:+.2f}  {arrow}")

print(f"""
Historical read on {latest_state}:
  {TARGET.split(':')[0]} {HORIZON_MONTHS}M fwd avg:   {state_stats[latest_state]['mean']:+.2f}%  (n={state_stats[latest_state]['n']})
  vs {worst_state}:           {state_stats[worst_state]['mean']:+.2f}%  (n={state_stats[worst_state]['n']})

VERDICT:   {verdict}
TILT:      <fill in manually based on verdict + target>
WATCH:     <fill in manually — indicators near their flip thresholds>

Big-drawdown catches ({worst_state} state clusters around crises):""")
for name, hit in catches.items():
    marker = "CAUGHT" if hit else "missed"
    print(f"  {name:<18} {marker}")
print(f"  Score:             {catch_score}/4")
print("═══════════════════════════════════════════════════════════════")
```

### Decision Card quality gates

The Decision Card also has its own pass/fail (separate from Tier 1/Tier 2 statistical bars):

| Gate | Requirement | Ship impact |
|---|---|---|
| DC1 | Latest conviction ≥ 60% OR persistence ≥ 6 months | Warn if fails — regime is currently contested |
| DC2 | Top 3 drivers at latest date all non-zero | Block — components must explain current state |
| DC3 | Big-drawdown catches ≥ 2/4 | Warn if fails — regime may be coincident not leading |
| DC4 | Verdict is RISK-ON or RISK-OFF (not NEUTRAL) | Warn if NEUTRAL — signal is ambiguous at current edge |

**DC2 is the only blocker.** A regime whose components are all zero at the current edge is broken — it can't explain its own output and isn't useful as a monitoring tool. DC1, DC3, DC4 emit warnings that go into LEARNINGS.md but don't prevent shipping.

**Manual fill-ins:** `TILT` and `WATCH` are deliberately not auto-generated. The skill writes `<fill in manually based on verdict + target>` and the user/operator fills them in during the ship commit. This forces explicit reasoning about *how* to trade the regime instead of rubber-stamping a stats card.

---

## What Ships When

| Outcome | Subclass file | Registry | Snapshot | Frontend | Preview | Decision Card | LEARNINGS | Combiner |
|---|---|---|---|---|---|---|---|---|
| **Tier 2 passed** | `ix/core/regimes/<name>.py` | `category="axis"` | persisted | constants.ts extended | 4-tab screenshots | emitted + logged | append PASS | emitted |
| **Tier 1 only** | `ix/core/regimes/<name>.py` | "(Tier 1 only)" | persisted | constants.ts extended | 4-tab screenshots | emitted + logged | append TIER-1 | emitted |
| **Tier 1 failed** | `ix/core/regimes/_drafts/<name>.py` | not registered | not persisted | NOT extended | skipped | emitted (diagnostic only) | append FAIL | not emitted |
| **DC2 blocker** | `ix/core/regimes/_drafts/<name>.py` | not registered | not persisted | NOT extended | skipped | emitted + BLOCKED reason | append DC-BLOCKED | not emitted |
| **Tier 0 disqualified** | nothing committed | — | — | — | — | not emitted | append REJECT | not emitted |

Always append to `LEARNINGS.md` regardless of outcome. The Decision Card is emitted to terminal AND copied into the LEARNINGS.md entry for every successful ship so the latest card is always in version control.

---

## Registration Pattern

After Tier 1 or Tier 2 pass, edit `ix/core/regimes/registry.py` `_register_builtins()`:

```python
# Nth. CreditLevelRegime — 1D axis
from .credit_level import CreditLevelRegime
register_regime(RegimeRegistration(
    key="credit_level",
    display_name="Credit Level (Wide × Tight)",
    description=(
        "2-state credit level regime — z-score of HY/IG/BBB OAS vs "
        "rolling 8y history. Target: HYG 6M fwd. "
        "Compose with credit_trend to reconstruct the Verdad cycle."
    ),
    states=["Wide", "Tight"],
    dimensions=["Level"],
    regime_class=CreditLevelRegime,
    default_params=_DEFAULT_PARAMS.copy(),
    has_strategy=False,
    category="axis",                 # MANDATORY — only 1D axis regimes are registered
    asset_tickers={
        "HYG": "HYG US EQUITY:PX_LAST",   # HY credit (most sensitive)
        "LQD": "LQD US EQUITY:PX_LAST",   # IG credit
        "TLT": "TLT US EQUITY:PX_LAST",   # Long Treasuries (flight to quality)
        "IEF": "IEF US EQUITY:PX_LAST",   # Intermediate Treasuries
        "SPY": "SPY US EQUITY:PX_LAST",   # Equity (credit-equity correlation)
        "GLD": "GLD US EQUITY:PX_LAST",   # Gold (crisis hedge)
        "BIL": "BIL US EQUITY:PX_LAST",   # Cash (risk-free proxy)
    },
    color_map={
        "Wide":  "#ef5350",  # red — wide spreads = stress
        "Tight": "#22c55e",  # green — tight spreads = carry
    },
    dimension_colors={"Level": "#ef5350"},
    state_descriptions={
        "Wide":  "Spreads above rolling history — risk premium embedded",
        "Tight": "Spreads below rolling history — carry-friendly conditions",
    },
))
```

Then run from bash:
```python
import sys; sys.path.insert(0, "D:/investment-x")
from ix.core.regimes import compute_regime
fp = compute_regime("credit_level")
print(f"Saved snapshot: {fp}")
```

The frontend auto-discovers new regimes via `/api/regimes/models`. The new tile appears in the AxisDock; users can click it to view it standalone or compose it with other axes.

---

## Frontend Wiring & Verification (MANDATORY after registration)

**Goal:** every registered regime renders correctly on `/macro` — proper tile in the AxisDock, proper state colors, descriptive labels, and no broken UI when selected as the single active regime.

### How the frontend works (read before editing)

- **Page:** `ui/src/app/macro/page.tsx` — AxisDock for selection + tab bar
- **AxisDock:** `ui/src/components/regimes/AxisDock.tsx` — 5-column grid of 1D tiles, each shows live current state
- **Types:** `ui/src/components/regimes/types.ts` — `RegimeModel` includes `color_map`, `dimension_colors`, `states`, `dimensions`
- **Constants:** `ui/src/components/regimes/constants.ts` — fallback `REGIME_COLORS`, `REGIME_DESCRIPTIONS`, `DIMENSION_COLORS` PLUS model-aware helpers (`getRegimeColor`, `getDimensionColor`, `getRegimeDescription`, `getRegimeOrder`)
- **Tab components:** `CurrentStateTab`, `HistoryTab`, `AssetPerformanceTab`, `ModelTab` accept a `model?: RegimeModel` prop and use the helpers. New regimes get correct colors automatically — IF the registration has correct `color_map`/`dimension_colors` AND the fallback constants are extended.

### Mandatory checklist — run these steps after registration

1. **Color map completeness**:

   ```python
   import sys; sys.path.insert(0, "D:/investment-x")
   from ix.core.regimes import get_regime
   r = get_regime("<key>")
   assert len(r.dimensions) == 1, f"D9: registered regime is not 1D ({r.dimensions})"
   assert r.category == "axis", f"category must be 'axis', got {r.category}"
   missing_states = set(r.states) - set(r.color_map.keys())
   missing_dims   = set(r.dimensions) - set(r.dimension_colors.keys())
   assert not missing_states, f"Missing color_map entries: {missing_states}"
   assert not missing_dims,   f"Missing dimension_colors entries: {missing_dims}"
   print("Registration completeness: OK")
   ```

2. **Extend frontend constants.ts fallbacks** — edit `ui/src/components/regimes/constants.ts` and add:
   - Each new state name → hex color in `REGIME_COLORS`
   - Each new state name → one-line description in `REGIME_DESCRIPTIONS`
   - Each new dimension name → hex color in `DIMENSION_COLORS`

   **Color palette convention:**
   - Best/most-positive state → `#22c55e` (green)
   - Warning/transition state → `#f59e0b` (amber)
   - Worst/stress state → `#ef5350` (red)
   - Peak-opportunity state → `#6382ff` (blue)

3. **Description copy** — `<condition> — <market implication>`. Examples:
   - `Wide:  "Spreads above rolling history — risk premium embedded"`
   - `Tight: "Spreads below rolling history — carry-friendly conditions"`

4. **Visual verification via Claude Preview (MANDATORY)**:

   ```
   - Confirm backend is running (port 8001) with the new registration loaded
   - preview_start frontend
   - Navigate to /macro
   - Verify the new tile appears in the AxisDock with correct state + color
   - Click the new tile to enter SINGLE mode (only this regime selected)
   - For each tab in this order: Current State, History, Asset Performance, Model
     - preview_screenshot (or DOM-query for layout assertion if screenshot times out)
     - Verify: regime name displays with correct state color
     - Verify: description appears
     - Verify: dimension card renders for the single declared dimension
     - Verify: probability bars use the model's color_map
     - Verify: History stacked area uses model state order + colors
     - Verify: Asset Performance heatmap shows declared tickers × declared states
   - preview_console_logs --level error — must be empty (or only pre-existing warnings)
   ```

5. **Tile sanity** — query the DOM to confirm the new tile is there:

   ```js
   (() => {
     const tiles = Array.from(document.querySelectorAll('.grid button'));
     return tiles.find(b => b.querySelector('.uppercase')?.textContent?.trim() === '<DisplayName>');
   })()
   ```

### Failure modes and fixes

| Symptom | Cause | Fix |
|---|---|---|
| State name renders in gray (#94a3b8) | Missing from `color_map` AND `REGIME_COLORS` fallback | Add to registration `color_map` + extend `constants.ts` |
| State has no description tagline under the banner | Not in `REGIME_DESCRIPTIONS` | Add one-line description to `constants.ts` |
| Tile missing from AxisDock | Registration `category` not `"axis"` (or `"phase"`) | Set `category="axis"` |
| Compose endpoint fails when this regime is included | New regime returns NaN states or wrong column names | Check `_state_probabilities` returns `P_<state>` keys for every declared state |
| TypeScript compile error after constants edit | Missing trailing comma or typo | Run `npm run build` in `ui/` to validate |

### DO NOT skip frontend verification

A regime that passes Tier 1/Tier 2 quality bars but renders with gray fallback colors and no description on the frontend is NOT shipped. Every run ends with screenshots (or DOM assertions) proving the new regime renders with its declared colors on at least the AxisDock tile, Current State, History, and Asset Performance tabs.

---

## NO Composite Escape Hatch (was removed)

The old "Composite Regime Escape Hatch" pattern (subclassing `RegimeComputer`, overriding `compute()` to join multiple regimes, registering with `regime_class=None`) is **removed as of 2026-04-07**. Composite views are now generated **on demand** by `ix/core/regimes/compose.py::compose_regimes(keys=[...])`, called by the frontend AxisDock when a user picks 2+ regimes.

**If you find yourself wanting to write a composite computer**: stop. Build the constituent 1D axes, register each independently, and run `/ix-regime-combiner` to find the best joint view. The combiner sub-skill empirically searches the space of 2/3/4-axis combinations and reports the strongest joint composition for any target asset.

---

## Discover Mode (no args)

When `/ix-regime-builder` is called with no arguments:

1. Run 3-5 parallel web searches for **1D axis** regime frameworks not yet in the registry:
   - `"yield curve regime" steepening flattening single dimension`
   - `"breadth regime" advance decline thrust single signal`
   - `"earnings revision regime" upgrades downgrades classifier`
   - `"speculation regime" margin debt ipo retail flow`
   - `"volatility regime" VIX low high single axis`

2. Read `ix/core/regimes/registry.py` to see what's already registered. Skip duplicates.

3. For each candidate, output a one-line summary:
   ```
   | Concept | Source | Why interesting | Target asset | Horizon | 1 dimension? | Data available? |
   ```

4. Pick the most promising 1 candidate that is naturally 1D (not a hybrid/multi-signal framework) and run the full build loop on it.

5. Append all candidates (built or not) to LEARNINGS.md so future runs don't re-search.

After shipping, automatically suggest a combiner run to test the new axis against existing ones.

---

## What This Skill Does NOT Do

- **Build multi-dimensional regime classes** → split into 1D parts; use `/ix-regime-combiner` for joint search
- **Build composite computers** (`MacroLiquidityComputer`-style) → REMOVED, use the compose endpoint
- **Search for best joint compositions** → use `/ix-regime-combiner`
- Build raw indicator functions → use `/ix-indicator-lab`
- Build allocation strategies on top of regime → use `/ix-strategy-builder`
- Run Streamlit dashboards or experiments → use `/ix-model-lab`
- Build new tab components for the regime page → existing tabs are reused via model-aware helpers
- Rewrite the frontend page shell → only edits `constants.ts` and verifies rendering
- Backtest specific allocation rules conditional on regime → strategy land
- Recommend trades

---

## LEARNINGS.md Format

Each attempt appends:

```markdown
## 2026-04-07 — credit_level (HYG @ 6M)

- Dimension: Level (single)
- Indicators: lv_HY_OAS, lv_IG_OAS, lv_BBB_OAS
- Verdict: PRODUCTION-READY (Tier 1 only)
- Tier 1: 6/6, Tier 2: 3/6
- Spread: +6.79% (Recovery -0.5% vs LateCycle +1.30%)
- Cohen's d: +0.42
- p-value: 0.0001
- Key finding: 3M ROC for trend dimension is the right horizon
- Combiner suggestion: /ix-regime-combiner --target HYG US EQUITY:PX_LAST --horizon 6m --include credit_level,credit_trend
```

For failures:

```markdown
## 2026-04-07 — china_property (FXI @ 12M)

- Dimension: Activity (single — proposed)
- Indicators: a_PropertySales, a_DeveloperBonds, a_LandAuction
- Verdict: TIER-1 FAILED
- Tier 1: 3/6 (failed T1.1 coverage 67%, T1.4 spread 2.1%, T1.5 p=0.34)
- Key finding: China property data has huge gaps pre-2015. Not buildable from current DB.
- Next: ingest CN.PROPERTY:* series before retrying
```

---

## Sub-Skill: ix-regime-combiner

After shipping any new 1D regime, the parent skill (this one) hands off to **`ix-regime-combiner`** for joint composition search:

- **Location:** `D:/investment-x/.claude/skills/ix-regime-combiner/SKILL.md`
- **Purpose:** Given a target asset + horizon, search across all registered 1D regimes to find the strongest 2/3/4-axis joint composition. Empirical only — no hand-coded logic.
- **Output:** Ranked list of top combinations with Cohen's d, Welch p, permutation p, OOS stability, joint state spread.
- **Invocation:**
  ```
  /ix-regime-combiner                                           # default: SPY 6M, all axes
  /ix-regime-combiner --target HYG --horizon 6m
  /ix-regime-combiner --include credit_level,credit_trend       # constrain to subset
  /ix-regime-combiner --target SPY --horizon 3m --max-axes 3
  ```

The parent skill will emit the recommended invocation as the final line of every successful run.

---

## Final Reminders

- **Lead with the outcome** — every shipped regime must answer "where are we, why, what to do, what flips it" via its Decision Card
- **Always read `base.py` + `STANDARD.md` before scaffolding** — the contract evolves
- **Always pick a signal class from the Good Regime §4 decision tree** — level-anchored / ROC / quantity / phase-pair
- **Always run the D11 orthogonality check in the Concept step** — before writing code
- **Always use `LW=0.25, RW=0.75` blend for ROC regimes** — empirically validated
- **Always use `zscore_anchored` for cyclical-level regimes** — rolling z-score drifts with the cycle
- **Always lock target before measurement** — no retargeting after seeing results
- **Always run `validate_composition` + `audit_regime_sensitivity`** — never hand-roll a measurement loop
- **Always emit the Decision Card** — a regime that can't explain its current state (DC2) does not ship
- **Always exactly one dimension** — `len(dimensions) == 1` is enforced as D9
- **For phase-paired regimes, validate the JOINT** — `credit_trend` alone is 0.21 Sharpe delta, joint with `credit_level` is 0.94. Same logic for `dollar_level ↔ dollar_trend` and `liquidity ↔ liquidity_impulse`.
- **Never import `MacroRegime`** — the 2D class was retired 2026-04-09 (D10). Use `fundamentals/loaders.py` for shared growth/inflation loaders.
- **Never rubber-stamp the TILT / WATCH fields** — they must be filled in manually during the ship commit
- **After shipping, always emit the combiner invocation** — that's how 1D regimes become useful joint views
- **If T1.7 comes back fragile** — the regime is overfit. Do not ship. Drop the noisiest indicator or move to `_drafts/`.
