"""Strategy ABC — core backtest engine.

Defines the abstract interface (``initialize``, ``generate_signals``,
``allocate``) and the daily walk-forward simulation loop.  Analytics and
DB persistence are provided by the ``StrategyAnalytics`` and
``StrategySaver`` mixins.
"""

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

from ix.common import get_logger, as_date
from ix.db.query import Series, MultiSeries
from ix.core.backtesting.tca import MarketImpactModel, TransactionCostAnalyzer
from .portfolio import Position, Portfolio
from .risk import RiskManager
from .analytics import StrategyAnalytics
from .persistence import StrategySaver

logger = get_logger(__name__)


# ----------------------------------------------------------------------
class Strategy(ABC, StrategyAnalytics, StrategySaver):
    """Abstract base class for backtesting strategies.

    Subclasses must implement:
    - ``initialize()`` — load data, set up signals
    - ``generate_signals()`` — return raw scores per asset
    - ``allocate()`` (optional) — convert signals to weights

    Built-in capabilities:
    - Daily walk-forward simulation with configurable rebalance frequency
    - Transaction costs (flat bps or market-impact model)
    - Risk management constraints via ``RiskManager``
    - Analytics: ``stats()``, ``plot()``, ``calendar_returns()``, etc.
    - Persistence: ``save()`` / ``load()`` to DB
    """

    # Configuration — override in subclass
    principal: int = 10_000
    universe: Dict[str, Dict[str, Any]] = {
        "SPY": {"code": "SPY US Equity", "weight": 1.00},
    }
    start: pd.Timestamp = pd.Timestamp("2020-01-03")
    end: Optional[pd.Timestamp] = None
    frequency: str = "ME"
    commission: int = 15  # bps
    slippage: int = 5     # bps
    lag: int = 1           # periods to delay trade execution
    impact_model: Optional[MarketImpactModel] = None
    volume: Optional[pd.DataFrame] = None

    # Metadata — override in subclass
    label: str = ""
    family: str = ""
    mode: str = ""
    description: str = ""
    author: str = ""

    # ------------------------------------------------------------------
    # Init & universe resolution
    # ------------------------------------------------------------------

    def __init__(
        self,
        verbose: bool = False,
        risk_manager: Optional[RiskManager] = None,
        impact_model: Optional[MarketImpactModel] = None,
        volume: Optional[pd.DataFrame] = None,
    ) -> None:
        self.verbose = verbose
        self.risk_manager = risk_manager or RiskManager()
        if impact_model is not None:
            self.impact_model = impact_model
        if volume is not None:
            self.volume = volume

        self._initialize_universe()

        if self.principal <= 0:
            raise ValueError("principal must be positive")
        if self.commission < 0:
            raise ValueError("commission cannot be negative")
        if self.slippage < 0:
            raise ValueError("slippage cannot be negative")

        # TCA
        self._tca: Optional[TransactionCostAnalyzer] = None
        if self.impact_model is not None:
            self._tca = TransactionCostAnalyzer(
                impact_model=self.impact_model,
                commission_bps=float(self.commission),
            )

        # State
        self.d = self.start
        self.portfolio = Portfolio(cash=self.principal)
        self.pending_allocation: Optional[pd.Series] = None
        self.last_target_weights: pd.Series = pd.Series(dtype=float)

        # History
        self.book = {
            "date": [],
            "portfolio_value": [],
            "cash": [],
            "positions": [],
            "weights": [],
            "target_weights": [],
            "benchmark_value": [],
            "turnover": [],
            "transaction_costs": [],
        }

        # Data
        self.pxs = pd.DataFrame()
        self.trade_dates: List[pd.Timestamp] = []

    def _declared_assets(self) -> Optional[List[str]]:
        """Return assets declared on the subclass (class/instance attribute)."""
        if "assets" in self.__dict__:
            assets = self.__dict__.get("assets")
        else:
            assets = self.__class__.__dict__.get("assets")
        if assets is None or isinstance(assets, property):
            return None
        return list(assets)

    def _initialize_universe(self) -> None:
        """Resolve universe from subclass declarations."""
        # 1. Class-level universe dict
        raw = self.__class__.__dict__.get("universe")
        if isinstance(raw, dict) and raw:
            base = raw
        else:
            # 2. Assets list → auto-build
            assets = self._declared_assets()
            if assets:
                w = 1.0 / len(assets) if assets else 0
                base = {a: {"code": a, "weight": w} for a in assets}
            else:
                # 3. Instance attribute
                base = getattr(self, "universe", None)

        if not isinstance(base, dict) or not base:
            raise ValueError("Strategy must define a non-empty universe or assets list.")

        self.universe = self._normalize_universe(deepcopy(base))
        self._bm_assets = self.__class__.__dict__.get("bm_assets") or getattr(self, "bm_assets", None)

    @staticmethod
    def _normalize_universe(universe: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Normalize universe dict: ensure code and weight keys exist."""
        out: Dict[str, Dict[str, Any]] = {}
        for name, meta in universe.items():
            meta_dict = dict(meta) if isinstance(meta, dict) else {"code": meta}
            out[name] = {"code": meta_dict.get("code", name), "weight": meta_dict.get("weight")}

        weights = [v["weight"] for v in out.values()]
        if any(w is None for w in weights) or (sum(w or 0 for w in weights) == 0):
            equal = 1.0 / len(out) if out else 0
            for v in out.values():
                v["weight"] = equal
        return out

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @abstractmethod
    def initialize(self) -> None:
        """Load data and initialize strategy-specific variables."""

    @abstractmethod
    def generate_signals(self) -> pd.Series:
        """Generate raw signal/score for each asset (can be unbounded)."""

    def allocate(self) -> pd.Series:
        """Convert signals to portfolio weights. Override for custom logic."""
        signals = self.generate_signals()
        positive = signals[signals > 0]
        if positive.empty:
            return pd.Series(0.0, index=self.universe.keys())
        return positive / positive.sum()

    def get_params(self) -> Dict[str, Any]:
        """Return parameter dict for fingerprinting. Subclasses should override."""
        return {}

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def assets(self) -> List[str]:
        return list(self.universe.keys())

    @property
    def asset_names(self) -> List[str]:
        return list(self.universe.keys())

    @property
    def asset_codes(self) -> List[str]:
        return [v["code"] for v in self.universe.values()]

    @property
    def name_to_code(self) -> Dict[str, str]:
        return {name: v["code"] for name, v in self.universe.items()}

    @property
    def code_to_name(self) -> Dict[str, str]:
        return {v["code"]: name for name, v in self.universe.items()}

    @property
    def benchmark_weights(self) -> pd.Series:
        """Benchmark weights as Series indexed by asset code."""
        if self._bm_assets:
            bm = self._coerce_weights(self._bm_assets)
            bm = bm.rename(self.name_to_code)
            valid = bm.index.intersection(self.asset_codes)
            bm = bm.reindex(valid, fill_value=0.0)
            total = bm.sum()
            if total > 0:
                bm = bm / total
            return bm
        return pd.Series({v["code"]: v["weight"] for v in self.universe.values()})

    @property
    def current_prices(self) -> pd.Series:
        if self.d in self.pxs.index:
            return self.pxs.loc[self.d].dropna()
        return pd.Series(dtype=float)

    @property
    def dates(self) -> pd.DatetimeIndex:
        return pd.DatetimeIndex(self.book["date"])

    @property
    def nav(self) -> pd.Series:
        return pd.Series(data=self.book["portfolio_value"], index=self.dates, name="Strategy")

    @property
    def benchmark(self) -> pd.Series:
        return pd.Series(data=self.book["benchmark_value"], index=self.dates, name="Benchmark")

    @property
    def weights_history(self) -> pd.DataFrame:
        df = pd.DataFrame(self.book["weights"], index=self.dates).fillna(0.0)
        return df.rename(columns=self.code_to_name)

    # ------------------------------------------------------------------
    # Weight helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_weights(weights: Optional[Union[pd.Series, Dict[str, float]]]) -> pd.Series:
        if weights is None:
            return pd.Series(dtype=float)
        out = weights.copy() if isinstance(weights, pd.Series) else pd.Series(weights, dtype=float)
        return out.dropna()

    def _to_names(self, weights: pd.Series) -> pd.Series:
        """Convert weights to asset-name index, aligned to universe."""
        if weights.empty:
            return pd.Series(0.0, index=self.asset_names)
        renamed = weights.rename(self.code_to_name)
        # Drop unknowns
        valid = renamed.index.intersection(self.asset_names)
        if len(valid) < len(renamed):
            unknown = renamed.index.difference(valid)
            if not unknown.empty:
                logger.warning(f"Ignoring unknown assets in weights: {list(unknown)}")
            renamed = renamed.reindex(valid)
        if renamed.index.has_duplicates:
            renamed = renamed.groupby(level=0).sum()
        return renamed.reindex(self.asset_names, fill_value=0.0)

    def _to_codes(self, weights: pd.Series) -> pd.Series:
        """Convert weights to asset-code index, dropping unknowns."""
        if weights.empty:
            return pd.Series(dtype=float)
        coded = weights.rename(self.name_to_code)
        valid = coded.index.intersection(self.asset_codes)
        if len(valid) < len(coded):
            unknown = coded.index.difference(valid)
            if not unknown.empty:
                logger.warning(f"Ignoring unknown assets in weights: {list(unknown)}")
            coded = coded.reindex(valid)
        if coded.index.has_duplicates:
            coded = coded.groupby(level=0).sum()
        return coded

    def _portfolio_weights_by_name(self) -> pd.Series:
        weights = self.portfolio.weights
        return self._to_names(weights)

    # ------------------------------------------------------------------
    # Hooks
    # ------------------------------------------------------------------

    def on_trade(self, turnover: float, cost: float) -> None:
        """Hook called after trade execution."""

    def on_rebalance_signal(self, target_weights: pd.Series) -> None:
        """Hook called when rebalance signal is generated."""

    # ------------------------------------------------------------------
    # Trade execution
    # ------------------------------------------------------------------

    def execute_trades(self, target_weights: pd.Series) -> Tuple[float, float]:
        """Execute trades to reach target allocation. Returns (turnover, cost)."""
        if target_weights.index.has_duplicates:
            target_weights = target_weights.groupby(level=0).sum()
        unknown = target_weights.index.difference(self.asset_codes)
        if not unknown.empty:
            raise ValueError(f"target_weights has unknown asset codes: {list(unknown)}")

        prices = self.current_prices
        if prices.empty:
            return 0.0, 0.0

        all_assets = target_weights.index.union(self.portfolio.weights.index)
        current_weights = self.portfolio.weights.reindex(all_assets, fill_value=0.0)
        target = target_weights.reindex(all_assets, fill_value=0.0)
        turnover = (current_weights - target).abs().sum()
        if turnover < 1e-6:
            return 0.0, 0.0

        # Calculate costs
        if self._tca is not None:
            vol_series = self._get_volatility_at_date(self.d)
            vol_data = self._get_volume_at_date(self.d)
            total_cost = self._tca.total_cost_for_rebalance(
                target_weights=target, current_weights=current_weights,
                portfolio_value=self.portfolio.total_value, prices=prices,
                volume=vol_data, volatility=vol_series,
            )
        else:
            total_cost = self.portfolio.total_value * turnover * ((self.commission + self.slippage) / 10_000)

        net_value = self.portfolio.total_value - total_cost

        # Filter to tradable assets
        valid_assets = prices.index.intersection(target_weights.index)
        if valid_assets.empty:
            self.portfolio.positions = {}
            self.portfolio.cash = net_value
            return turnover, total_cost

        valid_weights = target_weights.reindex(valid_assets, fill_value=0.0)
        weight_sum = valid_weights.sum()
        if weight_sum < 1e-10:
            self.portfolio.positions = {}
            self.portfolio.cash = net_value
            return turnover, total_cost
        if weight_sum > 0:
            valid_weights = valid_weights / weight_sum

        target_values = valid_weights * net_value
        new_shares = target_values / prices.reindex(valid_assets)

        self.portfolio.positions = {
            asset: Position(shares=shares)
            for asset, shares in new_shares.items()
            if not pd.isna(shares) and shares > 0
        }

        invested = sum(pos.shares * prices.get(asset, 0) for asset, pos in self.portfolio.positions.items())
        self.portfolio.cash = net_value - invested
        self.portfolio.mark_to_market(prices)

        if self.verbose:
            logger.info(f"{as_date(self.d)}: Traded. Turnover: {turnover:.2%}, Cost: ${total_cost:.2f}")

        self.on_trade(turnover, total_cost)
        return turnover, total_cost

    def _get_volatility_at_date(self, date: pd.Timestamp) -> Optional[pd.Series]:
        if self.pxs.empty:
            return None
        loc = self.pxs.index.get_loc(date)
        if isinstance(loc, slice):
            loc = loc.stop - 1
        start = max(0, loc - 20)
        window = self.pxs.iloc[start:loc + 1]
        return window.pct_change().std() if len(window) >= 2 else None

    def _get_volume_at_date(self, date: pd.Timestamp) -> Optional[pd.Series]:
        if self.volume is None or self.volume.empty:
            return None
        loc = self.volume.index.get_indexer([date], method="ffill")[0]
        if loc < 0:
            return None
        window = self.volume.iloc[max(0, loc - 20):loc + 1]
        return window.mean() if not window.empty else None

    @property
    def tca(self) -> Optional[TransactionCostAnalyzer]:
        return self._tca

    # ------------------------------------------------------------------
    # Backtest simulation
    # ------------------------------------------------------------------

    def mark_to_market(self) -> None:
        prices = self.current_prices
        if not prices.empty:
            self.portfolio.mark_to_market(prices)

    def backtest(self) -> "Strategy":
        """Run the backtest simulation."""
        logger.info(f"Fetching data for {len(self.universe)} assets...")

        series_map = {v["code"]: Series(v["code"]) for v in self.universe.values()}
        self.pxs = MultiSeries(**series_map).sort_index()

        if self.start:
            self.pxs = self.pxs.loc[self.start:]
        if self.end:
            self.pxs = self.pxs.loc[:self.end]
        if self.pxs.empty:
            logger.error("No price data found.")
            return self

        self.trade_dates = self._generate_trade_dates()
        self.initialize()
        benchmark = self._calculate_benchmark()

        for i, self.d in enumerate(self.pxs.index):
            self.mark_to_market()

            # Execute pending orders (lag > 0)
            if self.pending_allocation is not None:
                turnover, cost = self.execute_trades(self.pending_allocation)
                self.pending_allocation = None
            else:
                turnover, cost = 0.0, 0.0

            # Generate signals on rebalance dates
            if self.d in self.trade_dates or i == 0:
                raw_weights = self._coerce_weights(self.allocate())
                raw_weights = self._to_names(raw_weights)

                current_w = self._portfolio_weights_by_name()
                target_weights = self.risk_manager.apply_constraints(raw_weights, current_w)
                target_weights = self._coerce_weights(target_weights)
                target_weights = self._to_names(target_weights)
                self.last_target_weights = target_weights.copy()

                self.on_rebalance_signal(target_weights)

                coded_weights = self._to_codes(target_weights)

                if self.lag == 0:
                    t, c = self.execute_trades(coded_weights)
                    turnover, cost = t, c
                else:
                    self.pending_allocation = coded_weights

            self._record(benchmark.asof(self.d), turnover, cost)

        logger.info("Backtest complete.")
        return self

    def _calculate_benchmark(self) -> pd.Series:
        bm_weights = self.benchmark_weights
        valid_weights = bm_weights[bm_weights.index.intersection(self.pxs.columns)]
        if valid_weights.empty:
            return pd.Series(self.principal, index=self.pxs.index)
        valid_weights = valid_weights / valid_weights.sum()
        bm_ret = self.pxs.pct_change().mul(valid_weights).sum(axis=1)
        return (1 + bm_ret).cumprod() * self.principal

    def _record(self, bm_val: float, turnover: float, cost: float) -> None:
        self.book["date"].append(self.d)
        self.book["portfolio_value"].append(self.portfolio.total_value)
        self.book["cash"].append(self.portfolio.cash)
        self.book["positions"].append({k: v.shares for k, v in self.portfolio.positions.items()})
        self.book["weights"].append({k: v.weight for k, v in self.portfolio.positions.items()})
        target = self.last_target_weights
        self.book["target_weights"].append(target.to_dict() if target is not None else {})
        self.book["benchmark_value"].append(bm_val if pd.notna(bm_val) else self.principal)
        self.book["turnover"].append(turnover)
        self.book["transaction_costs"].append(cost)

    def _generate_trade_dates(self) -> List[pd.Timestamp]:
        if self.pxs.empty:
            return []
        grouper = self.pxs.index.to_series().groupby(pd.Grouper(freq=self.frequency))
        reb_dates = grouper.last().dropna().tolist()
        if self.pxs.index[0] not in reb_dates:
            reb_dates.insert(0, self.pxs.index[0])
        return sorted(set(reb_dates))
