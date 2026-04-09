"""Macro Regime Strategy — Composite Growth × Inflation 4-Season Framework.

Signals are derived from multi-indicator composites empirically validated by
the platform's walk-forward pipeline (frequency of selection across 189 periods):

  Growth composite    — Initial Claims (100%) + ISM New Orders (84%) + OECD CLI (84%)
  Inflation composite — ISM Prices Paid (100%) + CPI 3M Ann. (99%) + 10Y Breakeven (42%)

Each indicator is z-scored over a 36-month rolling window.  The composite is
the equal-weight average of available z-scores for that dimension.  A composite
z > 0 → rising; z < 0 → falling.
"""

import pandas as pd
import numpy as np
from ix.db.query import Series
from ix.core.backtesting.engine import Strategy


def _rolling_zscore(s: pd.Series, window: int = 36, min_periods: int = 12) -> pd.Series:
    """Standardise a series using rolling mean and std (z-score)."""
    mu  = s.rolling(window, min_periods=min_periods).mean()
    sig = s.rolling(window, min_periods=min_periods).std()
    return (s - mu) / (sig + 1e-9)


def _load_monthly(code: str, lag: int = 0) -> pd.Series:
    """Load a Series, resample to month-end, optionally shift for publication lag."""
    raw = Series(code)
    if raw.empty:
        return pd.Series(dtype=float)
    s = raw.resample("ME").last()
    return s.shift(lag) if lag else s


