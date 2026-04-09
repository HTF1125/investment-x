import pandas as pd
from typing import Optional
from ix.db import MultiSeries, Series
from ix.core.backtesting.engine import Strategy, RiskManager

class Classic6040(Strategy):
    """Classic 60/40 — 60% US Equity, 40% US Aggregate Bond."""

    universe = {
        "SPY": {"code": "SPY US EQUITY:PX_LAST", "weight": 0.6},
        "AGG": {"code": "AGG US EQUITY:PX_LAST", "weight": 0.4},
    }
    bm_assets: dict[str, float] = {"SPY": 1.0}
    frequency = "ME"
    start = pd.Timestamp("2004-11-18")

    def initialize(self) -> None:
        pass

    def generate_signals(self) -> pd.Series:
        return pd.Series({"SPY": 0.6, "AGG": 0.4})

    def allocate(self) -> pd.Series:
        return pd.Series({"SPY": 0.6, "AGG": 0.4})


class AllWeather(Strategy):
    """Ray Dalio All Weather — risk-parity-inspired static allocation.

    30% US Equity, 40% Long-Term Treasuries, 15% Intermediate Treasuries,
    7.5% Gold, 7.5% Commodities.
    """

    universe = {
        "SPY": {"code": "SPY US EQUITY:PX_LAST", "weight": 0.30},
        "TLT": {"code": "TLT US EQUITY:PX_LAST", "weight": 0.40},
        "IEI": {"code": "IEI US EQUITY:PX_LAST", "weight": 0.15},
        "GLD": {"code": "GLD US EQUITY:PX_LAST", "weight": 0.075},
        "DBC": {"code": "DBC US EQUITY:PX_LAST", "weight": 0.075},
    }
    bm_assets: dict[str, float] = {"SPY": 0.6, "TLT": 0.4}
    frequency = "ME"
    start = pd.Timestamp("2007-01-03")

    def initialize(self) -> None:
        pass

    def generate_signals(self) -> pd.Series:
        return pd.Series({k: v["weight"] for k, v in self.universe.items()})

    def allocate(self) -> pd.Series:
        return pd.Series({k: v["weight"] for k, v in self.universe.items()})


class GoldenButterfly(Strategy):
    """Golden Butterfly — 20% each: US Large Cap, US Small Cap Value,
    Long-Term Treasuries, Short-Term Treasuries, Gold.
    """

    universe = {
        "SPY": {"code": "SPY US EQUITY:PX_LAST", "weight": 0.20},
        "IWN": {"code": "IWN US EQUITY:PX_LAST", "weight": 0.20},
        "TLT": {"code": "TLT US EQUITY:PX_LAST", "weight": 0.20},
        "SHY": {"code": "SHY US EQUITY:PX_LAST", "weight": 0.20},
        "GLD": {"code": "GLD US EQUITY:PX_LAST", "weight": 0.20},
    }
    bm_assets: dict[str, float] = {"SPY": 0.6, "TLT": 0.4}
    frequency = "ME"
    start = pd.Timestamp("2005-01-03")

    def initialize(self) -> None:
        pass

    def generate_signals(self) -> pd.Series:
        return pd.Series({k: v["weight"] for k, v in self.universe.items()})

    def allocate(self) -> pd.Series:
        return pd.Series({k: v["weight"] for k, v in self.universe.items()})


# ------------------------------------------------------------------
# SB_Carlson_DefenseFirst — Research-driven (ix-strategy-builder)
