"""Dual momentum and defensive rotation strategy families."""

import pandas as pd
import numpy as np
from ._base import FamilyStrategy
from ix.core.backtesting.batch.constants import ASSET_CODES, SECTORS, MULTI5, MULTI8, BROAD6


class DualMomentum(FamilyStrategy):
    """Dual momentum: pick best risky asset by lookback return, check vs cash hurdle.

    If best risky > cash → hold best. If safe > cash → hold safe. Else cash.
    """
    family = "Momentum"

    def __init__(
        self,
        lookback: int,
        risky: list[str],
        safe: str = "IEF",
        cash: str = "BIL",
        **kw,
    ):
        self.lookback = lookback
        self._risky = risky
        self._safe = safe
        self._cash = cash
        all_assets = list(set(risky + [safe, cash]))
        self._build_universe(all_assets)
        risky_list = ", ".join(risky)
        self.label = f"DualMom({lookback}m, {len(risky)} risky)"
        self.description = (
            f"Antonacci dual momentum: picks the best-performing risky asset "
            f"({risky_list}) by {lookback}-month return (relative momentum). "
            f"Then checks if the winner beats {cash} (absolute momentum). "
            f"If yes → 100% winner. If no but {safe} beats {cash} → 100% {safe}. "
            f"Otherwise → 100% {cash}. Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self) -> pd.Series:
        hist = self._monthly.loc[:self.d]
        risky = self._avail(self._risky)
        lb = self.lookback
        if not risky or len(hist) <= lb:
            return pd.Series({self._safe: 1.0}).reindex(self.asset_names, fill_value=0.0)

        # Compute returns for risky + safe
        rets = {}
        for a in risky + [self._safe]:
            if a in hist.columns and len(hist[a].dropna()) > lb:
                rets[a] = hist[a].iloc[-1] / hist[a].iloc[-lb - 1] - 1

        # Cash hurdle
        cash_ret = 0.0
        if self._cash in hist.columns and len(hist[self._cash].dropna()) > lb:
            cash_ret = hist[self._cash].iloc[-1] / hist[self._cash].iloc[-lb - 1] - 1

        risky_rets = {a: rets[a] for a in risky if a in rets}
        if not risky_rets:
            return pd.Series({self._safe: 1.0}).reindex(self.asset_names, fill_value=0.0)

        best = max(risky_rets, key=risky_rets.get)
        if risky_rets[best] > cash_ret:
            w = {best: 1.0}
        elif self._safe in rets and rets[self._safe] > cash_ret:
            w = {self._safe: 1.0}
        else:
            w = {self._cash: 1.0} if self._cash in hist.columns else {self._safe: 1.0}

        return pd.Series(w).reindex(self.asset_names, fill_value=0.0)

    def get_params(self) -> dict:
        return {
            "lookback": self.lookback,
            "risky": self._risky,
            "safe": self._safe,
            "cash": self._cash,
        }


class DefensiveRotation(FamilyStrategy):
    """Defensive rotation using 13612W composite momentum score.

    Score = 12*r1 + 4*r3 + 2*r6 + r12. Top N assets passing cash hurdle.
    """
    family = "Momentum"

    def __init__(
        self,
        assets: list[str],
        cash: str = "BIL",
        top_n: int = 2,
        fallback: str = "SPY",
        **kw,
    ):
        self._rotation_assets = assets
        self._cash = cash
        self.top_n = top_n
        self._fallback = fallback
        all_assets = list(set(assets + [cash, fallback]))
        self._build_universe(all_assets)
        n = len(assets)
        asset_list = ", ".join(assets)
        self.label = f"DefRot(top{top_n}, {n} assets)"
        self.description = (
            f"Defensive asset rotation using 13612W composite momentum "
            f"(12×r1 + 4×r3 + 2×r6 + r12). Ranks {n} defensive assets "
            f"({asset_list}), filters by {cash} hurdle, and holds top {top_n} "
            f"in equal weight. Falls back to {fallback} if no asset passes "
            f"the hurdle. Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self) -> pd.Series:
        hist = self._monthly.loc[:self.d]
        assets = self._avail(self._rotation_assets)
        if len(hist) < 13 or not assets:
            return pd.Series({self._fallback: 1.0}).reindex(self.asset_names, fill_value=0.0)

        # Compute 13612W score for each asset
        scores = {}
        for a in assets:
            pr = hist[a].dropna()
            if len(pr) < 13:
                continue
            r1 = pr.iloc[-1] / pr.iloc[-2] - 1
            r3 = pr.iloc[-1] / pr.iloc[-4] - 1 if len(pr) > 3 else r1
            r6 = pr.iloc[-1] / pr.iloc[-7] - 1 if len(pr) > 6 else r3
            r12 = pr.iloc[-1] / pr.iloc[-13] - 1 if len(pr) > 12 else r6
            scores[a] = 12 * r1 + 4 * r3 + 2 * r6 + r12

        # Cash hurdle
        cash_score = 0.0
        if self._cash in hist.columns and len(hist[self._cash].dropna()) > 12:
            c = hist[self._cash].dropna()
            c_r1 = c.iloc[-1] / c.iloc[-2] - 1
            c_r3 = c.iloc[-1] / c.iloc[-4] - 1 if len(c) > 3 else c_r1
            c_r6 = c.iloc[-1] / c.iloc[-7] - 1 if len(c) > 6 else c_r3
            c_r12 = c.iloc[-1] / c.iloc[-13] - 1 if len(c) > 12 else c_r6
            cash_score = 12 * c_r1 + 4 * c_r3 + 2 * c_r6 + c_r12

        passing = {a: s for a, s in scores.items() if s > cash_score}
        if not passing:
            return pd.Series({self._fallback: 1.0}).reindex(self.asset_names, fill_value=0.0)

        ranked = sorted(passing.items(), key=lambda x: x[1], reverse=True)[:self.top_n]
        w_val = 1.0 / len(ranked)
        w = {a: w_val for a, _ in ranked}
        return pd.Series(w).reindex(self.asset_names, fill_value=0.0)

    def get_params(self) -> dict:
        return {
            "assets": self._rotation_assets,
            "cash": self._cash,
            "top_n": self.top_n,
            "fallback": self._fallback,
        }
