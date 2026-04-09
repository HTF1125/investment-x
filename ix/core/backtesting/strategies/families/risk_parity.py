"""Risk parity strategy families — inverse volatility and vol-targeting."""

import pandas as pd
import numpy as np
from ._base import FamilyStrategy
from ix.core.backtesting.batch.constants import ASSET_CODES, SECTORS, MULTI5, MULTI8, BROAD6


class InverseVol(FamilyStrategy):
    """Inverse-volatility weighting: allocate proportional to 1/vol, normalized."""
    family = "RiskParity"

    def __init__(self, vol_window: int, assets: list[str], **kw):
        self.vol_window = vol_window
        self._iv_assets = assets
        self._build_universe(assets)
        n = len(assets)
        asset_list = ", ".join(assets)
        self.label = f"InvVol({vol_window}m, {n} assets)"
        self.description = (
            f"Inverse volatility weighting: allocates to {n} assets ({asset_list}) "
            f"in proportion to 1/volatility, where volatility is the {vol_window}-month "
            f"realized standard deviation (annualized). Lower-vol assets get higher "
            f"weight. Normalized to sum 100%. Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self) -> pd.Series:
        hist = self._monthly.loc[:self.d]
        assets = self._avail(self._iv_assets)
        if len(hist) <= self.vol_window or not assets:
            return self._eq_weight(assets)

        ret = hist[assets].pct_change().iloc[-self.vol_window:]
        vol = ret.std() * np.sqrt(12)
        vol = vol.replace(0, np.nan).dropna()
        if vol.empty:
            return self._eq_weight(assets)

        inv = 1.0 / vol
        w = inv / inv.sum()
        return w.reindex(self.asset_names, fill_value=0.0)

    def get_params(self) -> dict:
        return {"vol_window": self.vol_window, "assets": self._iv_assets}


class VolTarget(FamilyStrategy):
    """Volatility targeting: scale equity exposure to match a target volatility."""
    family = "RiskParity"

    def __init__(
        self,
        target_vol: float,
        vol_window: int = 12,
        equity: str = "SPY",
        bond: str = "IEF",
        **kw,
    ):
        self.target_vol = target_vol
        self.vol_window = vol_window
        self._equity = equity
        self._bond = bond
        self._build_universe([equity, bond])
        self.label = f"VolTarget({target_vol:.0%}, {vol_window}m)"
        self.description = (
            f"Volatility targeting: scales {equity} exposure to maintain "
            f"{target_vol:.0%} annualized volatility using a {vol_window}-month "
            f"trailing window. equity_weight = min(100%, target_vol / realized_vol). "
            f"Remainder in {bond}. When realized vol is low, can be fully invested; "
            f"when high, reduces exposure. Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self) -> pd.Series:
        hist = self._monthly.loc[:self.d]
        if self._equity not in hist.columns or len(hist) <= self.vol_window:
            return pd.Series({self._equity: 0.5, self._bond: 0.5}).reindex(
                self.asset_names, fill_value=0.0
            )
        ret = hist[self._equity].pct_change().iloc[-self.vol_window:]
        realized_vol = ret.std() * np.sqrt(12)
        if realized_vol < 1e-10:
            return pd.Series({self._equity: 0.5, self._bond: 0.5}).reindex(
                self.asset_names, fill_value=0.0
            )
        eq_weight = min(1.0, max(0.0, self.target_vol / realized_vol))
        w = {self._equity: eq_weight, self._bond: 1 - eq_weight}
        return pd.Series(w).reindex(self.asset_names, fill_value=0.0)

    def get_params(self) -> dict:
        return {
            "target_vol": self.target_vol,
            "vol_window": self.vol_window,
            "equity": self._equity,
            "bond": self._bond,
        }
