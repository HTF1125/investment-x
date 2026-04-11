"""KoreaRegime — 2-state Korean equity market regime.

Thesis
------
Korea is a unique EM macro cell: ~30% of KOSPI market cap is concentrated
in semiconductors (Samsung Electronics + SK Hynix), making Korean equity
the most direct public-market proxy for the global memory / logic cycle.
On top of that Korea is China's 3rd-largest trading partner and a high-
beta risk-on / risk-off EM. Forward EWY returns are driven by the joint
product of:

    1. global semi cycle       — SOX (Philadelphia Semi) momentum
    2. China demand            — FXI (China large cap) momentum
    3. KRW FX regime           — USDKRW change (inverted)
    4. USD strength            — DXY change (inverted, EM headwind)

This regime blends the four into a single Expansion / Contraction signal
for EWY. It is intentionally complementary to the existing `global_liquidity`
(broad EM liquidity) and `dollar_trend` (US-centric FX) regimes — nothing
else in the registry isolates Korea-specific drivers (the semi cycle and
China trade in particular).

**Hard rule compliance:** this does not invert any contrarian gauge
forbidden by Hard Rule #3 (VIX / FCI / put-call). KRW and DXY are
inverted so that "EM risk-on" (falling USD, strengthening KRW) maps to
a positive composite z — that's a sign convention, not a contrarian trick.
No Global M2 (Hard Rule #4).

States
------
- **Expansion**   (Korea_Z > 0): semi cycle rising, China momentum
  positive, DXY weakening, KRW firming. Forward EWY 3M: positive.
- **Contraction** (Korea_Z ≤ 0): semi cycle falling, China momentum
  rolling over, DXY strengthening, KRW weakening. Forward EWY 3M:
  negative. The actionable state.

Indicators (3, all k_*)
    k_SOX_6M     — SOX Index, 6M momentum. Semi cycle proxy.
    k_China_6M   — FXI 6M momentum. Chinese demand proxy for Korean
                   exports.
    k_USDKRW_3M  — USDKRW 3M change, INVERTED. Rising KRW strength
                   (falling USDKRW ratio) = EM risk-on = bullish Korea.

[Tested but dropped: k_DXY_3M. DXY has 55 years of history which
extended the composite back to 1971, but pre-2004 Korean equity
dynamics (pre-Samsung semi dominance, pre-China WTO integration,
post-Asian Financial Crisis recovery) differ materially from post-
2004, and the regime lost signal when those samples were mixed in:
d=+0.22 on KOSPI 3M without DXY (n=244, effective post-2004 window)
vs d=+0.01 with DXY (n=350 including pre-2004). DXY is also already
captured by the separate dollar_trend regime; compose the two when a
dollar dimension is needed rather than re-importing it here.]

Publication lag: zero (all market data).
Target: KOSPI INDEX:PX_LAST at 3M forward.

Target note: KOSPI is the cleanest target because it's the local-currency
index — the composite directly predicts Korean economic conditions without
KRW/USD FX noise on top. EWY is the tradeable USD proxy for US investors;
its forward returns equal KOSPI plus KRW/USD, so the regime's KOSPI signal
combined with a separate FX view determines the EWY forecast. Empirically
the Korea composite gives d=+0.22 on KOSPI 3M fwd vs d=+0.09 on EWY 3M fwd
(the extra FX variance on EWY dilutes the economic signal).
"""

from __future__ import annotations

import logging

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

        # k_SOX_6M — Philadelphia Semi Index, 6M momentum. Korea is
        # ~30% semi by market cap (Samsung, SK Hynix); SOX is the
        # cleanest public-market proxy for the global memory / logic
        # inventory cycle. 32-year history (since 1994).
        sox = _load("SOX INDEX:PX_LAST")
        if not sox.empty:
            rows["k_SOX_6M"] = zscore(
                sox.pct_change(6, fill_method=None) * 100.0, z_window
            ).rename("k_SOX_6M")

        # k_China_6M — FXI (China large cap ETF), 6M momentum. China
        # is Korea's largest trading partner; Chinese equity momentum
        # leads Korean exporter demand by 1-3 months. 22-year history.
        fxi = _load("FXI US EQUITY:PX_LAST")
        if not fxi.empty:
            rows["k_China_6M"] = zscore(
                fxi.pct_change(6, fill_method=None) * 100.0, z_window
            ).rename("k_China_6M")

        # k_USDKRW_3M — USDKRW 3M change, INVERTED. Historically the
        # "flow channel" (KRW weakens when global EM outflows sell
        # Korean equities) dominates the "exporter margin channel"
        # (weak KRW boosts Samsung's USD revenues) at the 3M horizon,
        # so strong KRW / falling USDKRW is the bullish signal.
        usdkrw = _load("USDKRW Curncy:PX_LAST")
        if not usdkrw.empty:
            rows["k_USDKRW_3M"] = zscore(
                -usdkrw.pct_change(3, fill_method=None) * 100.0, z_window
            ).rename("k_USDKRW_3M")

        # [DROPPED: k_DXY_3M — adding it extended the composite back to
        #  1971 (DXY has 55y of history) and diluted cohen's d on KOSPI
        #  3M from +0.22 to +0.01 because pre-2004 Korean equity
        #  dynamics differ materially from post-2004. DXY is also
        #  captured by the separate dollar_trend regime — compose with
        #  that rather than double-importing the signal here.]

        if not rows:
            log.warning(
                "Korea: no indicators loaded. Expected DB codes: "
                "'SOX INDEX:PX_LAST', 'FXI US EQUITY:PX_LAST', "
                "'USDKRW Curncy:PX_LAST'."
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

        High composite z (semi + China + strong KRW + weak DXY aligned)
        → Expansion. Low composite z → Contraction.
        """
        kp = dim_probs["Korea"]
        return {
            "P_Expansion":   kp,
            "P_Contraction": 1.0 - kp,
        }