class SB_Macro_GrowthInflation(Strategy):
    """Composite Growth × Inflation 4-Season Macro Regime.

    Source: Ray Dalio "All Weather" / Dalio 4-season framework.
    Signals: multi-indicator composites validated by walk-forward IC selection.
    Mode: synthesize
    Built: 2026-04-01  —  upgraded 2026-04-01 (composite indicators)

    Growth composite (3 indicators, equal-weight z-score average):
    | Indicator        | Code              | Lag | Rationale                  |
    |-----------------|-------------------|-----|----------------------------|
    | Initial Claims  | ICSA              | 0   | Lagging inverted (↑=bad)   |
    | ISM New Orders  | ISMNOR_M:PX_LAST  | 1m  | Leading manufacturing      |
    | OECD CLI (US)   | USA.LOLITOAA.STSA | 1m  | Broad leading indicator    |

    Inflation composite (3 indicators, equal-weight z-score average):
    | Indicator        | Code                   | Lag | Rationale               |
    |-----------------|------------------------|-----|-------------------------|
    | ISM Prices Paid | ISMPRI_M:PX_LAST       | 1m  | Producer price pressure |
    | CPI 3M Ann.     | USPR1980783:PX_LAST    | 1m  | Realised CPI momentum   |
    | 10Y Breakeven   | T5YIE:PX_LAST          | 0   | Market inflation expect.|

    Z-score window: 36 months (rolling mean + std).
    Regime = sign(growth_z) × sign(inflation_z) → 4-quadrant classification.

    Allocations (Dalio-inspired, ETF universe):
    - Goldilocks  (g↑, i↓): 90% SPY + 10% GLD
    - Reflation   (g↑, i↑): 60% SPY + 20% TIP + 10% IEF + 10% GLD
    - Deflation   (g↓, i↓): 20% SPY + 50% IEF + 20% GLD + 10% BIL
    - Stagflation (g↓, i↑): 10% SPY + 20% IEF + 50% GLD + 20% TIP
    """

    label       = "Growth-Inflation Regime"
    family      = "macro"
    mode        = "synthesize"
    description = (
        "Multi-indicator composite regime strategy. "
        "Growth composite: Initial Claims (inverted) + ISM New Orders + OECD CLI, "
        "each z-scored over 36 months and averaged. "
        "Inflation composite: ISM Prices Paid + CPI 3M Annualized + 10Y Breakeven, "
        "same z-score treatment. "
        "Goldilocks (g↑, i↓) → 90% SPY + 10% GLD. "
        "Reflation (g↑, i↑) → 60% SPY + 20% TIP + 10% IEF + 10% GLD. "
        "Deflation (g↓, i↓) → 20% SPY + 50% IEF + 20% GLD + 10% BIL. "
        "Stagflation (g↓, i↑) → 10% SPY + 20% IEF + 50% GLD + 20% TIP. "
        "Indicators selected based on highest walk-forward selection frequency. "
        "Monthly rebalance, 1-month publication lag applied to survey data."
    )
    author = "Ray Dalio / All Weather"

    universe = {
        "SPY": {"code": "SPY US EQUITY:PX_LAST", "weight": 1.0},
        "IEF": {"code": "IEF US EQUITY:PX_LAST", "weight": 0.0},
        "GLD": {"code": "GLD US EQUITY:PX_LAST", "weight": 0.0},
        "TIP": {"code": "TIP US EQUITY:PX_LAST", "weight": 0.0},
        "BIL": {"code": "BIL US EQUITY:PX_LAST", "weight": 0.0},
    }

    bm_assets: dict[str, float] = {"SPY": 0.5, "IEF": 0.5}
    start      = pd.Timestamp("2004-01-01")
    frequency  = "ME"
    commission = 15
    slippage   = 5

    # Composite parameters
    Z_WINDOW    = 36   # rolling z-score window (months)
    Z_MIN       = 12   # min periods for z-score
    NEUTRAL_BND = 0.0  # z > 0 = rising, z < 0 = falling (no neutral zone)

    REGIMES = {
        "goldilocks":  {"SPY": 0.90, "IEF": 0.00, "GLD": 0.10, "TIP": 0.00, "BIL": 0.00},
        "reflation":   {"SPY": 0.60, "IEF": 0.10, "GLD": 0.10, "TIP": 0.20, "BIL": 0.00},
        "deflation":   {"SPY": 0.20, "IEF": 0.50, "GLD": 0.20, "TIP": 0.00, "BIL": 0.10},
        "stagflation": {"SPY": 0.10, "IEF": 0.20, "GLD": 0.50, "TIP": 0.20, "BIL": 0.00},
    }

    # ── Initialisation ────────────────────────────────────────────────

    def initialize(self) -> None:
        self._growth_z    = self._build_growth_composite()
        self._inflation_z = self._build_inflation_composite()

    def _build_growth_composite(self) -> pd.Series:
        """Equal-weight z-score composite of 3 growth indicators."""
        components = []

        # 1. Initial Claims (FRED: ICSA) — inverted: rising claims = weaker growth
        ic = _load_monthly("ICSA")
        if not ic.empty:
            components.append(-_rolling_zscore(ic, self.Z_WINDOW, self.Z_MIN))

        # 2. ISM New Orders — 1-month publication lag
        ism_no = _load_monthly("ISMNOR_M:PX_LAST", lag=1)
        if not ism_no.empty:
            components.append(_rolling_zscore(ism_no, self.Z_WINDOW, self.Z_MIN))

        # 3. OECD CLI (US) — 1-month publication lag
        oecd = _load_monthly("USA.LOLITOAA.STSA", lag=1)
        if not oecd.empty:
            components.append(_rolling_zscore(oecd, self.Z_WINDOW, self.Z_MIN))

        if not components:
            return pd.Series(dtype=float)

        return pd.concat(components, axis=1).mean(axis=1)

    def _build_inflation_composite(self) -> pd.Series:
        """Equal-weight z-score composite of 3 inflation indicators."""
        components = []

        # 1. ISM Prices Paid — 1-month publication lag
        ism_pr = _load_monthly("ISMPRI_M:PX_LAST", lag=1)
        if not ism_pr.empty:
            components.append(_rolling_zscore(ism_pr, self.Z_WINDOW, self.Z_MIN))

        # 2. CPI 3-month annualised (= pct_change(3) × 4 × 100) — 1-month lag
        cpi_raw = _load_monthly("USPR1980783:PX_LAST", lag=1)
        if not cpi_raw.empty:
            cpi_3m = cpi_raw.pct_change(3).mul(400)          # annualised %
            components.append(_rolling_zscore(cpi_3m, self.Z_WINDOW, self.Z_MIN))

        # 3. 10Y Breakeven (market-implied, no lag needed)
        be = _load_monthly("T5YIE:PX_LAST")
        if not be.empty:
            components.append(_rolling_zscore(be, self.Z_WINDOW, self.Z_MIN))

        if not components:
            return pd.Series(dtype=float)

        return pd.concat(components, axis=1).mean(axis=1)

    # ── Regime classification ─────────────────────────────────────────

    def _composite_at(self, composite: pd.Series) -> float:
        """Get most recent composite z-score up to self.d."""
        if composite.empty:
            return float("nan")
        vals = composite.loc[:self.d]
        return vals.iloc[-1] if len(vals) > 0 else float("nan")

    def _classify_regime(self) -> str:
        gz = self._composite_at(self._growth_z)
        iz = self._composite_at(self._inflation_z)

        if pd.isna(gz) or pd.isna(iz):
            return "goldilocks"   # neutral-bullish fallback

        growth_up    = gz > self.NEUTRAL_BND
        inflation_up = iz > self.NEUTRAL_BND

        if growth_up and not inflation_up:
            return "goldilocks"
        elif growth_up and inflation_up:
            return "reflation"
        elif not growth_up and not inflation_up:
            return "deflation"
        else:
            return "stagflation"

    # ── Strategy interface ────────────────────────────────────────────

    def generate_signals(self) -> pd.Series:
        return pd.Series(self.REGIMES[self._classify_regime()])

    def allocate(self) -> pd.Series:
        return self.generate_signals()

    def get_params(self) -> dict:
        return {
            "source":         "Dalio All Weather + WF-validated composite indicators",
            "mode":           "synthesize",
            "z_window_months": self.Z_WINDOW,
            "growth_inputs":   ["Initial Claims (inv)", "ISM New Orders", "OECD CLI US"],
            "inflation_inputs": ["ISM Prices Paid", "CPI 3M Ann.", "10Y Breakeven"],
        }
