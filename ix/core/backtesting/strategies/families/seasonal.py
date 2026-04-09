"""Seasonal strategy family — calendar-based allocation."""

import pandas as pd
import numpy as np
from ._base import FamilyStrategy, MacroFamilyStrategy
from ix.core.backtesting.batch.constants import ASSET_CODES, MACRO_CODES
from ix.db.query import Series as DbSeries


class SeasonalStrategy(FamilyStrategy):
    """Calendar-based seasonal rotation.

    Hold equity during specified months, bonds otherwise.
    Classic example: "Sell in May" → equity_months=[10,11,12,1,2,3,4].
    """

    family = "Seasonal"

    def __init__(
        self,
        equity_months: list[int] | None = None,
        equity: str = "SPY",
        bond: str = "IEF",
        name: str = "",
        **kw,
    ):
        if equity_months is None:
            equity_months = [10, 11, 12, 1, 2, 3, 4]
        self._equity_months = equity_months
        self._equity = equity
        self._bond = bond
        self._build_universe([equity, bond])
        month_abbr = {
            1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
        }
        month_names = ", ".join(month_abbr[m] for m in sorted(equity_months))
        months_str = ",".join(str(m) for m in equity_months)
        self.label = name or f"Seasonal [{months_str}]"
        self.description = (
            f"Calendar seasonality: holds 100% {equity} during historically "
            f"strong months ({month_names}) and 100% {bond} during weak months. "
            f"Based on the observation that equity returns are not uniformly "
            f"distributed across the calendar year — certain months consistently "
            f"outperform. Monthly rebalance."
        )
        super().__init__(**kw)

    def generate_signals(self) -> pd.Series:
        if self.d.month in self._equity_months:
            return self._eq_weight([self._equity])
        return self._eq_weight([self._bond])

    def get_params(self) -> dict:
        return {
            "equity_months": self._equity_months,
            "equity": self._equity,
            "bond": self._bond,
        }
