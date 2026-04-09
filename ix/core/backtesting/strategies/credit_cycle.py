import pandas as pd
from typing import Optional
from ix.db import MultiSeries, Series
from ix.core.backtesting.engine import Strategy, RiskManager


class SB_Auto_CreditCycle(Strategy):
    """Credit Cycle Regime Switching: HY spread level + direction + yield curve.

    Source: Verdad Capital "The Best Macro Indicator" (2020), Peter Barr
            "Asset Allocation Using the High Yield Spread" (2021),
            NY Fed yield curve research.
    Mode: auto (novel — no credit-based strategies in existing library)
    Built: 2026-03-29 by ix-strategy-builder

    Data mapping: 6 exact, 0 proxy

    | Research Concept | Implementation          | Match |
    |-----------------|-------------------------|-------|
    | HY OAS Spread   | BAMLH0A0HYM2            | Exact |
    | 3m10y Curve     | TRYUS10Y - TRYUS3M      | Exact |
    | US Equities     | SPY US EQUITY:PX_LAST   | Exact |
    | US Bonds        | IEF US EQUITY:PX_LAST   | Exact |
    | Gold            | GLD US EQUITY:PX_LAST   | Exact |
    | Cash / T-bills  | BIL US EQUITY:PX_LAST   | Exact |

    Rules:
    - Signal 1 (level): HY OAS above/below 60-month rolling median → wide/narrow
    - Signal 2 (direction): HY OAS higher/lower than 3 months ago → rising/falling
    - Signal 3 (override): 3m10y yield curve deeply inverted → force defensive
    - 4 credit cycle regimes:
      Recovery  (wide + falling)  → 80% SPY, 10% GLD, 10% BIL
      Growth    (narrow + falling)→ 100% SPY
      Overheat  (narrow + rising) → 60% SPY, 30% IEF, 10% BIL
      Recession (wide + rising)   → 10% SPY, 40% IEF, 30% GLD, 20% BIL
    - Yield curve override: if 3m10y < threshold AND regime = Overheat → Recession
    """


    label = "Credit Cycle"
    family = "credit"
    mode = "auto"
    description = "Classifies credit cycle using HY OAS spread vs 60-month median (wide/narrow) and 3-month direction (rising/falling). Four regimes: Recovery (wide+falling) → 80% SPY + 10% GLD + 10% BIL. Growth (narrow+falling) → 100% SPY. Overheat (narrow+rising) → 60% SPY + 30% IEF + 10% BIL. Recession (wide+rising) → 10% SPY + 40% IEF + 30% GLD + 20% BIL. Yield curve override forces defensive when 3m10y < -1%."
    author = "Verdad Capital"

    universe = {
        "SPY": {"code": "SPY US EQUITY:PX_LAST", "weight": 1.0},
        "IEF": {"code": "IEF US EQUITY:PX_LAST", "weight": 0.0},
        "GLD": {"code": "GLD US EQUITY:PX_LAST", "weight": 0.0},
        "BIL": {"code": "BIL US EQUITY:PX_LAST", "weight": 0.0},
    }

    bm_assets: dict[str, float] = {"SPY": 0.5, "IEF": 0.5}
    start = pd.Timestamp("2007-06-01")  # BIL inception ~2007-05
    frequency = "ME"
    commission = 15
    slippage = 5

    # Tunable parameters (max 3)
    MEDIAN_WINDOW = 60      # Months for HY spread rolling median (5 years)
    DIRECTION_DAYS = 63     # Trading days for HY spread direction (~3 months)
    CURVE_OVERRIDE = -1.0   # 3m10y threshold (%) for yield curve override

    # Regime allocations
    REGIMES = {
        "recovery":  {"SPY": 0.80, "IEF": 0.00, "GLD": 0.10, "BIL": 0.10},
        "growth":    {"SPY": 1.00, "IEF": 0.00, "GLD": 0.00, "BIL": 0.00},
        "overheat":  {"SPY": 0.60, "IEF": 0.30, "GLD": 0.00, "BIL": 0.10},
        "recession": {"SPY": 0.10, "IEF": 0.40, "GLD": 0.30, "BIL": 0.20},
    }

    def initialize(self) -> None:
        # HY OAS spread (daily, bps)
        self._hy = Series("BAMLH0A0HYM2")

        # Yield curve: 3m10y (daily, %)
        t10 = Series("TRYUS10Y:PX_YTM")
        t3m = Series("TRYUS3M:PX_YTM")
        if not t10.empty and not t3m.empty:
            aligned = pd.concat([t10, t3m], axis=1).dropna()
            self._curve = aligned.iloc[:, 0] - aligned.iloc[:, 1]
        else:
            self._curve = pd.Series(dtype=float)

        # Rolling median of HY spread (convert MEDIAN_WINDOW months to ~trading days)
        median_days = self.MEDIAN_WINDOW * 21
        self._hy_median = self._hy.rolling(
            window=median_days, min_periods=median_days // 2
        ).median()

    def _classify_regime(self) -> str:
        """Classify current credit cycle regime from HY spread and yield curve."""
        hy_now = self._hy.loc[:self.d].iloc[-1] if len(self._hy.loc[:self.d]) > 0 else float("nan")
        median_now = self._hy_median.loc[:self.d].iloc[-1] if len(self._hy_median.loc[:self.d]) > 0 else float("nan")

        # Direction: compare current HY to DIRECTION_DAYS ago
        hy_hist = self._hy.loc[:self.d]
        if len(hy_hist) > self.DIRECTION_DAYS:
            hy_past = hy_hist.iloc[-(self.DIRECTION_DAYS + 1)]
        else:
            hy_past = float("nan")

        if pd.isna(hy_now) or pd.isna(median_now) or pd.isna(hy_past):
            return "growth"  # Default to neutral-bullish when data insufficient

        wide = hy_now > median_now
        rising = hy_now > hy_past

        if wide and not rising:
            regime = "recovery"
        elif not wide and not rising:
            regime = "growth"
        elif not wide and rising:
            regime = "overheat"
        else:  # wide and rising
            regime = "recession"

        # Yield curve override: deep inversion forces defensive posture
        if regime == "overheat" and not self._curve.empty:
            curve_now = self._curve.loc[:self.d]
            if len(curve_now) > 0 and curve_now.iloc[-1] < self.CURVE_OVERRIDE:
                regime = "recession"

        return regime

    def generate_signals(self) -> pd.Series:
        regime = self._classify_regime()
        return pd.Series(self.REGIMES[regime])

    def allocate(self) -> pd.Series:
        return self.generate_signals()

    def get_params(self) -> dict:
        return {
            "source": "Verdad Capital + Peter Barr + NY Fed yield curve",
            "mode": "auto",
            "median_window_months": self.MEDIAN_WINDOW,
            "direction_days": self.DIRECTION_DAYS,
            "curve_override_pct": self.CURVE_OVERRIDE,
        }


# ------------------------------------------------------------------
# SB_Auto_VolRegime — Auto-discovered (ix-strategy-builder)
# ------------------------------------------------------------------
