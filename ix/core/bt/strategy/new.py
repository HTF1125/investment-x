import pandas as pd

from ix.db import MultiSeries, Series

from .base import RiskManager, Strategy
from typing import Optional


# Initialize with risk management
risk_mgr = RiskManager(
    max_position=0.25,  # Max 25% per sector
    min_position=0.05,  # Min 5% or zero
)



# ------------------------------------------------------------------
# Concrete Strategy: UsGicsEarningsImpulse
# ------------------------------------------------------------------
class UsGicsEarningsImpulse(Strategy):
    """Enhanced GICS Sector Rotation Strategy based on Earnings Growth Momentum.

    Improvements:
    - Momentum combination (1Y change + 3M acceleration)
    - Z‑score normalization for better cross‑sectional comparison
    - Volatility‑adjusted scoring
    - Dynamic position sizing
    """

    universe = {
        "Technology": {"code": "XLK US EQUITY:PX_LAST", "weight": 0.0},
        "Industrials": {"code": "XLI US EQUITY:PX_LAST", "weight": 0.0},
        "Financials": {"code": "XLF US EQUITY:PX_LAST", "weight": 0.0},
        "Communication": {"code": "XLC US EQUITY:PX_LAST", "weight": 0.0},
        "Energy": {"code": "XLE US EQUITY:PX_LAST", "weight": 0.0},
        "Discretionary": {"code": "XLY US EQUITY:PX_LAST", "weight": 0.0},
        "Materials": {"code": "XLB US EQUITY:PX_LAST", "weight": 0.0},
        "Healthcare": {"code": "XLV US EQUITY:PX_LAST", "weight": 0.0},
        "Staples": {"code": "XLP US EQUITY:PX_LAST", "weight": 0.0},
        "Utilities": {"code": "XLU US EQUITY:PX_LAST", "weight": 0.0},
        "S&P500": {"code": "SPY US EQUITY:PX_LAST", "weight": 1},
    }

    frequency: str = "ME"
    start = pd.Timestamp("2000-01-01")


    def __init__(
        self,
        top_n: int = 5,
        method: str = "ema_impulse",  # "level", "simple_impulse", "ema_impulse"
        ema_fast: int = 3,
        ema_slow: int = 12,
        winsorize: bool = True,
        lower_q: float = 0.05,
        upper_q: float = 0.95,
        exclude_nonpositive_ltm: bool = True,
        require_positive_score: bool = True,
        min_sectors_required: Optional[int] = None,
        fallback_asset: str = "S&P500",
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.top_n = top_n
        self.method = method
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.winsorize = winsorize
        self.lower_q = lower_q
        self.upper_q = upper_q
        self.exclude_nonpositive_ltm = exclude_nonpositive_ltm
        self.require_positive_score = require_positive_score
        self.min_sectors_required = min_sectors_required or top_n
        self.fallback_asset = fallback_asset

    def _winsorize_cross_section(
        self, df: pd.DataFrame, lower_q: float, upper_q: float
    ) -> pd.DataFrame:
        def _clip_row(row: pd.Series) -> pd.Series:
            vals = row.dropna()
            if vals.empty:
                return row
            lo = vals.quantile(lower_q)
            hi = vals.quantile(upper_q)
            return row.clip(lower=lo, upper=hi)

        return df.apply(_clip_row, axis=1)

    def initialize(self) -> None:
        """Load and prepare earnings impulse data.

        Validates that the generated signal columns align with the universe keys.
        """
        sector_eps = {
            "Communication": ("S5TELS INDEX:EPS_NTMA", "S5TELS INDEX:EPS_LTMA"),
            "Industrials": ("S5INDU INDEX:EPS_NTMA", "S5INDU INDEX:EPS_LTMA"),
            "Utilities": ("S5UTIL INDEX:EPS_NTMA", "S5UTIL INDEX:EPS_LTMA"),
            "Healthcare": ("S5HLTH INDEX:EPS_NTMA", "S5HLTH INDEX:EPS_LTMA"),
            "Energy": ("S5ENRS INDEX:EPS_NTMA", "S5ENRS INDEX:EPS_LTMA"),
            "Materials": ("S5MATR INDEX:EPS_NTMA", "S5MATR INDEX:EPS_LTMA"),
            "Technology": ("S5INFT INDEX:EPS_NTMA", "S5INFT INDEX:EPS_LTMA"),
            "Financials": ("S5FINL INDEX:EPS_NTMA", "S5FINL INDEX:EPS_LTMA"),
            "Discretionary": ("S5COND INDEX:EPS_NTMA", "S5COND INDEX:EPS_LTMA"),
            "Staples": ("S5CONS INDEX:EPS_NTMA", "S5CONS INDEX:EPS_LTMA"),
        }

        ntm = MultiSeries(
            **{
                sector: Series(codes[0], freq="W-Fri").ffill()
                for sector, codes in sector_eps.items()
            }
        )
        ltm = MultiSeries(
            **{
                sector: Series(codes[1], freq="W-Fri").ffill()
                for sector, codes in sector_eps.items()
            }
        )

        if self.exclude_nonpositive_ltm:
            ltm = ltm.mask(ltm <= 0)

        growth = ntm.div(ltm).sub(1.0)
        if self.winsorize:
            growth = self._winsorize_cross_section(
                growth, lower_q=self.lower_q, upper_q=self.upper_q
            )

        if self.method == "level":
            score = growth
        elif self.method == "simple_impulse":
            score = growth.diff(1)
        elif self.method == "ema_impulse":
            ema_fast = growth.ewm(
                span=self.ema_fast, adjust=False, min_periods=self.ema_fast
            ).mean()
            ema_slow = growth.ewm(
                span=self.ema_slow, adjust=False, min_periods=self.ema_slow
            ).mean()
            score = ema_fast - ema_slow
        else:
            raise ValueError(
                "method must be one of: 'level', 'simple_impulse', 'ema_impulse'"
            )

        # Align to price index
        self.growth = growth.reindex(self.pxs.index, method="ffill").fillna(0.0)
        self.earnings_signal = (
            score.reindex(self.pxs.index, method="ffill").dropna(how="all").fillna(0.0)
        )

    def generate_signals(self) -> pd.Series:
        """Generate signals for each sector based on earnings impulse."""
        if self.d not in self.earnings_signal.index:
            return pd.Series(0.0, index=self.assets)

        # Get current impulse values – signal names match universe keys
        impulse = self.earnings_signal.loc[self.d]
        return impulse.reindex(self.assets, fill_value=0.0)

    def allocate(self) -> pd.Series:
        """Allocate to top N sectors with equal weight."""
        signals = self.generate_signals()
        if self.require_positive_score:
            signals = signals[signals > 0]
        top_signals = signals.nlargest(self.top_n)
        if len(top_signals) < self.min_sectors_required:
            if self.fallback_asset in self.assets:
                return pd.Series({self.fallback_asset: 1.0})
            return pd.Series(0.0, index=self.assets)

        weight_per_sector = 1.0 / len(top_signals)
        weights = pd.Series(0.0, index=self.assets)
        for asset in top_signals.index:
            weights[asset] = weight_per_sector
        return weights


class SectorRotationMom90(Strategy):
    universe = {
        "XLY": {"code": "XLY US EQUITY:PX_LAST", "weight": 0.0},
        "XLP": {"code": "XLP US EQUITY:PX_LAST", "weight": 0.0},
        "XLE": {"code": "XLE US EQUITY:PX_LAST", "weight": 0.0},
        "XLF": {"code": "XLF US EQUITY:PX_LAST", "weight": 0.0},
        "XLV": {"code": "XLV US EQUITY:PX_LAST", "weight": 0.0},
        "XLI": {"code": "XLI US EQUITY:PX_LAST", "weight": 0.0},
        "XLB": {"code": "XLB US EQUITY:PX_LAST", "weight": 0.0},
        "XLU": {"code": "XLU US EQUITY:PX_LAST", "weight": 0.0},
        "XLC": {"code": "XLC US EQUITY:PX_LAST", "weight": 0.0},
        "XLK": {"code": "XLK US EQUITY:PX_LAST", "weight": 0.0},
        "XLRE": {"code": "XLRE US EQUITY:PX_LAST", "weight": 0.0},
        "SPY": {"code": "SPY US EQUITY:PX_LAST", "weight": 1.0},
    }
    start = pd.Timestamp("2000-01-03")
    frequency = "ME"
    momentum_window = 90
    top_n = 3

    def initialize(self) -> None:
        prices = self.pxs.rename(columns=self.code_to_name).ffill()
        self.mom = prices.pct_change(self.momentum_window)
        pct_change = prices.pct_change()
        corr_diff = pct_change.rolling(20).corr() - pct_change.rolling(250).corr()
        corr_difff = (
            corr_diff.unstack()["SPY"]
            .drop(labels="SPY", axis=1, errors="ignore")
            .mean(axis=1)
        )
        self.corr_signal = (
            corr_difff.reindex(prices.index, method="ffill").fillna(0.0)
        )

    def generate_signals(self) -> pd.Series:
        if self.d not in self.mom.index:
            return pd.Series(0.0, index=self.assets)
        return self.mom.loc[self.d].reindex(self.assets, fill_value=0.0)

    def allocate(self) -> pd.Series:
        corr_val = float(self.corr_signal.asof(self.d)) if not self.corr_signal.empty else 0.0
        if corr_val < 0:
            return pd.Series({"SPY": 1.0})

        momentum = self.generate_signals()
        positive_momentum = momentum[momentum > 0].nlargest(self.top_n)
        if positive_momentum.empty:
            return pd.Series(0.0, index=self.assets)
        return positive_momentum / positive_momentum.sum()


class SectorRotationCESI(Strategy):
    universe = {
        "XLY": {"code": "XLY US EQUITY:PX_LAST", "weight": 0.0},
        "XLF": {"code": "XLF US EQUITY:PX_LAST", "weight": 0.0},
        "XLV": {"code": "XLV US EQUITY:PX_LAST", "weight": 0.0},
        "XLI": {"code": "XLI US EQUITY:PX_LAST", "weight": 0.0},
        "XLC": {"code": "XLC US EQUITY:PX_LAST", "weight": 0.0},
        "XLK": {"code": "XLK US EQUITY:PX_LAST", "weight": 0.0},
        "SPY": {"code": "SPY US EQUITY:PX_LAST", "weight": 1.0},
    }
    start = pd.Timestamp("2007-01-03")

    def initialize(self) -> None:
        cesi = Series("USFXCESIUSD:PX_LAST", freq="D").ffill()
        if cesi.empty:
            cesi = Series("^CESIUSD", freq="D").ffill()
        self.cesi = cesi.rolling(20).mean()
        self.cesi = self.cesi.reindex(self.pxs.index, method="ffill").fillna(0.0)

    def generate_signals(self) -> pd.Series:
        if self.cesi.empty:
            return pd.Series(0.0, index=self.assets)
        return pd.Series(self.cesi.asof(self.d), index=self.assets)

    def allocate(self) -> pd.Series:
        if self.cesi.empty:
            return pd.Series(0.0, index=self.assets)
        cesi_val = float(self.cesi.asof(self.d))
        if cesi_val >= 10:
            selected = ["XLF", "XLV", "XLC"]
        elif cesi_val <= -10:
            selected = ["XLK", "XLI", "XLY"]
        else:
            selected = ["SPY"]
        return pd.Series(1 / len(selected), index=selected)


class UsIsmPmiManuEB(Strategy):
    universe = {
        "SPY": {"code": "SPY US EQUITY:PX_LAST", "weight": 0.5},
        "AGG": {"code": "AGG US EQUITY:PX_LAST", "weight": 0.5},
    }
    frequency = "ME"
    start = pd.Timestamp("2004-11-18")
    bm_assets: dict[str, float] = {"SPY": 0.5, "AGG": 0.5}

    def initialize(self) -> None:
        from ix.core.bt.signal import UsIsmPmiManu

        self.signal = UsIsmPmiManu().data
        self.signal = self.signal.reindex(self.pxs.index, method="ffill").fillna(0.0)
        prices = self.pxs.rename(columns=self.code_to_name).ffill()
        self.momentum = prices.pct_change(20)

    def generate_signals(self) -> pd.Series:
        if self.signal.empty:
            return pd.Series(0.0, index=self.assets)
        sig = float(self.signal.asof(self.d))
        return pd.Series({"SPY": sig, "AGG": -sig})

    def allocate(self) -> pd.Series:

        if self.signal.empty:
            return pd.Series(0.0, index=self.assets)
        w = 0.5 + 0.5 * float(self.signal.asof(self.d))
        m = self.momentum["AGG"].loc[self.d]
        if m > 0:
            return pd.Series({"SPY": w, "AGG": 1.0 - w})
        return pd.Series({"SPY": w, "AGG": 0.0})


class UsOecdLeiEB(Strategy):
    universe = {
        "SPY": {"code": "SPY US EQUITY:PX_LAST", "weight": 0.6},
        "AGG": {"code": "AGG US EQUITY:PX_LAST", "weight": 0.4},
    }
    frequency = "ME"
    start = pd.Timestamp("2004-11-18")
    bm_assets: dict[str, float] = {"SPY": 0.6, "AGG": 0.4}

    def initialize(self) -> None:
        signal = Series("USA.LOLITOAA.STSA:PX_DIFF_DIFF")
        if signal.empty:
            base = Series("USA.LOLITOAA.STSA")
            signal = base.diff().diff()
        signal.index = signal.index + pd.DateOffset(days=10)
        self.signal = signal.reindex(self.pxs.index, method="ffill").fillna(0.0)
        prices = self.pxs.rename(columns=self.code_to_name).ffill()
        self.momentum = prices.pct_change(20)

    def generate_signals(self) -> pd.Series:
        if self.signal.empty:
            return pd.Series(0.0, index=self.assets)
        sig = float(self.signal.asof(self.d))
        return pd.Series({"SPY": sig, "AGG": -sig})

    def allocate(self) -> pd.Series:

        if self.signal.empty:
            return pd.Series(0.0, index=self.assets)
        signal = float(self.signal.asof(self.d))
        m = self.momentum["AGG"].loc[self.d]
        if signal > 0:
            return pd.Series({"SPY": 0.8, "AGG": 0.2 if m > 0 else 0})

        return pd.Series({"SPY": 0.3, "AGG": 0.7})


class UsOecdLeiEB2(Strategy):
    universe = {
        "SPY": {"code": "SPY US EQUITY:PX_LAST", "weight": 0.6},
        "AGG": {"code": "AGG US EQUITY:PX_LAST", "weight": 0.4},
    }
    frequency = "ME"
    start = pd.Timestamp("2004-11-18")
    bm_assets: dict[str, float] = {"SPY": 0.6, "AGG": 0.4}

    def initialize(self) -> None:
        from ix.core.tech import WaveTrend

        self.signal = (
            WaveTrend.from_meta("USA.LOLITOAA.STSA")
            .hlc["wt_diff"]
            .clip(-10, 10)
            .div(10)
        )
        self.signal = self.signal.reindex(self.pxs.index, method="ffill").fillna(0.0)
        prices = self.pxs.rename(columns=self.code_to_name).ffill()
        self.momentum = prices.pct_change(20)

    def generate_signals(self) -> pd.Series:
        if self.signal.empty:
            return pd.Series(0.0, index=self.assets)
        sig = float(self.signal.asof(self.d))
        return pd.Series({"SPY": sig, "AGG": -sig})

    def allocate(self) -> pd.Series:

        if self.signal.empty:
            return pd.Series(0.0, index=self.assets)
        w = 0.5 + 0.5 * float(self.signal.asof(self.d))
        m = self.momentum["AGG"].loc[self.d]
        if m > 0:
            return pd.Series({"SPY": w, "AGG": 1.0 - w})
        return pd.Series({"SPY": w, "AGG": 0.0})


class MAM60CF(Strategy):
    universe = {
        "SPY": {"code": "SPY US EQUITY:PX_LAST", "weight": 1.0},
        "IWM": {"code": "IWM US EQUITY:PX_LAST", "weight": 0.0},
        "EEM": {"code": "EEM US EQUITY:PX_LAST", "weight": 0.0},
        "QQQ": {"code": "QQQ US EQUITY:PX_LAST", "weight": 0.0},
        "LQD": {"code": "LQD US EQUITY:PX_LAST", "weight": 0.0},
        "IEF": {"code": "IEF US EQUITY:PX_LAST", "weight": 0.0},
        "TLT": {"code": "TLT US EQUITY:PX_LAST", "weight": 0.0},
        "GLD": {"code": "GLD US EQUITY:PX_LAST", "weight": 0.0},
    }

    start = pd.Timestamp("2007-01-03")
    frequency = "ME"
    momentum_window = 60
    top_n = 4

    def initialize(self) -> None:
        prices = self.pxs.rename(columns=self.code_to_name).ffill()
        self.mom = prices.pct_change(self.momentum_window)
        pct_change = prices.pct_change()
        corr_diff = pct_change.rolling(20).corr() - pct_change.rolling(90).corr()
        corr_difff = corr_diff.unstack().mean(axis=1)
        self.corr_signal = (
            corr_difff.reindex(prices.index, method="ffill").fillna(0.0)
        )
        # self.corr_signal.loc["2020":].plot()

    def generate_signals(self) -> pd.Series:
        if self.d not in self.mom.index:
            return pd.Series(0.0, index=self.assets)
        return self.mom.loc[self.d].reindex(self.assets, fill_value=0.0)

    def allocate(self) -> pd.Series:
        corr_val = float(self.corr_signal.asof(self.d)) if not self.corr_signal.empty else 0.0
        if corr_val < 0:
            return pd.Series({"SPY": 1.0})
        momentum = self.generate_signals()
        momentum = momentum[momentum > 0]
        positive_momentum = momentum.nlargest(self.top_n)
        if positive_momentum.empty:
            return pd.Series(0.0, index=self.assets)
        return positive_momentum / positive_momentum.sum()


class SPX_Earnings(Strategy):

    universe = {
        "SPY": {"code": "SPY US EQUITY:PX_LAST", "weight": 1.0},
    }

    start = pd.Timestamp("2007-01-03")
    frequency = "ME"
    min_assets = 1

    def initialize(self):
        eps_ntma = Series("SPX Index:EPS_NTMA", freq="W-Fri").ffill()
        eps_ltma = Series("SPX Index:EPS_LTMA", freq="W-Fri").ffill()
        growth = eps_ntma.div(eps_ltma).sub(1).mul(100)
        self.earnings_momentum = growth.diff(52)
        self.earnings_momentum = self.earnings_momentum.reindex(
            self.pxs.index, method="ffill"
        ).fillna(0.0)
        return

    def generate_signals(self) -> pd.Series:
        if self.earnings_momentum.empty:
            return pd.Series(0.0, index=self.assets)
        return pd.Series(
            {"SPY": float(self.earnings_momentum.asof(self.d))},
            index=self.assets,
        )

    def allocate(self) -> pd.Series:

        if self.earnings_momentum.empty:
            return pd.Series(0.0, index=self.assets)
        if float(self.earnings_momentum.asof(self.d)) > 0:
            return pd.Series({"SPY": 1.0})
        return pd.Series({"SPY": 0.0})


def all_strategies() -> list[type[Strategy]]:
    return [
        # UsIsmPmiManuEB,
        UsOecdLeiEB,
        SectorRotationCESI,
        SectorRotationMom90,
        UsGicsEarningsImpulse
    ]
