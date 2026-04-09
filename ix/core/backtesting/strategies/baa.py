import pandas as pd
from typing import Optional
from ix.db import MultiSeries, Series
from ix.core.backtesting.engine import Strategy, RiskManager


class SB_Keller_BAABalanced(Strategy):
    """Bold Asset Allocation (Balanced): canary-driven dual momentum.

    Source: Wouter J. Keller & Jan Willem Keuning, "Breadth Momentum and
            the Canary Universe: Defensive Asset Allocation", SSRN #3212862.
    Mode: replicate
    Built: 2026-03-28 by ix-strategy-builder
    Data mapping: 16 exact, 0 proxy, 0 excluded

    Rules:
    - Canary universe (SPY, EFA, EEM, AGG): if ALL have positive 13612W
      momentum → offensive mode. If ANY negative → defensive mode.
    - Offensive: top 6 of 12 assets by relative momentum, equal weight.
    - Defensive: top 3 of 7 assets by relative momentum, but only if
      their momentum > BIL. Otherwise that share goes to BIL (cash).
    - 13612W momentum = 12*(p0/p1-1) + 4*(p0/p3-1) + 2*(p0/p6-1) + (p0/p12-1)
    - Relative momentum = price / avg(last 13 month-end prices)
    """


    label = "Bold Asset Allocation"
    family = "momentum"
    mode = "replicate"
    description = "Keller BAA: uses SPY + EFA as canary pair. If any canary has negative 13612W momentum → switch to defensive universe (TLT, IEF, GLD, BIL, ranked by 13612W, top 2). If canaries positive → offensive universe (SPY, QQQ, IWM, EFA, EEM, ranked by 13612W, top 3). Monthly rotation."
    author = "Wouter Keller"

    # All assets in one universe; allocation logic handles selection
    OFFENSIVE = ["SPY", "QQQ", "IWM", "VGK", "EWJ", "EEM",
                 "VNQ", "DBC", "GLD", "TLT", "HYG", "LQD"]
    DEFENSIVE = ["TIP", "DBC", "BIL", "IEF", "TLT", "LQD", "AGG"]
    CANARY = ["SPY", "EFA", "EEM", "AGG"]

    # Union of all assets
    _ALL = sorted(set(OFFENSIVE + DEFENSIVE + CANARY))

    universe = {t: {"code": f"{t} US EQUITY:PX_LAST", "weight": 0.0}
                for t in _ALL}
    universe["SPY"]["weight"] = 1.0  # benchmark reference

    bm_assets: dict[str, float] = {"SPY": 0.5}
    start = pd.Timestamp("2008-01-01")
    frequency = "ME"
    commission = 15
    slippage = 5

    TOP_N_OFFENSE = 6
    TOP_N_DEFENSE = 3

    def initialize(self) -> None:
        prices = self.pxs.rename(columns=self.code_to_name).ffill()
        self._prices = prices

        # Pre-compute 13612W momentum for canary universe
        # 12*(p0/p1-1) + 4*(p0/p3-1) + 2*(p0/p6-1) + (p0/p12-1)
        r1 = prices.pct_change(21)   # ~1 month
        r3 = prices.pct_change(63)   # ~3 months
        r6 = prices.pct_change(126)  # ~6 months
        r12 = prices.pct_change(252) # ~12 months
        self._mom_13612w = 12 * r1 + 4 * r3 + 2 * r6 + r12

        # Pre-compute relative momentum: price / SMA(13 months)
        self._rel_mom = prices / prices.rolling(window=273, min_periods=200).mean()

    def generate_signals(self) -> pd.Series:
        if self.d not in self._mom_13612w.index:
            return pd.Series(0.0, index=self.assets)

        mom = self._mom_13612w.loc[self.d]
        rel = self._rel_mom.loc[self.d]

        # Check canary: all 4 must have positive 13612W momentum
        canary_ok = all(
            mom.get(c, float("nan")) > 0 if pd.notna(mom.get(c, float("nan"))) else False
            for c in self.CANARY
        )

        weights = {a: 0.0 for a in self.assets}

        if canary_ok:
            # OFFENSIVE: top 6 by relative momentum, equal weight
            off_scores = {a: float(rel.get(a, 0.0)) for a in self.OFFENSIVE
                          if pd.notna(rel.get(a, float("nan")))}
            ranked = sorted(off_scores.items(), key=lambda x: x[1], reverse=True)
            top = ranked[:self.TOP_N_OFFENSE]
            w = 1.0 / self.TOP_N_OFFENSE
            for asset, _ in top:
                weights[asset] = w
        else:
            # DEFENSIVE: top 3 by relative momentum, but only if > BIL
            bil_rel = float(rel.get("BIL", 1.0)) if pd.notna(rel.get("BIL", float("nan"))) else 1.0
            def_scores = {a: float(rel.get(a, 0.0)) for a in self.DEFENSIVE
                          if pd.notna(rel.get(a, float("nan"))) and a != "BIL"}
            ranked = sorted(def_scores.items(), key=lambda x: x[1], reverse=True)

            w = 1.0 / self.TOP_N_DEFENSE
            cash_extra = 0.0
            selected = 0
            for asset, score in ranked:
                if selected >= self.TOP_N_DEFENSE:
                    break
                if score > bil_rel:
                    weights[asset] = w
                else:
                    cash_extra += w
                selected += 1
            # Remaining slots + failed assets → BIL
            remaining = self.TOP_N_DEFENSE - selected
            cash_extra += remaining * w
            weights["BIL"] = weights.get("BIL", 0.0) + cash_extra

        return pd.Series(weights).reindex(self.assets, fill_value=0.0)

    def allocate(self) -> pd.Series:
        return self.generate_signals()

    def get_params(self) -> dict:
        return {
            "source": "Keller & Keuning, SSRN #3212862",
            "mode": "replicate",
            "top_n_offense": self.TOP_N_OFFENSE,
            "top_n_defense": self.TOP_N_DEFENSE,
        }


# ------------------------------------------------------------------
# SB_Antonacci_CDM — Research-driven (ix-strategy-builder)
# ------------------------------------------------------------------
