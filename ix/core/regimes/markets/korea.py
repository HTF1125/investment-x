"""KoreaRegime — 2-state Korean equity regime (empirically rebuilt).

Thesis
------
Korean equity forward returns at 3-6M horizons are driven by two
independent channels that the audit (scripts/audit_korea.py,
gitignored) found to be the strongest predictors out of 30 tested
candidate indicators:

    1. CONTRARIAN risk channels
       - KRW realised volatility — high = panic / EM outflows already
         occurred → mean-reversion forward
       - HY credit spread level — wide = credit stress already priced
         → positive forward returns historically
    2. MOMENTUM channels
       - MCHI (China broader) 6M momentum — China demand leads Korean
         exports; MCHI post-2010 IC on KOSPI is ~2x FXI
       - Korea 10Y-3Y yield curve 3M change — steepening = growth
         expectations rising, Korea-specific rate signal

All four are measured as post-2010 Spearman IC > |0.19| with p < 0.01
on both KOSPI and EWY targets. The prior thematic set (SOX momentum,
FXI momentum, USDKRW change) was largely noise at these horizons
because the semi cycle and spot FX are priced into KOSPI in close to
real-time.

**Hard rule compliance**
- Hard Rule #3 (don't invert contrarian gauges): KRW_Vol and HYOAS
  are NOT inverted. High level → high z → predicts positive forward
  return = contrarian bullish. Compliant.
- Hard Rule #4 (no Global M2): none used.
- Hard Rule #2 (walk-forward): regime pipeline is causal by default.

**Semantics note**: the composite z mixes momentum (MCHI, KR yield
curve) and contrarian stress (KRW_Vol, HYOAS) in the same dimension.
Both channels produce POSITIVE forward-return IC when taken raw, so
they're additive in the composite — but the "Expansion" state label
means "composite predicts positive forward returns," which can come
from either strong macro conditions (momentum side) or stressed /
washed-out conditions that mean-revert (contrarian side). This is
the same pattern the existing `risk_appetite` regime uses.

States
------
- **Expansion**   (Korea_Z > 0): composite predicts positive KOSPI
  forward returns. Could be driven by strong China + steepening KR
  curve (momentum setup) OR high KRW vol + wide HY spreads (contrarian
  mean-reversion setup). Both channels point the same direction.
- **Contraction** (Korea_Z ≤ 0): the opposite — weak China, flat curve,
  calm FX, tight spreads. "Complacent" setup with below-average forward
  returns.

Indicators (4, all k_*)
    k_KRW_Vol       — USDKRW 20-day realised volatility (annualised).
                      Contrarian: high vol = risk-off already happened
                      = positive forward return.
    k_HYOAS_level   — ICE BofA HY Master OAS level (BAMLH0A0HYM2).
                      Contrarian: wide spreads = credit stress already
                      priced = positive forward return.
    k_MCHI_6M       — MCHI (China broader ETF) 6M momentum. NOT
                      inverted. Direct signal.
    k_KR_YC_3M      — Korea 10Y-3Y yield curve 3M change. NOT inverted.
                      Steepening = growth expectations rising.

Publication lag: zero (all market data).
Target: KOSPI INDEX:PX_LAST at 3M forward.

Target note: KOSPI chosen over EWY because EWY adds KRW/USD FX
variance on top of the economic signal. On this indicator set, KOSPI
3M d ≈ EWY 3M d (FX noise is dampened by using KRW_Vol as an input),
but KOSPI has slightly cleaner ICs per the audit. Traders targeting
EWY can use this signal directly or compose with dollar_trend.

History / audit notes
---------------------
- 2026-04-12 v2 rebuild: dropped k_SOX_6M (post-2010 IC -0.017 on
  KOSPI 1M, near-zero at 3M — semi cycle is priced too efficiently at
  monthly frequency), k_China_6M (FXI replaced with MCHI which has
  +0.06 higher post-2010 IC), and k_USDKRW_3M (post-2010 IC -0.018 on
  KOSPI 1M, essentially noise; replaced with the realised-vol variant
  which is contrarian and strongly significant). Full audit:
  scripts/_korea_audit_report.md (gitignored).
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from ..base import Regime, load_series as _load, zscore

log = logging.getLogger(__name__)


class KoreaRegime(Regime):
    """2-state Korean equity regime (Expansion × Contraction)."""

    name = "Korea"
    dimensions = ["Korea"]
    states = ["Expansion", "Contraction"]

    # ── Indicators ───────────────────────────────────────────────────────

    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        rows: dict[str, pd.Series] = {}

        # k_KRW_Vol — USDKRW 20-day realised volatility (annualised).
        # NOT inverted. Strongest post-2010 IC on KOSPI (|IC|=0.279 at
        # 3M, 0.327 at 6M). Contrarian channel per Hard Rule #3:
        # spikes in KRW vol correspond to EM outflow events that have
        # already happened; forward returns mean-revert positive.
        usdkrw = _load("USDKRW Curncy:PX_LAST")
        if not usdkrw.empty:
            krw_vol = usdkrw.pct_change().rolling(20).std() * float(np.sqrt(252))
            rows["k_KRW_Vol"] = zscore(krw_vol, z_window).rename("k_KRW_Vol")

        # k_HYOAS_level — ICE BofA HY Master Option-Adjusted Spread.
        # NOT inverted (Hard Rule #3 — credit spreads are contrarian
        # at wide extremes). Wide HY spreads = credit stress already
        # priced into equities globally = positive forward return
        # for high-beta EM like Korea. Post-2010 IC +0.192 (KOSPI 3M),
        # +0.290 (KOSPI 6M).
        hy = _load("BAMLH0A0HYM2")
        if not hy.empty:
            rows["k_HYOAS_level"] = zscore(hy, z_window).rename("k_HYOAS_level")

        # k_MCHI_6M — MSCI China ETF (MCHI), 6M momentum. NOT inverted.
        # Direct momentum signal: when broader China equity is trending
        # up, Korean exporter demand strengthens 1-3 months later. MCHI
        # post-2010 IC +0.227 (KOSPI 3M) beats FXI's +0.148 because
        # MCHI is broader than FXI's large-cap focus. 3779 obs since
        # 2011-03 — shorter history than FXI but stronger signal.
        mchi = _load("MCHI US EQUITY:PX_LAST")
        if not mchi.empty:
            rows["k_MCHI_6M"] = zscore(
                mchi.pct_change(6, fill_method=None) * 100.0, z_window
            ).rename("k_MCHI_6M")

        # k_KR_YC_3M — Korea 10Y-3Y yield curve, 3M change. NOT inverted.
        # Steepening curve = market pricing in accelerating Korean growth
        # / BOK easing = bullish Korean equities. Korea-specific channel
        # unavailable elsewhere in the registry. Uses KR 10Y (6362 obs
        # since 2000) and KR 3Y (6921 obs since 1998) directly.
        kr10 = _load("TRYKR10Y:PX_YTM")
        kr3 = _load("TRYKR3Y:PX_YTM")
        if not kr10.empty and not kr3.empty:
            yc = (kr10 - kr3.reindex(kr10.index, method="ffill")).dropna()
            rows["k_KR_YC_3M"] = zscore(yc.diff(3), z_window).rename("k_KR_YC_3M")

        if not rows:
            log.warning(
                "Korea: no indicators loaded. Expected DB codes: "
                "'USDKRW Curncy:PX_LAST', 'BAMLH0A0HYM2', "
                "'MCHI US EQUITY:PX_LAST', 'TRYKR10Y:PX_YTM', "
                "'TRYKR3Y:PX_YTM'."
            )
        return rows

    # ── Composite overrides ──────────────────────────────────────────────

    def _dimension_prefixes(self) -> dict[str, str]:
        return {"Korea": "k_"}

    # ── State probabilities ──────────────────────────────────────────────

    def _state_probabilities(
        self, dim_probs: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:
        """Map Korea composite probability to 2 states.

        High composite z (strong China + steepening KR curve + high KRW
        vol + wide HY spreads — any mix) → Expansion → forward-return
        positive. Low composite z → Contraction → forward-return
        negative. See module docstring for semantic explanation of the
        momentum / contrarian channel mix.
        """
        kp = dim_probs["Korea"]
        return {
            "P_Expansion":   kp,
            "P_Contraction": 1.0 - kp,
        }
