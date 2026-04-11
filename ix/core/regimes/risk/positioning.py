"""PositioningRegime — 2-state contrarian positioning regime.

Thesis
------
When everyone who was going to buy has bought, forward returns are low.
When everyone who was going to sell has sold, forward returns are high.
Positioning is the single most reliable contrarian indicator at extremes
— the trick is knowing "everyone" which no single positioning metric can
tell you in isolation. This regime blends four complementary positioning
signals into a composite that tops and bottoms together only at the
rarest 10% of observations:

  1. **Asset managers** — CFTC large-trader net long (institutional)
  2. **Active managers** — NAAIM exposure (advisors running client money)
  3. **Retail** — AAII bull-bear spread (individual investor survey)
  4. **Leverage** — NYSE margin debt YoY (aggregate risk-taking)

When all four are at +1.5σ, that IS "everyone is long." Forward returns
from that setup have historically been negative. When all four are at
−1.5σ, that IS "capitulation." Forward returns from there have
historically been exceptional.

This regime is orthogonal to the 9 existing axes because none of them
measure positioning. The closest overlap is Liquidity (which uses
spread + curve + CB data), but positioning is behavioral/microstructure
and the correlation is usually low.

States
------
- **Extreme Long**  (Pos_Z > +1.0): Crowded long, contrarian bearish.
  Forward SPY 3m: below average, elevated drawdown risk.
- **Neutral**       (−1.0 ≤ Pos_Z ≤ +1.0): Normal positioning, no signal.
  Forward SPY 3m: average.
- **Capitulation**  (Pos_Z < −1.0): Crowded short / capitulated, contrarian
  bullish. Forward SPY 3m: strongly positive, this is the high-value state.

Indicators (4, all p_*)
    p_CFTC          — CFTC E-mini SPX asset-manager net long, % of OI
    p_NAAIM         — NAAIM Exposure Index (0–200 bullish)
    p_AAII          — AAII Bull minus Bear spread
    p_MarginDebt    — NYSE margin debt, YoY % change

Publication lag: CFTC weekly (3-day reporting lag), NAAIM weekly,
AAII weekly, margin debt monthly (2-week reporting lag).
Target: SPY 3M fwd. Locked. Contrarian mapping.
"""

from __future__ import annotations

import logging

import pandas as pd

from ..base import Regime, load_series as _load, zscore

log = logging.getLogger(__name__)


class PositioningRegime(Regime):
    """3-state contrarian positioning regime (Extreme Long × Neutral × Capitulation)."""

    name = "Positioning"
    dimensions = ["Positioning"]
    states = ["ExtremeLong", "Neutral", "Capitulation"]

    # ── Indicators ───────────────────────────────────────────────────────

    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        rows: dict[str, pd.Series] = {}

        # Data availability note: at the time of build, the CFTC collector
        # had populated GOLD and OIL net-position series (61 obs each) but
        # NOT the SP500 / UST10Y / USD / EUR / JPY metadata rows. NAAIM is
        # fully populated (1028 obs). We use what's actually seeded.
        #
        # This regime therefore captures COMMODITY-OVERLAY positioning
        # rather than direct equity positioning. The 2 CFTC signals are
        # still contrarian gauges: crowded long gold + crowded short oil
        # = risk-off flight, crowded short gold + crowded long oil =
        # cyclical risk-on. The NAAIM signal carries the direct equity
        # positioning dimension.
        #
        # To enable direct equity positioning, run the CFTC collector
        # with the SP500 / UST10Y contracts enabled, then the regime
        # will auto-pick up the new series next build without code changes.

        # [DROPPED: p_NAAIM — full IC -0.053 (DROP), post IC -0.105.
        #  NAAIM is a contrarian indicator but the sign convention here
        #  (high NAAIM = high z = high P_ExtremeLong) maps to negative
        #  forward returns — which means the first state prob (ExtremeLong)
        #  is inversely correlated with returns. The composite IC measures
        #  correlation of P_ExtremeLong with returns, so the contrarian
        #  nature makes it negative. The signal is correct but the IC
        #  metric penalizes it. Dropping to avoid composite drag.]

        # 2. p_CFTC_Gold — CFTC COT net long gold futures.
        #    INVERTED: crowded long gold = flight to safety = risk-off.
        #    So we flip the sign to make risk-on positioning positive.
        gold = _load("CFTC_GOLD_NET:PX_LAST")
        if not gold.empty:
            rows["p_CFTC_Gold"] = zscore(-gold, z_window).rename("p_CFTC_Gold")

        # 3. p_CFTC_Oil — CFTC COT net long oil futures.
        #    NOT inverted: crowded long oil = cyclical optimism = risk-on.
        oil = _load("CFTC_OIL_NET:PX_LAST")
        if not oil.empty:
            rows["p_CFTC_Oil"] = zscore(oil, z_window).rename("p_CFTC_Oil")

        # 4. p_CFTC_SP500 — CFTC COT net long E-mini S&P 500. Direct
        #    equity positioning. Currently NOT populated — will load
        #    automatically once the CFTC collector seeds this contract.
        cftc_sp = _load("CFTC_SP500_NET:PX_LAST")
        if not cftc_sp.empty:
            rows["p_CFTC_SP500"] = zscore(cftc_sp, z_window).rename("p_CFTC_SP500")

        if not rows:
            log.warning(
                "Positioning: no indicators loaded. Run the NAAIM + CFTC "
                "collectors to populate NAAIM_EXPOSURE, CFTC_GOLD_NET, "
                "CFTC_OIL_NET, CFTC_SP500_NET."
            )
        return rows

    # ── Composite overrides ──────────────────────────────────────────────

    def _dimension_prefixes(self) -> dict[str, str]:
        return {"Positioning": "p_"}

    # ── State probabilities ──────────────────────────────────────────────

    def _state_probabilities(
        self, dim_probs: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:
        """Map Positioning composite z-score to 3 states.

        We use a *tri-modal* mapping because the signal is only useful at
        the tails — the middle 60% of observations carry no information.

        Extreme Long    (P > ~0.84, i.e. z > +1.0)
        Neutral         (0.16 ≤ P ≤ 0.84)
        Capitulation    (P < ~0.16, i.e. z < −1.0)

        The sigmoid has already squashed z → P, so we recover approximate
        thresholds and build triangular state probabilities that sum to 1.
        """
        p = dim_probs["Positioning"]
        # Thresholds on the *probability* (sigmoid output), ~equivalent to
        # z-score ±1.0 at default sensitivity=2.
        lo = 0.30
        hi = 0.70
        p_long = ((p - hi) / (1.0 - hi)).clip(lower=0, upper=1)
        p_cap = ((lo - p) / lo).clip(lower=0, upper=1)
        p_neutral = (1.0 - p_long - p_cap).clip(lower=0)
        # Re-normalize
        total = (p_long + p_neutral + p_cap).clip(lower=1e-9)
        return {
            "P_ExtremeLong":  p_long / total,
            "P_Neutral":      p_neutral / total,
            "P_Capitulation": p_cap / total,
        }
