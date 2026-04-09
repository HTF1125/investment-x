"""Advanced strategy families — multi-timeframe, composite macro, vol-scaled, adaptive."""

import pandas as pd
import numpy as np
from ._base import FamilyStrategy, MacroFamilyStrategy
from ix.core.backtesting.batch.constants import ASSET_CODES, MACRO_CODES, SECTORS, MULTI5, MULTI8, BROAD6
from ix.db.query import Series as DbSeries


class MultiTimeframe(FamilyStrategy):
    """Weighted blend of short and long momentum signals for equity/bond switching."""
    family = "Advanced"

    def __init__(
        self,
        short_lb: int = 3,
        long_lb: int = 12,
        short_weight: float = 0.4,
        equity: str = "SPY",
        bond: str = "IEF",
        name: str = "",
        **kw,
    ):
        self._short_lb = short_lb
        self._long_lb = long_lb
        self._short_weight = short_weight
        self._equity = equity
        self._bond = bond
        self._build_universe([equity, bond])
        self.label = name or f"MultiTF {short_lb}/{long_lb} w={short_weight}"
        self.description = (
            f"Multi-timeframe momentum blend: combines a short-term {short_lb}-month "
            f"momentum signal (weight {short_weight:.0%}) with a long-term {long_lb}-month "
            f"signal (weight {1-short_weight:.0%}). Each signal is binary (return > 0 = 1, "
            f"else = 0). The blended score drives the {equity}/{bond} split — score 1.0 = "
            f"fully invested, 0.0 = fully defensive. Captures both trend persistence and "
            f"trend-reversal. Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self) -> pd.Series:
        hist = self._monthly.loc[:self.d]
        eq = self._equity
        if eq not in hist.columns or len(hist) < self._long_lb + 1:
            return self._eq_weight([self._equity, self._bond])

        short_ret = hist[eq].iloc[-1] / hist[eq].iloc[-self._short_lb - 1] - 1
        long_ret = hist[eq].iloc[-1] / hist[eq].iloc[-self._long_lb - 1] - 1

        short_sig = float(short_ret > 0)
        long_sig = float(long_ret > 0)
        score = self._short_weight * short_sig + (1 - self._short_weight) * long_sig

        w = {self._equity: score, self._bond: 1 - score}
        return pd.Series(w).reindex(self.asset_names, fill_value=0.0)

    def get_params(self) -> dict:
        return {
            "short_lb": self._short_lb,
            "long_lb": self._long_lb,
            "short_weight": self._short_weight,
            "equity": self._equity,
            "bond": self._bond,
        }


class CompositeMacro(MacroFamilyStrategy):
    """Score multiple macro indicators against thresholds; allocate by composite score.

    Each indicator tuple: (macro_code, threshold, lag, weight).
    Score >= 0.6 -> equity, <= 0.3 -> bond, else 50/50.
    """
    family = "Advanced"

    def __init__(
        self,
        indicators: list[tuple[str, float, int, float]],
        equity: str = "SPY",
        bond: str = "IEF",
        name: str = "",
        **kw,
    ):
        self._indicators = indicators
        self._equity = equity
        self._bond = bond
        self._macro_code = None  # disable single-macro resolution in base
        self._build_universe([equity, bond])
        self.label = name or f"CompositeMacro {len(indicators)} indicators"
        codes = ", ".join(t[0] for t in indicators)
        self.description = (
            f"Composite macro scoring: evaluates {len(indicators)} macro indicators "
            f"({codes}) against their thresholds with publication lags. Each indicator "
            f"gets a weight — total score = sum(passing_weights) / sum(all_weights). "
            f"Score >= 60% → 100% {equity}. Score <= 30% → 100% {bond}. Between → 50/50. "
            f"Aggregates multiple economic signals for a robust macro regime assessment. "
            f"Monthly rebalance."
        )
        super().__init__(**kw)

    def initialize(self):
        super().initialize()
        self._macro_series = {}
        for macro_code, _thresh, _lag, _weight in self._indicators:
            if macro_code in MACRO_CODES:
                self._macro_series[macro_code] = DbSeries(MACRO_CODES[macro_code])

    def generate_signals(self) -> pd.Series:
        total_weight = sum(w for _, _, _, w in self._indicators)
        if total_weight < 1e-10:
            return self._eq_weight([self._equity, self._bond])

        passing_weight = 0.0
        for macro_code, threshold, lag, weight in self._indicators:
            series = self._macro_series.get(macro_code)
            if series is None or series.empty:
                continue
            m = series.loc[:self.d]
            if len(m) < lag + 1:
                continue
            val = m.iloc[-(lag + 1)]
            if pd.notna(val) and val > threshold:
                passing_weight += weight

        score = passing_weight / total_weight

        if score >= 0.6:
            w = {self._equity: 1.0, self._bond: 0.0}
        elif score <= 0.3:
            w = {self._equity: 0.0, self._bond: 1.0}
        else:
            w = {self._equity: 0.5, self._bond: 0.5}
        return pd.Series(w).reindex(self.asset_names, fill_value=0.0)

    def get_params(self) -> dict:
        return {
            "indicators": self._indicators,
            "equity": self._equity,
            "bond": self._bond,
        }


class VolScaledMomentum(FamilyStrategy):
    """Momentum divided by volatility, inverse-vol weighted among top N winners."""
    family = "Advanced"

    def __init__(
        self,
        lookback: int = 12,
        vol_window: int = 6,
        assets: list[str] | None = None,
        top_n: int = 2,
        cash: str | None = None,
        name: str = "",
        **kw,
    ):
        self._lookback = lookback
        self._vol_window = vol_window
        self._assets = assets or MULTI5
        self._top_n = top_n
        self._cash = cash

        all_assets = list(self._assets)
        if cash and cash not in all_assets:
            all_assets.append(cash)
        self._build_universe(all_assets)

        asset_list = ", ".join(self._assets)
        cash_desc = ", filtering by BIL cash hurdle" if cash else ""
        self.label = name or f"VolScaledMom {lookback}m Top{top_n}"
        self.description = (
            f"Vol-scaled momentum rotation: ranks {len(self._assets)} assets by "
            f"momentum-to-volatility ratio (return / vol) using {lookback}-month returns "
            f"and {vol_window}-month realized vol. Selects top {top_n} by score"
            f"{cash_desc}. Weights winners by inverse vol — lower-vol assets get more. "
            f"Favors assets with strong risk-adjusted momentum. Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self) -> pd.Series:
        px = self._monthly
        lb = self._lookback
        vw = self._vol_window
        assets = self._avail(self._assets)
        cash = self._cash

        if len(px) <= max(lb, vw) or not assets:
            return self._eq_weight(assets or ["SPY"])

        ret = px[assets].iloc[-1] / px[assets].iloc[-lb - 1] - 1
        monthly_ret = px[assets].pct_change()
        vol = monthly_ret.iloc[-vw:].std() * np.sqrt(12)
        vol = vol.replace(0, np.nan)

        score = (ret / vol).dropna()

        # Cash hurdle filter
        if cash and cash in px.columns and len(px[cash].dropna()) > lb:
            cash_ret = px[cash].iloc[-1] / px[cash].iloc[-lb - 1] - 1
            cash_vol = monthly_ret[cash].iloc[-vw:].std() * np.sqrt(12) if cash in monthly_ret.columns else 0.01
            cash_score = cash_ret / cash_vol if cash_vol > 0 else 0
            candidates = score[score > cash_score]
            if candidates.empty:
                w = pd.Series(0.0, index=self.asset_names)
                if cash in w.index:
                    w[cash] = 1.0
                return w
        else:
            candidates = score[score > 0]

        if candidates.empty:
            if cash:
                w = pd.Series(0.0, index=self.asset_names)
                if cash in w.index:
                    w[cash] = 1.0
                return w
            return self._eq_weight(assets)

        top = candidates.nlargest(min(self._top_n, len(candidates)))

        # Inverse-vol weight among winners
        inv_vol = 1.0 / vol.reindex(top.index).replace(0, np.nan).dropna()
        if inv_vol.empty:
            w = pd.Series(1.0 / len(top), index=top.index)
        else:
            w = inv_vol / inv_vol.sum()

        return w.reindex(self.asset_names, fill_value=0.0)

    def get_params(self) -> dict:
        return {
            "lookback": self._lookback,
            "vol_window": self._vol_window,
            "assets": self._assets,
            "top_n": self._top_n,
            "cash": self._cash,
        }


class AdaptiveMomentum(FamilyStrategy):
    """Switch between short and long lookback based on realized volatility."""
    family = "Advanced"

    def __init__(
        self,
        short_lb: int = 3,
        long_lb: int = 12,
        vol_threshold: float = 0.20,
        vol_window: int = 6,
        equity: str = "SPY",
        bond: str = "IEF",
        name: str = "",
        **kw,
    ):
        self._short_lb = short_lb
        self._long_lb = long_lb
        self._vol_threshold = vol_threshold
        self._vol_window = vol_window
        self._equity = equity
        self._bond = bond
        self._build_universe([equity, bond])
        self.label = name or f"AdaptiveMom {short_lb}/{long_lb} vol>{vol_threshold:.0%}"
        self.description = (
            f"Adaptive lookback momentum: uses {short_lb}-month lookback when {equity} "
            f"realized vol exceeds {vol_threshold:.0%} (fast-moving regime), otherwise "
            f"uses {long_lb}-month lookback (calm regime). If return over the chosen "
            f"lookback is positive → 100% {equity}, else 100% {bond}. Adapts signal "
            f"speed to market conditions — faster in volatile markets, slower in calm. "
            f"Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self) -> pd.Series:
        hist = self._monthly.loc[:self.d]
        eq = self._equity
        if eq not in hist.columns or len(hist) < self._long_lb + 1:
            return self._eq_weight([self._equity, self._bond])

        monthly_ret = hist[eq].pct_change()
        realized_vol = monthly_ret.iloc[-self._vol_window:].std() * np.sqrt(12)

        lb = self._short_lb if realized_vol > self._vol_threshold else self._long_lb
        ret = hist[eq].iloc[-1] / hist[eq].iloc[-lb - 1] - 1

        if ret > 0:
            return self._eq_weight([self._equity])
        return self._eq_weight([self._bond])

    def get_params(self) -> dict:
        return {
            "short_lb": self._short_lb,
            "long_lb": self._long_lb,
            "vol_threshold": self._vol_threshold,
            "vol_window": self._vol_window,
            "equity": self._equity,
            "bond": self._bond,
        }


class TrendVolFilter(FamilyStrategy):
    """Trend + volatility filter: scale equity allocation by vol cap when trend is up."""
    family = "Advanced"

    def __init__(
        self,
        sma_months: int = 10,
        vol_window: int = 6,
        vol_cap: float = 0.20,
        equity: str = "SPY",
        bond: str = "IEF",
        name: str = "",
        **kw,
    ):
        self._sma_months = sma_months
        self._vol_window = vol_window
        self._vol_cap = vol_cap
        self._equity = equity
        self._bond = bond
        self._build_universe([equity, bond])
        self.label = name or f"TrendVolFilter SMA{sma_months} cap={vol_cap:.0%}"
        self.description = (
            f"Trend + volatility overlay: first checks if {equity} is above its "
            f"{sma_months}-month SMA (trend filter). If trend is down → 0% {equity}. "
            f"If trend is up but realized vol exceeds {vol_cap:.0%} → scales exposure "
            f"down (weight = {vol_cap:.0%} / realized_vol). If trend is up and vol is "
            f"low → 100% {equity}. Combines directional trend with volatility-based "
            f"position sizing. Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self) -> pd.Series:
        hist = self._monthly.loc[:self.d]
        eq = self._equity
        if eq not in hist.columns or len(hist) < self._sma_months + 1:
            return self._eq_weight([self._equity, self._bond])

        price = hist[eq].iloc[-1]
        sma_val = hist[eq].iloc[-self._sma_months:].mean()

        # Trend down -> 0% equity
        if price <= sma_val:
            return self._eq_weight([self._bond])

        # Trend up -> check vol
        monthly_ret = hist[eq].pct_change()
        realized_vol = monthly_ret.iloc[-self._vol_window:].std() * np.sqrt(12)

        if realized_vol > self._vol_cap and realized_vol > 0:
            eq_weight = min(1.0, self._vol_cap / realized_vol)
        else:
            eq_weight = 1.0

        w = {self._equity: eq_weight, self._bond: 1 - eq_weight}
        return pd.Series(w).reindex(self.asset_names, fill_value=0.0)

    def get_params(self) -> dict:
        return {
            "sma_months": self._sma_months,
            "vol_window": self._vol_window,
            "vol_cap": self._vol_cap,
            "equity": self._equity,
            "bond": self._bond,
        }
