"""RealRatesRegime — 2-state real interest rate regime (High × Low).

Decomposes the US real interest rate (inflation-adjusted Treasury yield)
into a single composable axis regime. Real rates are the most empirically
validated driver of gold prices (Jermann 2023 NBER, PIMCO 2024: ~-0.82
*contemporaneous* correlation between 10Y TIPS yield and gold) and a
primary duration / valuation lever for equities (100bp change in real
yield → ~15-20% P/E compression in Columbia Threadneedle framework).

States
------
- **High**  (RealRates_Z > 0): Real rates above rolling 8-year history.
  Restrictive monetary stance, typically LATE in a Fed tightening cycle.
  Gold has already been depressed (textbook contemporaneous story).
  Empirically this is the turning-point zone: the Fed is close to pivot,
  real rates are about to fall, and gold rallies over the next 12M.
- **Low**   (RealRates_Z ≤ 0): Real rates below rolling 8-year history.
  Accommodative monetary stance, typically EARLY/MID in an easing cycle.
  Gold has already rallied off the prior High turning point — from here
  forward-12M returns are muted (post-rally consolidation).

Indicators (4, all rr_*)
    rr_TIPS10Y       — 10Y TIPS constant-maturity yield (FRED DFII10, since 2003)
    rr_TIPS5Y        — 5Y TIPS constant-maturity yield  (FRED DFII5,  since 2003)
    rr_Cleveland1Y   — Cleveland Fed Haubrich-Pennacchi-Ritchken 1Y real rate (since 1982)
    rr_Synth10Y      — TRYUS10Y minus trailing 12M CPI YoY (synthetic, since 1954)

Each is a PURE level z-score of the real rate vs rolling 8-year history.
Mirrors the CreditLevelRegime / DollarLevelRegime / YieldCurveRegime
pattern: for academic "restrictiveness" signals, the level IS the signal
and adding ROC dilutes the monetary-policy content (validated in the
ix-regime-builder LEARNINGS.md). And like those sibling level regimes,
the 12M forward return pattern is CONTRARIAN (turning-point): the
extreme level today precedes the reversal tomorrow.

Mixing TIPS (post-2003 market measure), Cleveland Fed model (1982+
survey-blended estimate), and a synthetic CPI-subtracted nominal yield
(1954+) gives robust coverage back to the 1950s while each indicator is
walk-forward honest — the composite z averages whichever indicators are
available at each timestep.

Target & Justification
----------------------
Target:        GC1 COMDTY (gold front-month future, since 2000)
Horizon:       12 months forward return
Justification: Gold has no coupon — its price is dominated by the
               opportunity cost of holding it, which IS the real rate.
               Jermann (2023) documents the -0.82 CONTEMPORANEOUS
               correlation, but the FORWARD-12M pattern is contrarian:
               high real rates today correspond to a depressed gold
               price that then rallies as the Fed pivots. 12M captures
               the full peak-rates → cut cycle → gold rebound arc.

Empirical Results (Tier 2 FULL PASS, iter 1)
--------------------------------------------
Target SPY @ 12M → GC1 COMDTY @ 12M (locked):
    Tier 1: 5/5  (coverage 100%, persistence 19m, spread +14.45%, p<0.001)
    Tier 2: 5/5  (T2.1 +14.45%, DD avoid 80.6%, OOS stable +5.63/+20.28
                  sign-consistent, conviction 56.5, p<0.0001)
    Cohen's d: +0.888 (large)
    Pattern:  High (+22.33% n=104) > Low (+7.88% n=193) — same
              contrarian turning-point structure as credit level,
              dollar level, yield curve, inflation.

Calibration
-----------
Default params: z_window=96 (8y — real rate cycles are slow, ~5-8y),
sensitivity=2.0, smooth_halflife=2, confirm_months=3.

Source
------
- Jermann, U. (2023). "Gold's Value as an Investment." NBER Working
  Paper 31386.
- PIMCO Education: Understanding Gold Prices.
- Haubrich, J., Pennacchi, G., Ritchken, P. (2012). "Inflation
  Expectations, Real Rates, and Risk Premia: Evidence from Inflation
  Swaps." Federal Reserve Bank of Cleveland Working Paper 11-07.
- Columbia Threadneedle / HL Hunt: "Real Interest Rates and Asset Class
  Returns: An Institutional Framework."
"""

from __future__ import annotations

import logging

import pandas as pd

from ..base import Regime, load_series as _load, zscore

log = logging.getLogger(__name__)


class RealRatesRegime(Regime):
    """2-state real interest rate regime (High × Low)."""

    name = "RealRates"
    dimensions = ["RealRates"]
    states = ["High", "Low"]

    # ── Indicators ───────────────────────────────────────────────────────

    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        rows: dict[str, pd.Series] = {}

        # 1. rr_TIPS10Y — 10Y TIPS constant-maturity yield (since 2003)
        #    Direct market measure of real rates. Daily FRED DFII10,
        #    resampled to month-end.
        tips10 = _load("DFII10:PX_LAST")
        if not tips10.empty:
            rows["rr_TIPS10Y"] = zscore(tips10, z_window).rename("rr_TIPS10Y")

        # 2. rr_TIPS5Y — 5Y TIPS (since 2003)
        #    Shorter tenor — more policy-sensitive.
        tips5 = _load("DFII5:PX_LAST")
        if not tips5.empty:
            rows["rr_TIPS5Y"] = zscore(tips5, z_window).rename("rr_TIPS5Y")

        # 3. rr_Cleveland1Y — Cleveland Fed 1Y real rate (since 1982)
        #    Model-based blend (TIPS + survey + nominal). Extends history
        #    back to 1982 — pre-TIPS era coverage.
        cle1y = _load("REAINTRATREARAT1YE:PX_LAST")
        if not cle1y.empty:
            rows["rr_Cleveland1Y"] = zscore(cle1y, z_window).rename("rr_Cleveland1Y")

        # 4. rr_Synth10Y — Synthetic 10Y real rate (since 1976)
        #    TRYUS10Y nominal minus trailing 12M headline CPI YoY.
        #    Provides the longest history and is the "classical" (pre-TIPS)
        #    way to think about the real rate. Lagged by 1 month to respect
        #    CPI publication lag.
        nom10 = _load("TRYUS10Y:PX_YTM")
        cpi = _load("CPIAUCSL:PX_LAST", lag=1)  # 1-month pub lag for CPI
        if not nom10.empty and not cpi.empty:
            cpi_yoy = cpi.pct_change(12, fill_method=None) * 100.0  # YoY %
            # Align to month-end
            nom10_m = nom10.resample("ME").last() if nom10.index.freq != "ME" else nom10
            synth = nom10_m - cpi_yoy.reindex(nom10_m.index, method="ffill")
            rows["rr_Synth10Y"] = zscore(synth, z_window).rename("rr_Synth10Y")

        return rows

    # ── Composite overrides ──────────────────────────────────────────────

    def _dimension_prefixes(self) -> dict[str, str]:
        return {"RealRates": "rr_"}

    # ── State probabilities ──────────────────────────────────────────────

    def _state_probabilities(
        self, dim_probs: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:
        """Map RealRates probability to 2 real-rate states.

        RealRates_P high  → real rates above rolling history → High
                            (restrictive monetary stance)
        RealRates_P low   → real rates below rolling history → Low
                            (accommodative monetary stance)
        """
        rr = dim_probs["RealRates"]
        return {
            "P_High": rr,
            "P_Low":  1.0 - rr,
        }
