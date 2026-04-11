"""DispersionRegime — 2-state cross-sectional dispersion regime.

Thesis
------
Dispersion is the width of the distribution of individual stock returns
across the index. When dispersion is low, returns are compressed around
the mean — everything moves together and stock picking is futile. When
dispersion is high, single-name selection dominates and sector rotation
pays. Correlation is the flip side: high correlation → low dispersion
(macro-driven), low correlation → high dispersion (stock-picker's
market).

This regime is NOT primarily a directional signal — it's a *strategy
selection* signal. It tells the system "at this moment, does broad
market beta dominate, or does single-name / sector dispersion dominate?"
The directional content shows up only at the extreme: very high
dispersion combined with very high correlation is a crisis state, and
forward SPY returns are below average in that combination.

**Orthogonality:** fully orthogonal to the existing 9 axes — none of
them measure cross-sectional dispersion. This is a microstructure
signal that lives alongside the macro axes rather than competing with
them.

States
------
- **MacroDriven**  (Disp_Z < −0.5σ): Low dispersion, high correlation.
  Everything moves together. Forward SPY 3m: average; strategy signal =
  prefer index over single-name.
- **Crisis**       (Disp_Z > +1.5σ in addition to high correlation):
  High dispersion AND high correlation simultaneously. Rare, tail
  state. Forward SPY 3m: significantly negative (this is the DotCom
  top / 2008 / 2020-March footprint).
- **StockPicking** (Disp_Z > +0.5σ): High dispersion, normal correlation.
  Single-name dispersion. Forward SPY 3m: average; strategy signal =
  rotation opportunities.

Indicators (3, all ds_*)
    ds_CrossSec       — Cross-sectional stdev of SPX constituent monthly
                        returns, 60d rolling window
    ds_ImpCorr        — CBOE implied correlation (ICJ / ICJ2 index)
    ds_SectorSpread   — Best-sector minus worst-sector return, 60d

Publication lag: zero (market data) or 1 day.
Target: SPY 3M fwd. Locked.

Status: DRAFT — the cross-sectional stdev calculation requires access
to SPX constituent returns which may not be in the timeseries store as
a single pre-computed series. If absent, only ds_ImpCorr and
ds_SectorSpread will load.
"""

from __future__ import annotations

import logging

import pandas as pd

from ..base import Regime, load_series as _load, zscore

log = logging.getLogger(__name__)


class DispersionRegime(Regime):
    """3-state cross-sectional dispersion regime."""

    name = "Dispersion"
    dimensions = ["Dispersion"]
    states = ["MacroDriven", "StockPicking", "Crisis"]

    # ── Indicators ───────────────────────────────────────────────────────

    def _load_indicators(self, z_window: int) -> dict[str, pd.Series]:
        rows: dict[str, pd.Series] = {}

        # Sector ETFs (SPDR GICS sectors) — used to compute the cross-
        # sectional dispersion signal below.
        sector_codes = [
            "XLE US EQUITY:PX_LAST", "XLF US EQUITY:PX_LAST",
            "XLK US EQUITY:PX_LAST", "XLV US EQUITY:PX_LAST",
            "XLU US EQUITY:PX_LAST", "XLI US EQUITY:PX_LAST",
            "XLP US EQUITY:PX_LAST", "XLY US EQUITY:PX_LAST",
            "XLB US EQUITY:PX_LAST", "XLC US EQUITY:PX_LAST",
            "XLRE US EQUITY:PX_LAST",
        ]
        sector_data = {}
        for code in sector_codes:
            s = _load(code)
            if not s.empty:
                sector_data[code] = s.pct_change(3) * 100.0  # 3m return %

        # ds_SectorStdev — cross-sectional standard deviation of 3m sector
        # returns. High stdev = dispersed (stock-picker's market). Low
        # stdev = compressed (macro-driven). Stdev is preferred over the
        # range statistic because it's less sensitive to single-sector
        # outliers.
        if len(sector_data) >= 5:
            df = pd.DataFrame(sector_data)
            stdev = df.std(axis=1)
            rows["ds_SectorStdev"] = zscore(stdev, z_window).rename(
                "ds_SectorStdev"
            )

        # [DROPPED 2026-04-12: ds_SectorRange — triage found r=+0.97 with
        #  ds_SectorStdev (both are derivatives of the same sector-return
        #  cross-section). Dropped the range statistic because it's more
        #  sensitive to single-sector outliers; stdev is the more stable
        #  of the two.]

        # ds_VIXVol — 30-day stdev of daily VIX changes. When VIX itself
        # is volatile, the market is experiencing dispersion in risk
        # pricing. Orthogonal channel from the sector dispersion above
        # (r=+0.07 in the triage) — genuinely adds information.
        vix = _load("VIX INDEX:PX_LAST")
        if not vix.empty:
            vv = vix.pct_change().rolling(30).std()
            rows["ds_VIXVol"] = zscore(vv, z_window).rename("ds_VIXVol")

        if not rows:
            log.warning(
                "Dispersion: no indicators loaded. Expected at least 5 sector "
                "ETFs (XLE/XLF/XLK/XLV/XLU/XLI/XLP/XLY/XLB/XLC/XLRE) or VIX."
            )
        return rows

    # ── Composite overrides ──────────────────────────────────────────────

    def _dimension_prefixes(self) -> dict[str, str]:
        return {"Dispersion": "ds_"}

    # ── State probabilities ──────────────────────────────────────────────

    def _state_probabilities(
        self, dim_probs: dict[str, pd.Series]
    ) -> dict[str, pd.Series]:
        """Map Dispersion composite probability to 3 states.

        Low  dispersion → MacroDriven (index beta dominates)
        Mid  dispersion → StockPicking (rotation pays)
        High dispersion → Crisis only at extreme (>+1.5σ)

        We partition the sigmoid range into three bands. Because the
        default sensitivity maps z=+1.5 → P≈0.95 and z=-1.5 → P≈0.05,
        we use 0.85 and 0.15 as the band thresholds.
        """
        p = dim_probs["Dispersion"]
        p_macro = ((0.25 - p) / 0.25).clip(lower=0, upper=1)
        p_crisis = ((p - 0.85) / 0.15).clip(lower=0, upper=1)
        p_stock = (1.0 - p_macro - p_crisis).clip(lower=0)
        total = (p_macro + p_stock + p_crisis).clip(lower=1e-9)
        return {
            "P_MacroDriven":  p_macro / total,
            "P_StockPicking": p_stock / total,
            "P_Crisis":       p_crisis / total,
        }
