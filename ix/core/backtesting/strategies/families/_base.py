"""Base classes for parameterized strategy families."""

import pandas as pd
from ix.core.backtesting.engine import Strategy
from ix.core.backtesting.batch.constants import ASSET_CODES, MACRO_CODES
from ix.db.query import Series as DbSeries


class FamilyStrategy(Strategy):
    """Base for all parameterized family strategies."""
    frequency = "ME"
    commission = 15
    slippage = 5
    start = pd.Timestamp("2005-01-01")
    mode = "production"
    author = "Strategy Research Lab"

    def _build_universe(
        self,
        assets: list[str],
        benchmark: dict[str, float] | None = None,
    ):
        """Build universe and set benchmark.

        Parameters
        ----------
        assets
            Ticker names for the strategy universe.
        benchmark
            Custom benchmark weights ``{asset: weight}``.
            If ``None``, auto-derived:
            - 2 assets → 50/50
            - N assets → equal-weight (1/N each)
        """
        self.universe = {
            a: {"code": ASSET_CODES[a], "weight": 0.0}
            for a in assets
            if a in ASSET_CODES
        }
        # Set first asset weight to 1.0 for universe normalization
        if self.universe:
            first = next(iter(self.universe))
            self.universe[first]["weight"] = 1.0

        # Benchmark
        if benchmark:
            self.bm_assets = benchmark
        elif len(assets) == 2:
            self.bm_assets = {assets[0]: 0.5, assets[1]: 0.5}
        elif len(assets) > 2:
            w = 1.0 / len(assets)
            self.bm_assets = {a: w for a in assets if a in ASSET_CODES}
        else:
            self.bm_assets = {assets[0]: 1.0} if assets else {}

    def initialize(self):
        self._monthly = self.pxs.rename(columns=self.code_to_name).resample("ME").last().ffill()

    def allocate(self):
        w = self.generate_signals()
        s = w.sum()
        return w / s if s > 1e-10 else pd.Series(0.0, index=self.asset_names)

    def _avail(self, assets: list[str]) -> list[str]:
        """Filter to assets available in monthly data."""
        return [a for a in assets if a in self._monthly.columns and self._monthly[a].notna().any()]

    def _eq_weight(self, assets: list[str]) -> pd.Series:
        if not assets:
            return pd.Series(0.0, index=self.asset_names)
        w = pd.Series(1.0 / len(assets), index=assets)
        return w.reindex(self.asset_names, fill_value=0.0)


class MacroFamilyStrategy(FamilyStrategy):
    """Base for strategies using macro data."""

    def initialize(self):
        super().initialize()
        if hasattr(self, '_macro_code') and self._macro_code:
            self._macro = DbSeries(MACRO_CODES[self._macro_code])
        else:
            self._macro = pd.Series(dtype=float)
