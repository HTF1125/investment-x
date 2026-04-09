"""Ensemble strategies — combine momentum, trend, and macro signals."""

import pandas as pd
import numpy as np
from ._base import FamilyStrategy, MacroFamilyStrategy
from ix.core.backtesting.batch.constants import ASSET_CODES, MACRO_CODES, MULTI5
from ix.db.query import Series as DbSeries


class MomentumTrend(FamilyStrategy):
    """Combine momentum and trend signals to toggle equity/bond allocation."""
    family = "Ensemble"

    def __init__(
        self,
        mom_lookback: int = 12,
        sma_lookback: int = 10,
        equity: str = "SPY",
        bond: str = "IEF",
        mode: str = "both",
        **kw,
    ):
        self._mom_lookback = mom_lookback
        self._sma_lookback = sma_lookback
        self._equity = equity
        self._bond = bond
        self._mode = mode
        self._build_universe([equity, bond])
        mode_desc = {
            "both": "both signals must confirm for risk-on, both must fail for risk-off, otherwise 50/50 neutral",
            "any": "either signal confirms risk-on",
        }
        mode_text = mode_desc.get(
            mode,
            "equity weight = average of two binary signals (0, 0.5, or 1.0)",
        )
        self.label = f"MomentumTrend {equity}/{bond} mom={mom_lookback} sma={sma_lookback} mode={mode}"
        self.description = (
            f"Dual-signal ensemble: combines {mom_lookback}-month absolute momentum "
            f"(return > 0) with {sma_lookback}-month SMA trend (price > SMA) on "
            f"{equity}. Mode '{mode}': {mode_text}. "
            f"Risk-off asset: {bond}. Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self):
        m = self._monthly
        px = m[self._equity]
        sig_mom = px.pct_change(self._mom_lookback).iloc[-1] > 0
        sig_trend = px.iloc[-1] > px.rolling(self._sma_lookback).mean().iloc[-1]

        if self._mode == "both":
            if sig_mom and sig_trend:
                w_eq = 1.0
            elif not sig_mom and not sig_trend:
                w_eq = 0.0
            else:
                w_eq = 0.5
        elif self._mode == "any":
            w_eq = 1.0 if (sig_mom or sig_trend) else 0.0
        else:  # average
            w_eq = (int(sig_mom) + int(sig_trend)) / 2

        w = pd.Series(0.0, index=self.asset_names)
        w[self._equity] = w_eq
        w[self._bond] = 1.0 - w_eq
        return w

    def get_params(self):
        return {
            "mom_lookback": self._mom_lookback,
            "sma_lookback": self._sma_lookback,
            "equity": self._equity,
            "bond": self._bond,
            "mode": self._mode,
        }


class MacroTrendEnsemble(MacroFamilyStrategy):
    """Combine macro regime and trend signals for equity/bond allocation."""
    family = "Ensemble"

    def __init__(
        self,
        macro_code: str = "ISM_PMI",
        threshold: float = 50,
        lag: int = 1,
        sma_lookback: int = 10,
        equity: str = "SPY",
        bond: str = "IEF",
        **kw,
    ):
        self._macro_code = macro_code
        self._threshold = threshold
        self._macro_lag = lag
        self._sma_lookback = sma_lookback
        self._equity = equity
        self._bond = bond
        self._build_universe([equity, bond])
        self.label = f"MacroTrend {macro_code}>{threshold} sma={sma_lookback} {equity}/{bond}"
        self.description = (
            f"Macro + trend ensemble: combines {macro_code} level > {threshold} "
            f"(lagged {lag} periods) with {sma_lookback}-month SMA trend on "
            f"{equity}. Both positive → 100% {equity}. Both negative → 100% "
            f"{bond}. Mixed → 50/50. Pairs fundamental economic conditions with "
            f"price trend for confirmation. Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self):
        m = self._monthly
        px = m[self._equity]
        sig_trend = px.iloc[-1] > px.rolling(self._sma_lookback).mean().iloc[-1]

        macro = self._macro.resample("ME").last().ffill()
        if self._macro_lag > 0:
            macro = macro.shift(self._macro_lag)
        sig_macro = macro.iloc[-1] > self._threshold if len(macro) else False

        if sig_macro and sig_trend:
            w_eq = 1.0
        elif not sig_macro and not sig_trend:
            w_eq = 0.0
        else:
            w_eq = 0.5

        w = pd.Series(0.0, index=self.asset_names)
        w[self._equity] = w_eq
        w[self._bond] = 1.0 - w_eq
        return w

    def get_params(self):
        return {
            "macro_code": self._macro_code,
            "threshold": self._threshold,
            "lag": self._macro_lag,
            "sma_lookback": self._sma_lookback,
            "equity": self._equity,
            "bond": self._bond,
        }


class TripleSignal(MacroFamilyStrategy):
    """Three-signal voting: momentum + trend + macro → graduated equity weight."""
    family = "Ensemble"

    def __init__(
        self,
        macro_code: str = "ISM_PMI",
        threshold: float = 50,
        lag: int = 1,
        mom_lookback: int = 12,
        sma_lookback: int = 10,
        equity: str = "SPY",
        bond: str = "IEF",
        **kw,
    ):
        self._macro_code = macro_code
        self._threshold = threshold
        self._macro_lag = lag
        self._mom_lookback = mom_lookback
        self._sma_lookback = sma_lookback
        self._equity = equity
        self._bond = bond
        self._build_universe([equity, bond])
        self.label = (
            f"TripleSignal {macro_code}>{threshold} mom={mom_lookback} "
            f"sma={sma_lookback} {equity}/{bond}"
        )
        self.description = (
            f"Triple-signal voting: three independent binary signals — "
            f"{mom_lookback}-month momentum, {sma_lookback}-month SMA trend, "
            f"and {macro_code} > {threshold}. Counts votes: 3/3 → 100% {equity}, "
            f"2/3 → 70%, 1/3 → 30%, 0/3 → 0%. Graduated allocation reduces "
            f"regime-switching whipsaw. Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self):
        m = self._monthly
        px = m[self._equity]
        sig_mom = px.pct_change(self._mom_lookback).iloc[-1] > 0
        sig_trend = px.iloc[-1] > px.rolling(self._sma_lookback).mean().iloc[-1]

        macro = self._macro.resample("ME").last().ffill()
        if self._macro_lag > 0:
            macro = macro.shift(self._macro_lag)
        sig_macro = macro.iloc[-1] > self._threshold if len(macro) else False

        votes = int(sig_mom) + int(sig_trend) + int(sig_macro)
        weight_map = {3: 1.0, 2: 0.7, 1: 0.3, 0: 0.0}
        w_eq = weight_map[votes]

        w = pd.Series(0.0, index=self.asset_names)
        w[self._equity] = w_eq
        w[self._bond] = 1.0 - w_eq
        return w

    def get_params(self):
        return {
            "macro_code": self._macro_code,
            "threshold": self._threshold,
            "lag": self._macro_lag,
            "mom_lookback": self._mom_lookback,
            "sma_lookback": self._sma_lookback,
            "equity": self._equity,
            "bond": self._bond,
        }


class MultiAssetTrendMom(FamilyStrategy):
    """Multi-asset trend + momentum: score passing assets, equal-weight top N."""
    family = "Ensemble"

    def __init__(
        self,
        sma_months: int = 10,
        mom_months: int = 6,
        assets: list[str] = MULTI5,
        cash: str = "BIL",
        top_n: int = 2,
        **kw,
    ):
        self._sma_months = sma_months
        self._mom_months = mom_months
        self._assets = assets
        self._cash = cash
        self._top_n = top_n
        self._build_universe(assets + ([cash] if cash else []))
        self.label = f"MultiTrendMom top{top_n}/{len(assets)} sma={sma_months} mom={mom_months}"
        self.description = (
            f"Multi-asset trend + momentum filter: screens {len(assets)} assets "
            f"for both SMA trend ({sma_months}-month) AND positive momentum "
            f"({mom_months}-month return > 0). Only assets passing both filters "
            f"qualify. Ranks qualifiers by momentum, holds top {top_n} in equal "
            f"weight. If none qualify → 100% {cash}. Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self):
        m = self._monthly
        avail = self._avail(self._assets)
        passing = []
        mom_scores = {}

        for a in avail:
            px = m[a]
            trend_ok = px.iloc[-1] > px.rolling(self._sma_months).mean().iloc[-1]
            mom_ret = px.pct_change(self._mom_months).iloc[-1]
            mom_ok = mom_ret > 0
            if trend_ok and mom_ok:
                passing.append(a)
                mom_scores[a] = mom_ret

        if passing:
            ranked = sorted(passing, key=lambda a: mom_scores[a], reverse=True)
            selected = ranked[: self._top_n]
            return self._eq_weight(selected)

        return self._eq_weight([self._cash] if self._cash in self.asset_names else [])

    def get_params(self):
        return {
            "sma_months": self._sma_months,
            "mom_months": self._mom_months,
            "assets": self._assets,
            "cash": self._cash,
            "top_n": self._top_n,
        }
