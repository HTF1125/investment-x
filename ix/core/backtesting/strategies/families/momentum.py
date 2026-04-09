"""Momentum strategy families — absolute, composite-weighted, and sector rotation."""

import pandas as pd
import numpy as np
from ._base import FamilyStrategy
from ix.core.backtesting.batch.constants import ASSET_CODES, SECTORS


class MomentumStrategy(FamilyStrategy):
    """Absolute momentum — rank by lookback return, pick top N."""
    family = "Momentum"

    def __init__(
        self,
        lookback: int = 12,
        top_n: int = 1,
        assets: list[str] | None = None,
        cash: str | None = None,
        absolute: bool = True,
        name: str = "",
        **kw,
    ):
        self._lookback = lookback
        self._top_n = top_n
        self._assets = assets or ["SPY", "EFA", "EEM", "TLT", "GLD"]
        self._cash = cash
        self._absolute = absolute

        all_assets = list(self._assets)
        if cash and cash not in all_assets:
            all_assets.append(cash)
        self._build_universe(all_assets)

        n = len(self._assets)
        asset_list = ", ".join(self._assets)
        self.label = name or f"Momentum {lookback}m Top{top_n}"
        self.description = (
            f"Absolute momentum: computes {lookback}-month total return for each of "
            f"{n} assets ({asset_list}). Selects the top {top_n} performers with "
            f"positive returns{' that beat ' + cash + ' cash hurdle' if cash else ''}. "
            f"Equal-weights winners. If no asset qualifies, holds "
            f"{'100% ' + cash + ' cash' if cash else 'equal-weight fallback'}. "
            f"Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self) -> pd.Series:
        px = self._monthly
        lb = self._lookback
        assets = self._avail(self._assets)
        cash = self._cash

        if len(px) <= lb or not assets:
            return self._eq_weight(assets or ["SPY"])

        ret = px[assets].iloc[-1] / px[assets].iloc[-lb - 1] - 1
        ret = ret.dropna()

        if cash and cash in px.columns and len(px[cash].dropna()) > lb:
            cash_ret = px[cash].iloc[-1] / px[cash].iloc[-lb - 1] - 1
            candidates = ret[ret > cash_ret]
            if candidates.empty:
                w = pd.Series(0.0, index=self.asset_names)
                if cash in w.index:
                    w[cash] = 1.0
                return w
        else:
            candidates = ret[ret > 0] if self._absolute else ret

        if candidates.empty:
            if cash:
                w = pd.Series(0.0, index=self.asset_names)
                if cash in w.index:
                    w[cash] = 1.0
                return w
            return self._eq_weight(assets)

        top = candidates.nlargest(min(self._top_n, len(candidates)))
        w = pd.Series(1.0 / len(top), index=top.index)
        return w.reindex(self.asset_names, fill_value=0.0)

    def get_params(self):
        return {
            "lookback": self._lookback,
            "top_n": self._top_n,
            "assets": self._assets,
            "cash": self._cash,
            "absolute": self._absolute,
        }


class Momentum13612W(FamilyStrategy):
    """Composite momentum — 12*r1 + 4*r3 + 2*r6 + r12 weighted scoring."""
    family = "Momentum"

    def __init__(
        self,
        assets: list[str] | None = None,
        top_n: int = 1,
        cash: str | None = None,
        name: str = "",
        **kw,
    ):
        self._assets = assets or ["SPY", "EFA", "EEM", "TLT", "GLD"]
        self._top_n = top_n
        self._cash = cash

        all_assets = list(self._assets)
        if cash and cash not in all_assets:
            all_assets.append(cash)
        self._build_universe(all_assets)

        n = len(self._assets)
        asset_list = ", ".join(self._assets)
        self.label = name or f"13612W Momentum Top{top_n}"
        self.description = (
            f"Composite weighted momentum using 13612W scoring "
            f"(12×r1 + 4×r3 + 2×r6 + r12) across {n} assets ({asset_list}). "
            f"Ranks by composite score and selects top {top_n}. "
            f"{'Filters by ' + cash + ' cash hurdle' if cash else 'Filters by positive score'}. "
            f"Equal-weights winners. Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self) -> pd.Series:
        px = self._monthly
        assets = self._avail(self._assets)
        top_n = self._top_n
        cash = self._cash

        if len(px) < 13 or not assets:
            return self._eq_weight(assets or ["SPY"])

        pr = px[assets]
        r1 = pr.iloc[-1] / pr.iloc[-2] - 1
        r3 = pr.iloc[-1] / pr.iloc[-4] - 1 if len(pr) > 3 else r1
        r6 = pr.iloc[-1] / pr.iloc[-7] - 1 if len(pr) > 6 else r3
        r12 = pr.iloc[-1] / pr.iloc[-13] - 1 if len(pr) > 12 else r6
        score = 12 * r1 + 4 * r3 + 2 * r6 + r12

        if cash and cash in px.columns and len(px[cash].dropna()) > 12:
            c = px[cash]
            c_r1 = c.iloc[-1] / c.iloc[-2] - 1
            c_r3 = c.iloc[-1] / c.iloc[-4] - 1 if len(c) > 3 else c_r1
            c_r6 = c.iloc[-1] / c.iloc[-7] - 1 if len(c) > 6 else c_r3
            c_r12 = c.iloc[-1] / c.iloc[-13] - 1 if len(c) > 12 else c_r6
            cash_score = 12 * c_r1 + 4 * c_r3 + 2 * c_r6 + c_r12
            candidates = score[score > cash_score].dropna()
            if candidates.empty:
                w = pd.Series(0.0, index=self.asset_names)
                if cash in w.index:
                    w[cash] = 1.0
                return w
        else:
            candidates = score.dropna()
            candidates = candidates[candidates > 0]

        if candidates.empty:
            if cash:
                w = pd.Series(0.0, index=self.asset_names)
                if cash in w.index:
                    w[cash] = 1.0
                return w
            return self._eq_weight(assets)

        top = candidates.nlargest(min(top_n, len(candidates)))
        w = pd.Series(1.0 / len(top), index=top.index)
        return w.reindex(self.asset_names, fill_value=0.0)

    def get_params(self):
        return {
            "assets": self._assets,
            "top_n": self._top_n,
            "cash": self._cash,
        }


class SectorMomentum(FamilyStrategy):
    """Sector rotation — rank sectors by lookback return, pick top N."""
    family = "Momentum"

    def __init__(
        self,
        lookback: int = 3,
        top_n: int = 3,
        sectors: list[str] | None = None,
        fallback: str = "SPY",
        name: str = "",
        **kw,
    ):
        self._lookback = lookback
        self._top_n = top_n
        self._sectors = sectors or SECTORS
        self._fallback = fallback

        all_assets = list(self._sectors)
        if fallback not in all_assets:
            all_assets.append(fallback)
        self._build_universe(all_assets, benchmark={"SPY": 1.0})

        n = len(self._sectors)
        sector_list = ", ".join(self._sectors)
        self.label = name or f"Sector Momentum {lookback}m Top{top_n}"
        self.description = (
            f"Sector rotation: computes {lookback}-month total return for {n} sector "
            f"ETFs ({sector_list}). Selects top {top_n} sectors with positive returns "
            f"and equal-weights them. Falls back to 100% {fallback} when no sector has "
            f"positive momentum. Benchmark: 100% SPY (sector pickers should beat broad "
            f"market). Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self) -> pd.Series:
        px = self._monthly
        lb = self._lookback
        top_n = self._top_n
        sectors = self._avail(self._sectors)
        fallback = self._fallback

        if len(px) <= lb or len(sectors) < top_n:
            w = pd.Series(0.0, index=self.asset_names)
            if fallback in w.index:
                w[fallback] = 1.0
            return w

        ret = px[sectors].iloc[-1] / px[sectors].iloc[-lb - 1] - 1
        ret = ret.dropna()

        if len(ret) < top_n:
            w = pd.Series(0.0, index=self.asset_names)
            if fallback in w.index:
                w[fallback] = 1.0
            return w

        top = ret.nlargest(top_n)
        top = top[top > 0]

        if top.empty:
            w = pd.Series(0.0, index=self.asset_names)
            if fallback in w.index:
                w[fallback] = 1.0
            return w

        w = pd.Series(1.0 / len(top), index=top.index)
        return w.reindex(self.asset_names, fill_value=0.0)

    def get_params(self):
        return {
            "lookback": self._lookback,
            "top_n": self._top_n,
            "sectors": self._sectors,
            "fallback": self._fallback,
        }
