"""Mean-reversion strategy family — RSI and Z-score based."""

import pandas as pd
import numpy as np
from ._base import FamilyStrategy, MacroFamilyStrategy
from ix.core.backtesting.batch.constants import ASSET_CODES, MACRO_CODES
from ix.db.query import Series as DbSeries


class MeanReversionStrategy(FamilyStrategy):
    """Mean-reversion timing using RSI or Z-score on monthly prices.

    RSI mode: oversold → buy equity, overbought → sell to bonds, else 50/50.
    ZScore mode: z < -threshold → buy equity, z > threshold → sell to bonds, else 50/50.
    """

    family = "MeanReversion"

    def __init__(
        self,
        method: str = "rsi",
        period: int = 14,
        overbought: float = 70.0,
        oversold: float = 30.0,
        window: int = 20,
        threshold: float = 1.5,
        equity: str = "SPY",
        bond: str = "IEF",
        name: str = "",
        **kw,
    ):
        if method not in ("rsi", "zscore"):
            raise ValueError(f"method must be 'rsi' or 'zscore', got '{method}'")
        self._method = method
        self._period = period
        self._overbought = overbought
        self._oversold = oversold
        self._window = window
        self._threshold = threshold
        self._equity = equity
        self._bond = bond
        self._build_universe([equity, bond])
        if method == "rsi":
            self.label = name or f"RSI({period}) {oversold}/{overbought}"
            self.description = (
                f"RSI mean-reversion: computes {period}-period RSI on monthly "
                f"{equity} prices. RSI below {oversold} → oversold → 100% {equity} "
                f"(buy the dip). RSI above {overbought} → overbought → 100% {bond} "
                f"(take profit). Between thresholds → 50/50 neutral. Contrarian "
                f"approach that buys weakness and sells strength. Monthly rebalance."
            )
        else:
            self.label = name or f"ZScore({window}) ±{threshold}"
            self.description = (
                f"Z-score mean-reversion: computes the z-score of {equity} price "
                f"over a {window}-month window. Z < -{threshold} → deeply oversold "
                f"→ 100% {equity}. Z > +{threshold} → overbought → 100% {bond}. "
                f"Between → 50/50 neutral. Statistical approach to identifying "
                f"extreme price deviations from the mean. Monthly rebalance."
            )
        super().__init__(**kw)

    def _compute_rsi(self, series: pd.Series) -> float:
        """Compute RSI for the series up to current date."""
        delta = series.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(self._period, min_periods=self._period).mean()
        avg_loss = loss.rolling(self._period, min_periods=self._period).mean()
        if avg_gain.empty or avg_loss.empty:
            return 50.0
        ag = avg_gain.iloc[-1]
        al = avg_loss.iloc[-1]
        if pd.isna(ag) or pd.isna(al) or al == 0:
            return 50.0
        rs = ag / al
        return 100.0 - 100.0 / (1.0 + rs)

    def _compute_zscore(self, series: pd.Series) -> float:
        """Compute Z-score for the series up to current date."""
        if len(series) < self._window:
            return 0.0
        rolling_mean = series.rolling(self._window).mean()
        rolling_std = series.rolling(self._window).std()
        if rolling_std.empty:
            return 0.0
        m = rolling_mean.iloc[-1]
        s = rolling_std.iloc[-1]
        v = series.iloc[-1]
        if pd.isna(m) or pd.isna(s) or s == 0:
            return 0.0
        return (v - m) / s

    def generate_signals(self) -> pd.Series:
        if self._equity not in self._monthly.columns:
            return self._eq_weight([self._bond])
        prices = self._monthly[self._equity].loc[:self.d].dropna()
        if len(prices) < 2:
            return self._eq_weight([self._equity, self._bond])

        if self._method == "rsi":
            rsi = self._compute_rsi(prices)
            if rsi < self._oversold:
                return self._eq_weight([self._equity])
            if rsi > self._overbought:
                return self._eq_weight([self._bond])
            return self._eq_weight([self._equity, self._bond])
        else:
            z = self._compute_zscore(prices)
            if z < -self._threshold:
                return self._eq_weight([self._equity])
            if z > self._threshold:
                return self._eq_weight([self._bond])
            return self._eq_weight([self._equity, self._bond])

    def get_params(self) -> dict:
        if self._method == "rsi":
            return {
                "method": "rsi",
                "period": self._period,
                "overbought": self._overbought,
                "oversold": self._oversold,
                "equity": self._equity,
                "bond": self._bond,
            }
        return {
            "method": "zscore",
            "window": self._window,
            "threshold": self._threshold,
            "equity": self._equity,
            "bond": self._bond,
        }
