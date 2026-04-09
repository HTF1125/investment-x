"""Macro-driven strategy families — regime switching based on macro indicators."""

import pandas as pd
import numpy as np
from ._base import FamilyStrategy, MacroFamilyStrategy
from ix.core.backtesting.batch.constants import ASSET_CODES, MACRO_CODES
from ix.db.query import Series as DbSeries


class MacroLevel(MacroFamilyStrategy):
    """Switch between equity and bonds based on a macro indicator level vs threshold.

    When the macro reading (lagged) is above the threshold, hold equity;
    otherwise hold bonds.  Typical use: ISM PMI > 50 → risk-on.
    """

    family = "Macro"

    def __init__(
        self,
        macro_code: str = "ISM_PMI",
        threshold: float = 50.0,
        lag: int = 1,
        equity: str = "SPY",
        bond: str = "IEF",
        name: str = "",
        **kw,
    ):
        self._macro_code = macro_code
        self._threshold = threshold
        self._lag = lag
        self._equity = equity
        self._bond = bond
        indicator_name = macro_code.replace("_", " ")
        self._build_universe([equity, bond])
        self.label = name or f"MacroLevel {macro_code}>{threshold}"
        self.description = (
            f"Macro level threshold: holds 100% {equity} when {indicator_name} "
            f"exceeds {threshold}, otherwise 100% {bond}. Indicator value is "
            f"lagged {lag} period(s) for publication delay. Simple binary signal "
            f"based on the level of the economic indicator — above threshold "
            f"signals expansion, below signals contraction. Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self) -> pd.Series:
        m = self._macro.loc[:self.d]
        if len(m) < self._lag + 1:
            return self._eq_weight([self._bond])
        val = m.iloc[-(self._lag + 1)]
        if pd.isna(val):
            return self._eq_weight([self._bond])
        if val > self._threshold:
            return self._eq_weight([self._equity])
        return self._eq_weight([self._bond])

    def get_params(self) -> dict:
        return {
            "macro_code": self._macro_code,
            "threshold": self._threshold,
            "lag": self._lag,
            "equity": self._equity,
            "bond": self._bond,
        }


class MacroDirection(MacroFamilyStrategy):
    """Switch based on the direction of a macro indicator's moving average.

    If the MA is rising (current > previous), hold equity; otherwise hold bonds.
    """

    family = "Macro"

    def __init__(
        self,
        macro_code: str = "ISM_PMI",
        lag: int = 1,
        ma_window: int = 3,
        equity: str = "SPY",
        bond: str = "IEF",
        name: str = "",
        **kw,
    ):
        self._macro_code = macro_code
        self._lag = lag
        self._ma_window = ma_window
        self._equity = equity
        self._bond = bond
        indicator_name = macro_code.replace("_", " ")
        self._build_universe([equity, bond])
        self.label = name or f"MacroDir {macro_code} MA{ma_window}"
        self.description = (
            f"Macro direction: holds 100% {equity} when the {ma_window}-month "
            f"moving average of {indicator_name} is rising (current > previous), "
            f"otherwise 100% {bond}. Lagged {lag} period(s). Direction captures "
            f"momentum in the economic cycle rather than absolute level. "
            f"Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self) -> pd.Series:
        m = self._macro.loc[:self.d]
        ma = m.rolling(self._ma_window, min_periods=1).mean()
        if len(ma) < self._lag + 2:
            return self._eq_weight([self._bond])
        curr = ma.iloc[-(self._lag + 1)]
        prev = ma.iloc[-(self._lag + 2)]
        if pd.isna(curr) or pd.isna(prev):
            return self._eq_weight([self._bond])
        if curr > prev:
            return self._eq_weight([self._equity])
        return self._eq_weight([self._bond])

    def get_params(self) -> dict:
        return {
            "macro_code": self._macro_code,
            "lag": self._lag,
            "ma_window": self._ma_window,
            "equity": self._equity,
            "bond": self._bond,
        }


class VixRegime(MacroFamilyStrategy):
    """Contrarian VIX regime strategy.

    High VIX (fear) is a bullish signal → hold equity.
    Low VIX (complacency) is a bearish signal → hold bonds.
    Between thresholds → 50/50 split.
    """

    family = "Macro"

    def __init__(
        self,
        high_thresh: float = 25.0,
        low_thresh: float = 15.0,
        equity: str = "SPY",
        bond: str = "IEF",
        name: str = "",
        **kw,
    ):
        self._macro_code = "VIX"
        self._high_thresh = high_thresh
        self._low_thresh = low_thresh
        self._equity = equity
        self._bond = bond
        self._build_universe([equity, bond])
        self.label = name or f"VixRegime {low_thresh}/{high_thresh}"
        self.description = (
            f"Contrarian VIX regime: holds 100% {equity} when VIX > {high_thresh} "
            f"(high fear = buying opportunity), 100% {bond} when VIX < {low_thresh} "
            f"(low fear = complacency risk), and 50/50 between thresholds. "
            f"Contrarian logic — elevated volatility historically precedes "
            f"mean-reversion and market recovery. Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self) -> pd.Series:
        m = self._macro.loc[:self.d]
        if m.empty:
            return self._eq_weight([self._equity, self._bond])
        vix = m.iloc[-1]
        if pd.isna(vix):
            return self._eq_weight([self._equity, self._bond])
        if vix > self._high_thresh:
            return self._eq_weight([self._equity])
        if vix < self._low_thresh:
            return self._eq_weight([self._bond])
        return self._eq_weight([self._equity, self._bond])

    def get_params(self) -> dict:
        return {
            "high_thresh": self._high_thresh,
            "low_thresh": self._low_thresh,
            "equity": self._equity,
            "bond": self._bond,
        }
