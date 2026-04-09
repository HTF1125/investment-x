"""Risk-control strategies — drawdown management, bond rotation, relative value."""

import pandas as pd
import numpy as np
from ._base import FamilyStrategy
from ix.core.backtesting.batch.constants import ASSET_CODES


class DrawdownControl(FamilyStrategy):
    """Graduated equity exposure based on drawdown severity."""
    family = "Risk Control"

    def __init__(
        self,
        dd_thresh: float = -0.10,
        lookback: int = 12,
        equity: str = "SPY",
        bond: str = "IEF",
        **kw,
    ):
        self._dd_thresh = dd_thresh
        self._lookback = lookback
        self._equity = equity
        self._bond = bond
        self._build_universe([equity, bond])
        self.label = f"DrawdownControl {equity}/{bond} dd={dd_thresh:.0%} lb={lookback}"
        self.description = (
            f"Drawdown-based risk control: monitors {equity} drawdown from its "
            f"{lookback}-month peak. No drawdown → 100% {equity}. Drawdown exceeds "
            f"{dd_thresh:.0%} → reduces to 30% {equity} + 70% {bond}. Drawdown exceeds "
            f"{dd_thresh*2:.0%} → full defensive 0% {equity} + 100% {bond}. Graduated "
            f"response prevents overreaction to shallow pullbacks while protecting "
            f"against deep bears. Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self):
        m = self._monthly
        px = m[self._equity]
        peak = px.rolling(self._lookback, min_periods=1).max()
        dd = (px / peak) - 1

        dd_now = dd.iloc[-1]
        if dd_now < self._dd_thresh * 2:
            w_eq = 0.0
        elif dd_now < self._dd_thresh:
            w_eq = 0.3
        else:
            w_eq = 1.0

        w = pd.Series(0.0, index=self.asset_names)
        w[self._equity] = w_eq
        w[self._bond] = 1.0 - w_eq
        return w

    def get_params(self):
        return {
            "dd_thresh": self._dd_thresh,
            "lookback": self._lookback,
            "equity": self._equity,
            "bond": self._bond,
        }


class BondRotation(FamilyStrategy):
    """Momentum-based bond rotation: rank by return, equal-weight top N."""
    family = "Risk Control"

    def __init__(
        self,
        lookback: int = 3,
        bonds: list[str] = None,
        top_n: int = 1,
        **kw,
    ):
        if bonds is None:
            bonds = ["AGG", "TLT", "IEF", "TIP", "HYG", "LQD"]
        self._lookback = lookback
        self._bonds = bonds
        self._top_n = top_n
        bond_list = ", ".join(bonds)
        self._build_universe(bonds)
        self.label = f"BondRotation top{top_n}/{len(bonds)} lb={lookback}"
        self.description = (
            f"Bond momentum rotation: ranks {len(bonds)} bond ETFs ({bond_list}) "
            f"by their {lookback}-month total return. Holds the top {top_n} in equal "
            f"weight. Captures the tendency of bond momentum to persist across rate "
            f"cycles — strong duration or credit performers tend to continue. "
            f"Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self):
        m = self._monthly
        avail = self._avail(self._bonds)
        if not avail:
            return pd.Series(0.0, index=self.asset_names)

        returns = {b: m[b].pct_change(self._lookback).iloc[-1] for b in avail}
        ranked = sorted(returns, key=returns.get, reverse=True)
        selected = ranked[: self._top_n]
        return self._eq_weight(selected)

    def get_params(self):
        return {
            "lookback": self._lookback,
            "bonds": self._bonds,
            "top_n": self._top_n,
        }


class RelativeValue(FamilyStrategy):
    """Relative momentum: 100% to whichever asset has higher lookback return."""
    family = "Risk Control"

    def __init__(
        self,
        lookback: int = 6,
        asset_a: str = "SPY",
        asset_b: str = "TLT",
        **kw,
    ):
        self._lookback = lookback
        self._asset_a = asset_a
        self._asset_b = asset_b
        self._build_universe([asset_a, asset_b])
        self.label = f"RelativeValue {asset_a}/{asset_b} lb={lookback}"
        self.description = (
            f"Relative momentum switching: allocates 100% to whichever of "
            f"{asset_a} or {asset_b} has the higher {lookback}-month return. "
            f"Binary switch between two assets — captures persistent relative "
            f"strength between asset classes (e.g., US vs International, Growth "
            f"vs Value). Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self):
        m = self._monthly
        ret_a = m[self._asset_a].pct_change(self._lookback).iloc[-1]
        ret_b = m[self._asset_b].pct_change(self._lookback).iloc[-1]

        w = pd.Series(0.0, index=self.asset_names)
        if ret_a >= ret_b:
            w[self._asset_a] = 1.0
        else:
            w[self._asset_b] = 1.0
        return w

    def get_params(self):
        return {
            "lookback": self._lookback,
            "asset_a": self._asset_a,
            "asset_b": self._asset_b,
        }
