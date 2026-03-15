import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
from ix.misc import get_logger, as_date
from ix.core.performance.metrics import to_ann_return, to_ann_volatility
from ix.db.query import Series, MultiSeries
from ix.core.backtesting.tca import MarketImpactModel, TransactionCostAnalyzer
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = get_logger(__name__)


# ----------------------------------------------------------------------
# Position & Portfolio
# ----------------------------------------------------------------------
@dataclass
class Position:
    """Represents a position in a single asset."""

    shares: float = 0.0
    value: float = 0.0
    weight: float = 0.0

    def update(self, price: float, total_value: float) -> None:
        """Update position value and weight based on current price."""
        self.value = self.shares * price
        self.weight = self.value / total_value if total_value > 0 else 0.0


@dataclass
class Portfolio:
    """Portfolio state container with helper methods."""

    cash: float = 0.0
    positions: Dict[str, Position] = field(default_factory=dict)

    @property
    def invested_value(self) -> float:
        return sum(pos.value for pos in self.positions.values())

    @property
    def total_value(self) -> float:
        return self.cash + self.invested_value

    @property
    def weights(self) -> pd.Series:
        return pd.Series({k: v.weight for k, v in self.positions.items()})

    @property
    def shares(self) -> pd.Series:
        return pd.Series({k: v.shares for k, v in self.positions.items()})

    def mark_to_market(self, prices: pd.Series) -> None:
        """Update all positions based on current prices.

        The total portfolio value is recomputed from *current* market prices
        (rather than using stale position values) to ensure newly created
        positions receive correct weights immediately after a trade.
        """
        # Calculate invested value using the latest prices
        invested = sum(
            pos.shares * prices.get(asset, 0) for asset, pos in self.positions.items()
        )
        total_val = self.cash + invested

        # Update each position's value and weight
        for asset, pos in self.positions.items():
            if asset in prices.index:
                pos.update(prices[asset], total_val)


# ----------------------------------------------------------------------
# Risk Management
# ----------------------------------------------------------------------
class RiskManager:
    """Handles position sizing, risk limits, and constraints.

    Note: The sector‑limit logic may reduce sector exposure below the
    maximum; the final renormalisation step in ``apply_constraints``
    restores the total weight to 1.0.
    """

    def __init__(
        self,
        max_position: float = 0.30,
        max_sector_exposure: float = 0.50,
        min_position: float = 0.01,
        max_turnover: Optional[float] = None,
    ):
        self.max_position = max_position
        self.max_sector_exposure = max_sector_exposure
        self.min_position = min_position
        self.max_turnover = max_turnover

    def apply_constraints(
        self,
        target_weights: pd.Series,
        current_weights: pd.Series,
        sector_map: Optional[Dict[str, str]] = None,
    ) -> pd.Series:
        """Apply risk constraints to target weights."""
        weights = target_weights.copy()

        # 1. Apply position limits
        weights = weights.clip(upper=self.max_position)

        # 2. Remove small positions
        weights[weights < self.min_position] = 0.0

        # 3. Apply sector exposure limits if sector map provided
        if sector_map:
            weights = self._apply_sector_limits(weights, sector_map)

        # 4. Apply turnover constraint if specified
        if self.max_turnover is not None:
            weights = self._apply_turnover_limit(weights, current_weights)

        # 5. Renormalize to sum to 1.0
        total = weights.sum()
        if total > 0:
            weights = weights / total

        return weights

    def _apply_sector_limits(
        self, weights: pd.Series, sector_map: Dict[str, str]
    ) -> pd.Series:
        """Ensure no sector exceeds maximum exposure."""
        sector_weights = {}
        for asset, weight in weights.items():
            sector = sector_map.get(asset, "Unknown")
            sector_weights[sector] = sector_weights.get(sector, 0.0) + weight

        # Scale down overweight sectors
        adjusted = weights.copy()
        for sector, total_weight in sector_weights.items():
            if total_weight > self.max_sector_exposure:
                scale_factor = self.max_sector_exposure / total_weight
                for asset, sector_name in sector_map.items():
                    if sector_name == sector and asset in adjusted.index:
                        adjusted[asset] *= scale_factor
        return adjusted

    def _apply_turnover_limit(
        self, target_weights: pd.Series, current_weights: pd.Series
    ) -> pd.Series:
        """Limit turnover to maximum allowed."""
        all_assets = target_weights.index.union(current_weights.index)
        target = target_weights.reindex(all_assets, fill_value=0.0)
        current = current_weights.reindex(all_assets, fill_value=0.0)

        turnover = (target - current).abs().sum()

        if turnover > self.max_turnover:
            # Scale adjustment to meet turnover limit
            scale = self.max_turnover / turnover
            adjusted = current + (target - current) * scale
            return adjusted

        return target_weights


# ----------------------------------------------------------------------
# Strategy Base Class
# ----------------------------------------------------------------------
class Strategy(ABC):
    """Enhanced Abstract Base Class for Backtesting Strategies.

    Improvements:
    - Portfolio object for cleaner state management
    - RiskManager integration
    - Slippage modeling
    - Better analytics and attribution
    - Event hooks for extensibility
    """

    # Configuration
    principal: int = 10_000
    universe: Dict[str, Dict[str, Any]] = {
        "SPY": {"code": "SPY US Equity", "weight": 1.00},
    }
    start: pd.Timestamp = pd.Timestamp("2020-01-03")
    end: Optional[pd.Timestamp] = None
    frequency: str = "ME"
    commission: int = 15  # bps (must be non‑negative)
    slippage: int = 5  # bps (must be non‑negative)
    lag: int = (
        0  # Number of periods to delay trade execution (simulates realistic fill latency)
    )
    impact_model: Optional[MarketImpactModel] = None  # Replaces flat slippage when set
    volume: Optional[pd.DataFrame] = None  # Dollar volume per asset (DatetimeIndex x assets)

    def _declared_assets(self) -> Optional[List[str]]:
        """Return assets declared on the subclass (class/instance attribute)."""
        if "assets" in self.__dict__:
            assets = self.__dict__.get("assets")
        else:
            assets = self.__class__.__dict__.get("assets")
        if assets is None or isinstance(assets, property):
            return None
        return list(assets)

    def _build_universe_from_assets(
        self, assets: Iterable[str]
    ) -> Dict[str, Dict[str, Any]]:
        assets = list(assets)
        if not assets:
            return {}
        weight = 1.0 / len(assets)
        return {asset: {"code": asset, "weight": weight} for asset in assets}

    def _normalize_universe(
        self, universe: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        out: Dict[str, Dict[str, Any]] = {}
        for name, meta in universe.items():
            if isinstance(meta, dict):
                meta_dict = dict(meta)
            else:
                meta_dict = {"code": meta}
            out[name] = {
                "code": meta_dict.get("code", name),
                "weight": meta_dict.get("weight"),
            }

        weights = [v["weight"] for v in out.values()]
        if any(w is None for w in weights) or (sum(w or 0 for w in weights) == 0):
            if out:
                equal = 1.0 / len(out)
                for v in out.values():
                    v["weight"] = equal
        return out

    def _initialize_universe(self) -> None:
        """Resolve universe from subclass declarations or defaults."""
        class_universe = self.__class__.__dict__.get("universe")
        if isinstance(class_universe, dict) and class_universe:
            base_universe = class_universe
        else:
            assets = self._declared_assets()
            if assets:
                base_universe = self._build_universe_from_assets(assets)
            else:
                base_universe = getattr(self, "universe", None)

        if not isinstance(base_universe, dict) or not base_universe:
            raise ValueError(
                "Strategy must define a non-empty universe or assets list."
            )

        self.universe = self._normalize_universe(deepcopy(base_universe))
        self._bm_assets = self.__class__.__dict__.get("bm_assets") or getattr(
            self, "bm_assets", None
        )

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

        # Validate configuration values
        if self.principal <= 0:
            raise ValueError("principal must be positive")
        if self.commission < 0:
            raise ValueError("commission cannot be negative")
        if self.slippage < 0:
            raise ValueError("slippage cannot be negative")

        # TCA analyzer (created when impact_model is set)
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
        self.trade_dates = []

    @abstractmethod
    def initialize(self) -> None:
        """Load data and initialize strategy-specific variables."""
        pass

    @abstractmethod
    def generate_signals(self) -> pd.Series:
        """Generate raw signal/score for each asset (can be unbounded)."""
        pass

    def allocate(self) -> pd.Series:
        """Convert signals to portfolio weights.
        Override for custom allocation logic.
        """
        signals = self.generate_signals()

        # Default: long‑only proportional to positive signals
        positive_signals = signals[signals > 0]
        if positive_signals.empty:
            return pd.Series(0.0, index=self.universe.keys())

        weights = positive_signals / positive_signals.sum()
        return weights

    @property
    def assets(self) -> List[str]:
        """Return list of asset names (keys in universe)."""
        return list(self.universe.keys())

    @property
    def asset_names(self) -> List[str]:
        """Return list of asset names (universe keys), regardless of subclass assets attr."""
        return list(self.universe.keys())

    @property
    def asset_codes(self) -> List[str]:
        """Return list of asset codes for data fetching."""
        return [v["code"] for v in self.universe.values()]

    @property
    def benchmark_weights(self) -> pd.Series:
        """Return benchmark weights as Series indexed by asset code."""
        if self._bm_assets:
            bm = self._coerce_weights(self._bm_assets)
            bm = self._weights_to_codes(bm)
            bm = self._drop_unknown_weights(bm, self.asset_codes, context="benchmark")
            total = bm.sum()
            if total > 0:
                bm = bm / total
            return bm

        return pd.Series({v["code"]: v["weight"] for v in self.universe.values()})

    @property
    def name_to_code(self) -> Dict[str, str]:
        """Return mapping from asset names to asset codes."""
        return {name: v["code"] for name, v in self.universe.items()}

    @property
    def code_to_name(self) -> Dict[str, str]:
        """Return mapping from asset codes to asset names."""
        return {v["code"]: name for name, v in self.universe.items()}

    def _coerce_weights(
        self, weights: Optional[Union[pd.Series, Dict[str, float]]]
    ) -> pd.Series:
        if weights is None:
            return pd.Series(dtype=float)
        if isinstance(weights, pd.Series):
            out = weights.copy()
        else:
            out = pd.Series(weights, dtype=float)
        return out.dropna()

    def _weights_to_names(self, weights: pd.Series) -> pd.Series:
        """Convert weights indexed by codes to weights indexed by names (if possible)."""
        if weights.empty:
            return weights
        return weights.rename(self.code_to_name)

    def _weights_to_codes(self, weights: pd.Series) -> pd.Series:
        """Convert weights indexed by asset names to weights indexed by codes."""
        if weights.empty:
            return weights
        return weights.rename(self.name_to_code)

    def _align_weights(self, weights: pd.Series, index: Iterable[str]) -> pd.Series:
        if weights.empty:
            return pd.Series(0.0, index=list(index))
        return weights.reindex(pd.Index(index), fill_value=0.0)

    def _drop_unknown_weights(
        self, weights: pd.Series, valid_index: Iterable[str], context: str
    ) -> pd.Series:
        valid = pd.Index(valid_index)
        unknown = weights.index.difference(valid)
        if not unknown.empty:
            logger.warning(
                f"Ignoring unknown assets in {context} weights: {list(unknown)}"
            )
            weights = weights.drop(index=unknown)
        if weights.index.has_duplicates:
            weights = weights.groupby(level=0).sum()
        return weights

    def _portfolio_weights_by_name(self) -> pd.Series:
        weights = self.portfolio.weights
        weights = self._weights_to_names(weights)
        return self._align_weights(weights, self.asset_names)

    @property
    def current_prices(self) -> pd.Series:
        """Get current price vector."""
        if self.d in self.pxs.index:
            return self.pxs.loc[self.d].dropna()
        return pd.Series(dtype=float)

    def on_trade(self, turnover: float, cost: float) -> None:
        """Hook called after trade execution."""
        pass

    def on_rebalance_signal(self, target_weights: pd.Series) -> None:
        """Hook called when rebalance signal is generated."""
        pass

    def execute_trades(self, target_weights: pd.Series) -> Tuple[float, float]:
        """Execute trades to reach target allocation.
        Returns (turnover, total_cost).
        """
        # Defensive check: target_weights must be indexed by asset codes
        if target_weights.index.has_duplicates:
            target_weights = target_weights.groupby(level=0).sum()
        unknown = target_weights.index.difference(self.asset_codes)
        if not unknown.empty:
            raise ValueError(
                f"target_weights has unknown asset codes: {list(unknown)}"
            )

        prices = self.current_prices
        if prices.empty:
            return 0.0, 0.0

        # Calculate current weights (code‑indexed) on union for full turnover
        all_assets = target_weights.index.union(self.portfolio.weights.index)
        current_weights = self.portfolio.weights.reindex(all_assets, fill_value=0.0)
        target = target_weights.reindex(all_assets, fill_value=0.0)

        # Calculate turnover
        turnover = (current_weights - target).abs().sum()
        if turnover < 1e-6:
            return 0.0, 0.0

        # Calculate costs — use impact model when available, else flat bps
        if self._tca is not None:
            vol_series = self._get_volatility_at_date(self.d)
            vol_data = self._get_volume_at_date(self.d)
            total_cost = self._tca.total_cost_for_rebalance(
                target_weights=target,
                current_weights=current_weights,
                portfolio_value=self.portfolio.total_value,
                prices=prices,
                volume=vol_data,
                volatility=vol_series,
            )
        else:
            commission_cost = (
                self.portfolio.total_value * turnover * (self.commission / 10_000)
            )
            slippage_cost = (
                self.portfolio.total_value * turnover * (self.slippage / 10_000)
            )
            total_cost = commission_cost + slippage_cost

        # Deduct costs from portfolio
        net_value = self.portfolio.total_value - total_cost

        # Filter to assets with valid price data
        valid_assets = prices.index.intersection(target_weights.index)
        if valid_assets.empty:
            # No tradable assets – go fully cash
            self.portfolio.positions = {}
            self.portfolio.cash = net_value
            return turnover, total_cost

        # Recalculate weights for valid assets only and renormalise
        valid_weights = target_weights.reindex(valid_assets, fill_value=0.0)
        weight_sum = valid_weights.sum()
        if weight_sum < 1e-10:
            # Effectively zero – treat as cash position
            self.portfolio.positions = {}
            self.portfolio.cash = net_value
            return turnover, total_cost
        if weight_sum > 0:
            valid_weights = valid_weights / weight_sum

        # Compute target dollar values and new shares
        target_values = valid_weights * net_value
        new_shares = target_values / prices.reindex(valid_assets)

        # Update portfolio positions
        self.portfolio.positions = {
            asset: Position(shares=shares)
            for asset, shares in new_shares.items()
            if not pd.isna(shares) and shares > 0
        }

        # Update cash based on actual invested value
        invested_value = sum(
            pos.shares * prices.get(asset, 0)
            for asset, pos in self.portfolio.positions.items()
        )
        self.portfolio.cash = net_value - invested_value
        self.portfolio.mark_to_market(prices)

        if self.verbose:
            logger.info(
                f"{as_date(self.d)}: Traded. Turnover: {turnover:.2%}, "
                f"Cost: ${total_cost:.2f}"
            )

        self.on_trade(turnover, total_cost)
        return turnover, total_cost

    def _get_volatility_at_date(self, date: pd.Timestamp) -> Optional[pd.Series]:
        """Compute trailing 20-day realized volatility for each asset."""
        if self.pxs.empty:
            return None
        loc = self.pxs.index.get_loc(date)
        if isinstance(loc, slice):
            loc = loc.stop - 1
        start = max(0, loc - 20)
        window = self.pxs.iloc[start : loc + 1]
        if len(window) < 2:
            return None
        return window.pct_change().std()

    def _get_volume_at_date(self, date: pd.Timestamp) -> Optional[pd.Series]:
        """Get volume data for the current date (20-day average dollar volume)."""
        if self.volume is None or self.volume.empty:
            return None
        loc = self.volume.index.get_indexer([date], method="ffill")[0]
        if loc < 0:
            return None
        start = max(0, loc - 20)
        window = self.volume.iloc[start : loc + 1]
        if window.empty:
            return None
        return window.mean()

    @property
    def tca(self) -> Optional[TransactionCostAnalyzer]:
        """Access the transaction cost analyzer (None if no impact model set)."""
        return self._tca

    def mark_to_market(self) -> None:
        """Update portfolio values based on current prices."""
        prices = self.current_prices
        if not prices.empty:
            self.portfolio.mark_to_market(prices)

    def backtest(self) -> "Strategy":
        """Run the backtest simulation."""
        logger.info(f"Fetching data for {len(self.universe)} assets...")

        # 1. Fetch price data using asset codes
        series_map = {v["code"]: Series(v["code"]) for v in self.universe.values()}
        self.pxs = MultiSeries(**series_map).sort_index()

        if self.start:
            self.pxs = self.pxs.loc[self.start :]

        if self.end:
            self.pxs = self.pxs.loc[: self.end]

        if self.pxs.empty:
            logger.error("No price data found.")
            return self

        # 2. Initialise strategy
        self.trade_dates = self._generate_trade_dates()
        self.initialize()

        # 3. Setup benchmark
        benchmark = self._calculate_benchmark()

        # 4. Main simulation loop
        for i, self.d in enumerate(self.pxs.index):
            # A. Mark to market
            self.mark_to_market()

            # B. Execute pending orders (if lag > 0)
            if self.pending_allocation is not None:
                turnover, cost = self.execute_trades(self.pending_allocation)
                self.pending_allocation = None
            else:
                turnover, cost = 0.0, 0.0

            # C. Generate new signals on rebalance dates
            if self.d in self.trade_dates or i == 0:
                raw_weights = self._coerce_weights(self.allocate())
                raw_weights = self._weights_to_names(raw_weights)
                raw_weights = self._drop_unknown_weights(
                    raw_weights, self.asset_names, context="allocation"
                )
                raw_weights = self._align_weights(raw_weights, self.asset_names)

                # Apply risk management constraints
                current_w = self._portfolio_weights_by_name()
                target_weights = self.risk_manager.apply_constraints(
                    raw_weights, current_w
                )
                target_weights = self._coerce_weights(target_weights)
                target_weights = self._weights_to_names(target_weights)
                target_weights = self._align_weights(target_weights, self.asset_names)
                self.last_target_weights = target_weights.copy()

                self.on_rebalance_signal(target_weights)

                # Convert weights from names to codes for execute_trades
                coded_weights = self._weights_to_codes(target_weights)
                coded_weights = self._drop_unknown_weights(
                    coded_weights, self.asset_codes, context="allocation"
                )

                if self.lag == 0:
                    t, c = self.execute_trades(coded_weights)
                    turnover, cost = t, c
                else:
                    self.pending_allocation = coded_weights

            # D. Record state
            self._record(benchmark.asof(self.d), turnover, cost)

        logger.info("Backtest complete.")
        return self

    def _calculate_benchmark(self) -> pd.Series:
        """Calculate benchmark returns."""
        bm_weights = self.benchmark_weights
        valid_weights = bm_weights[bm_weights.index.intersection(self.pxs.columns)]
        if valid_weights.empty:
            return pd.Series(self.principal, index=self.pxs.index)

        valid_weights = valid_weights / valid_weights.sum()
        bm_ret = self.pxs.pct_change().mul(valid_weights).sum(axis=1)
        return (1 + bm_ret).cumprod() * self.principal

    def _record(self, bm_val: float, turnover: float, cost: float) -> None:
        """Record current state to history."""
        self.book["date"].append(self.d)
        self.book["portfolio_value"].append(self.portfolio.total_value)
        self.book["cash"].append(self.portfolio.cash)
        self.book["positions"].append(
            {k: v.shares for k, v in self.portfolio.positions.items()}
        )
        self.book["weights"].append(
            {k: v.weight for k, v in self.portfolio.positions.items()}
        )

        target = self.last_target_weights
        self.book["target_weights"].append(
            target.to_dict() if target is not None else {}
        )
        self.book["benchmark_value"].append(
            bm_val if pd.notna(bm_val) else self.principal
        )
        self.book["turnover"].append(turnover)
        self.book["transaction_costs"].append(cost)

    def _generate_trade_dates(self) -> List[pd.Timestamp]:
        """Generate rebalancing dates based on frequency."""
        if self.pxs.empty:
            return []

        grouper = self.pxs.index.to_series().groupby(pd.Grouper(freq=self.frequency))
        reb_dates = grouper.last().dropna().tolist()

        if self.pxs.index[0] not in reb_dates:
            reb_dates.insert(0, self.pxs.index[0])

        return sorted(list(set(reb_dates)))

    # --- Analytics ---

    @property
    def dates(self) -> pd.DatetimeIndex:
        return pd.DatetimeIndex(self.book["date"])

    @property
    def nav(self) -> pd.Series:
        return pd.Series(
            data=self.book["portfolio_value"], index=self.dates, name="Strategy"
        )

    @property
    def benchmark(self) -> pd.Series:
        return pd.Series(
            data=self.book["benchmark_value"], index=self.dates, name="Benchmark"
        )

    @property
    def weights_history(self) -> pd.DataFrame:
        df = pd.DataFrame(self.book["weights"], index=self.dates).fillna(0.0)
        return df.rename(columns=self.code_to_name)

    def calculate_metrics(self, series: pd.Series) -> Dict[str, float]:
        """Calculate performance metrics for a return series."""
        if series.empty or len(series) < 2:
            return {
                "Total Return": 0.0,
                "CAGR": 0.0,
                "Volatility": 0.0,
                "Sharpe": 0.0,
                "Sortino": 0.0,
                "Max Drawdown": 0.0,
                "Win Rate": 0.0,
                "Avg Daily Return": 0.0,
            }
        daily_ret = series.pct_change().dropna()

        # Returns
        total_return = (series.iloc[-1] / series.iloc[0]) - 1
        ann_ret = to_ann_return(series)
        ann_vol = to_ann_volatility(series)

        # Risk metrics
        sharpe = (ann_ret / ann_vol) if ann_vol != 0 else 0
        sortino = self._calculate_sortino(daily_ret)

        # Drawdown
        roll_max = series.cummax()
        drawdown = (series - roll_max) / roll_max
        max_dd = drawdown.min()

        # Win rate
        win_rate = (daily_ret > 0).sum() / len(daily_ret) if len(daily_ret) > 0 else 0

        return {
            "Total Return": total_return,
            "CAGR": ann_ret,
            "Volatility": ann_vol,
            "Sharpe": sharpe,
            "Sortino": sortino,
            "Max Drawdown": max_dd,
            "Win Rate": win_rate,
            "Avg Daily Return": daily_ret.mean(),
        }

    def _calculate_sortino(self, returns: pd.Series, mar: float = 0.0) -> float:
        """Calculate Sortino ratio."""
        excess = returns - mar / 252  # Daily MAR
        downside = excess[excess < 0].std()
        if downside == 0 or pd.isna(downside):
            return 0.0
        return (excess.mean() * 252) / (downside * np.sqrt(252))

    def stats(self) -> pd.DataFrame:
        """Generate performance statistics table.

        If the strategy was loaded from DB (via ``load()``), uses the
        stored ``_loaded_performance`` for accurate metrics rather than
        recomputing from subsampled curves.
        """
        perf = getattr(self, "_loaded_performance", None)
        if perf is not None:
            # Use stored ground-truth metrics
            bm = perf.get("benchmark", {})
            formatted = {
                "Strategy": {
                    "Total Return": f"{perf.get('total_return', 0):.2%}",
                    "CAGR": f"{perf.get('cagr', 0):.2%}",
                    "Volatility": f"{perf.get('vol', 0):.2%}",
                    "Sharpe": f"{perf.get('sharpe', 0):.2f}",
                    "Sortino": f"{perf.get('sortino', 0):.2f}",
                    "Max DD": f"{perf.get('max_dd', 0):.2%}",
                    "Win Rate": f"{perf.get('win_rate', 0):.2%}",
                    "Alpha": f"{perf.get('alpha', 0):.2%}",
                    "IR": f"{perf.get('ir', 0):.2f}",
                },
                "Benchmark": {
                    "Total Return": f"{bm.get('total_return', 0):.2%}",
                    "CAGR": f"{bm.get('cagr', 0):.2%}",
                    "Volatility": f"{bm.get('vol', 0):.2%}",
                    "Sharpe": f"{bm.get('sharpe', 0):.2f}",
                    "Sortino": f"{bm.get('sortino', 0):.2f}",
                    "Max DD": f"{bm.get('max_dd', 0):.2%}",
                },
            }
            return pd.DataFrame(formatted)

        strategy_metrics = self.calculate_metrics(self.nav)
        benchmark_metrics = self.calculate_metrics(self.benchmark)

        # Format for display
        formatted = {}
        for name, metrics in {
            "Strategy": strategy_metrics,
            "Benchmark": benchmark_metrics,
        }.items():
            formatted[name] = {
                "Total Return": f"{metrics['Total Return']:.2%}",
                "CAGR": f"{metrics['CAGR']:.2%}",
                "Volatility": f"{metrics['Volatility']:.2%}",
                "Sharpe": f"{metrics['Sharpe']:.2f}",
                "Sortino": f"{metrics['Sortino']:.2f}",
                "Max DD": f"{metrics['Max Drawdown']:.2%}",
                "Win Rate": f"{metrics['Win Rate']:.2%}",
            }

        # Add strategy‑specific metrics
        total_costs = sum(self.book["transaction_costs"])
        turnovers = [t for t in self.book["turnover"] if t > 0]
        avg_turnover = float(np.mean(turnovers)) if turnovers else 0.0
        formatted["Strategy"]["Avg Turnover"] = f"{avg_turnover:.2%}"
        formatted["Strategy"]["Total Costs"] = f"${total_costs:,.0f}"

        return pd.DataFrame(formatted)

    def plot(self):
        """Generate comprehensive tearsheet."""
        fig = make_subplots(
            rows=4,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.06,
            row_heights=[0.40, 0.20, 0.25, 0.15],
            subplot_titles=(
                "Cumulative Performance",
                "Drawdown",
                "Asset Allocation",
                "Rolling Sharpe (6M)",
            ),
        )

        # 1. NAV - Strategy and Benchmark only in main chart
        fig.add_trace(
            go.Scatter(
                x=self.dates,
                y=self.nav,
                name="Strategy",
                line=dict(color="#2E86AB", width=2.5),
                legendgroup="main",
            ),
            row=1,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=self.dates,
                y=self.benchmark,
                name="Benchmark",
                line=dict(color="#A23B72", dash="dot", width=2),
                legendgroup="main",
            ),
            row=1,
            col=1,
        )

        # 2. Drawdown
        dd = (self.nav / self.nav.cummax()) - 1
        dd_bm = (self.benchmark / self.benchmark.cummax()) - 1

        fig.add_trace(
            go.Scatter(
                x=self.dates,
                y=dd,
                name="Strategy DD",
                fill="tozeroy",
                line=dict(color="#C73E1D", width=0),
                fillcolor="rgba(199, 62, 29, 0.5)",
                legendgroup="dd",
                showlegend=True,
            ),
            row=2,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=self.dates,
                y=dd_bm,
                name="Benchmark DD",
                line=dict(color="#A23B72", width=1, dash="dot"),
                legendgroup="dd",
                showlegend=True,
            ),
            row=2,
            col=1,
        )

        # 3. Allocations - Clean up the stacked area chart
        weights_df = self.weights_history
        if not weights_df.empty:
            # Use a better color palette
            colors = [
                "#1f77b4",
                "#ff7f0e",
                "#2ca02c",
                "#d62728",
                "#9467bd",
                "#8c564b",
                "#e377c2",
                "#7f7f7f",
                "#bcbd22",
                "#17becf",
            ]

            # Mapping for cleaner sector names
            sector_names = {
                "XLK US EQUITY:PX_LAST": "Tech",
                "XLI US EQUITY:PX_LAST": "Industrials",
                "XLF US EQUITY:PX_LAST": "Financials",
                "XLC US EQUITY:PX_LAST": "Communications",
                "XLE US EQUITY:PX_LAST": "Energy",
                "XLY US EQUITY:PX_LAST": "Discretionary",
                "XLB US EQUITY:PX_LAST": "Materials",
                "XLV US EQUITY:PX_LAST": "Healthcare",
                "XLP US EQUITY:PX_LAST": "Staples",
                "XLU US EQUITY:PX_LAST": "Utilities",
            }

            # Sort columns by average weight for better visualization
            avg_weights = weights_df.mean().sort_values(ascending=False)
            sorted_cols = avg_weights.index.tolist()

            for i, col in enumerate(sorted_cols):
                # Get clean sector name
                display_name = sector_names.get(col, col)
                fig.add_trace(
                    go.Scatter(
                        x=weights_df.index,
                        y=weights_df[col],
                        name=display_name,
                        stackgroup="allocation",
                        mode="none",
                        fillcolor=colors[i % len(colors)],
                        legendgroup="allocation",
                        showlegend=True,
                    ),
                    row=3,
                    col=1,
                )

        # 4. Rolling Sharpe
        returns = self.nav.pct_change()
        rolling_sharpe = (
            returns.rolling(126).mean() / returns.rolling(126).std()
        ) * np.sqrt(252)

        fig.add_trace(
            go.Scatter(
                x=self.dates,
                y=rolling_sharpe,
                name="Rolling Sharpe",
                line=dict(color="#18A558", width=2),
                legendgroup="sharpe",
                showlegend=False,
            ),
            row=4,
            col=1,
        )
        fig.add_hline(
            y=0, line_dash="dash", line_color="gray", row=4, col=1, line_width=1
        )
        fig.add_hline(
            y=1, line_dash="dash", line_color="lightgray", row=4, col=1, line_width=0.5
        )

        # Layout improvements
        fig.update_layout(
            height=1200,
            title_text=f"{self.__class__.__name__} Performance Tearsheet",
            hovermode="x unified",
            template="plotly_white",
            legend=dict(groupclick="toggleitem", tracegroupgap=180),
        )

        fig.update_yaxes(title_text="Portfolio Value ($)", row=1, col=1)
        fig.update_yaxes(title_text="Drawdown", tickformat=".0%", row=2, col=1)
        fig.update_yaxes(
            title_text="Weight", tickformat=".0%", row=3, col=1, range=[0, 1]
        )
        fig.update_yaxes(title_text="Sharpe Ratio", row=4, col=1)
        fig.update_xaxes(title_text="Date", row=4, col=1)

        return fig

    # ------------------------------------------------------------------
    # Persistence: save() / load() via StrategyResult
    # ------------------------------------------------------------------

    def get_params(self) -> Dict[str, Any]:
        """Return parameter dict for fingerprinting.

        Subclasses should override to declare all configurable parameters.
        The dict must be JSON-serializable.
        """
        return {}

    @staticmethod
    def _subsample(
        dates: List[str], values: List, max_pts: int = 800
    ) -> Tuple[List[str], List]:
        """Thin time series to at most *max_pts* points, keeping first/last."""
        n = len(dates)
        if n <= max_pts:
            return dates, values
        step = max(1, n // max_pts)
        idx = list(range(0, n, step))
        if idx[-1] != n - 1:
            idx.append(n - 1)
        return [dates[i] for i in idx], [values[i] for i in idx]

    @staticmethod
    def _safe_float(v) -> Optional[float]:
        """Convert to float, returning None for NaN/Inf."""
        if v is None:
            return None
        try:
            f = float(v)
            return None if (pd.isna(f) or np.isinf(f)) else round(f, 6)
        except (TypeError, ValueError):
            return None

    def _serialize_backtest(self) -> Dict[str, Any]:
        """Serialize NAV, benchmark, and weights into a JSON-safe dict."""
        sf = self._safe_float
        dates_raw = [d.strftime("%Y-%m-%d") for d in self.dates]
        nav_raw = [sf(v) for v in self.nav.values]
        bm_raw = [sf(v) for v in self.benchmark.values]

        # Subsample curves
        s_dates, s_nav = self._subsample(dates_raw, nav_raw)
        _, s_bm = self._subsample(dates_raw, bm_raw)

        # Drawdown
        dd = (self.nav / self.nav.cummax()) - 1
        dd_raw = [sf(v) for v in dd.values]
        dd_dates, dd_vals = self._subsample(dates_raw, dd_raw)

        # Weights history (subsample)
        wh = self.weights_history
        wh_dict: Dict[str, Any] = {}
        if not wh.empty:
            wh_dates = [d.strftime("%Y-%m-%d") for d in wh.index]
            wh_sub_dates, _ = self._subsample(wh_dates, wh_dates)
            wh_idx = [wh_dates.index(d) for d in wh_sub_dates]
            wh_dict["dates"] = wh_sub_dates
            for col in wh.columns:
                vals = [sf(wh[col].iloc[i]) for i in wh_idx]
                wh_dict[col] = vals

        # Turnover
        turnovers = self.book.get("turnover", [])
        to_raw = [sf(v) for v in turnovers]
        to_dates, to_vals = self._subsample(dates_raw, to_raw)

        return {
            "cumulative": {"dates": s_dates, "nav": s_nav, "benchmark": s_bm},
            "drawdown": {"dates": dd_dates, "values": dd_vals},
            "weights": wh_dict,
            "turnover": {"dates": to_dates, "values": to_vals},
        }

    def _build_performance(self) -> Dict[str, Any]:
        """Build standardized performance dict from backtest results."""
        sf = self._safe_float
        strat_m = self.calculate_metrics(self.nav)
        bench_m = self.calculate_metrics(self.benchmark)

        # Alpha & tracking error
        strat_ret = self.nav.pct_change().dropna()
        bench_ret = self.benchmark.pct_change().dropna()
        excess = strat_ret - bench_ret
        te = float(excess.std() * np.sqrt(252)) if len(excess) > 1 else 0.0
        ir = float(excess.mean() * 252 / te) if te > 1e-8 else 0.0

        return {
            "total_return": sf(strat_m["Total Return"]),
            "cagr": sf(strat_m["CAGR"]),
            "vol": sf(strat_m["Volatility"]),
            "sharpe": sf(strat_m["Sharpe"]),
            "sortino": sf(strat_m["Sortino"]),
            "max_dd": sf(strat_m["Max Drawdown"]),
            "win_rate": sf(strat_m["Win Rate"]),
            "alpha": sf(strat_m["CAGR"] - bench_m["CAGR"]),
            "ir": sf(ir),
            "te": sf(te),
            "period_start": self.dates[0].strftime("%Y-%m") if len(self.dates) > 0 else None,
            "period_end": self.dates[-1].strftime("%Y-%m") if len(self.dates) > 0 else None,
            "benchmark": {
                "total_return": sf(bench_m["Total Return"]),
                "cagr": sf(bench_m["CAGR"]),
                "vol": sf(bench_m["Volatility"]),
                "sharpe": sf(bench_m["Sharpe"]),
                "sortino": sf(bench_m["Sortino"]),
                "max_dd": sf(bench_m["Max Drawdown"]),
            },
        }

    def save(self, **extra) -> "Strategy":
        """Persist backtest results to the ``strategy_result`` table.

        Parameters
        ----------
        **extra
            Optional overrides for ``signals`` and ``meta`` JSONB columns.
            Subclasses can pass strategy-specific data here.

        Returns
        -------
        Strategy
            ``self``, for chaining: ``strat.backtest().save()``.
        """
        from datetime import datetime, timezone

        from ix.db.conn import Session
        from ix.db.models.strategy_result import StrategyResult, compute_fingerprint

        params = self.get_params()
        fingerprint = compute_fingerprint(self.__class__.__name__, params)
        performance = self._build_performance()
        backtest_blob = self._serialize_backtest()

        with Session() as session:
            existing = (
                session.query(StrategyResult)
                .filter_by(fingerprint=fingerprint)
                .first()
            )
            if existing:
                existing.computed_at = datetime.now(timezone.utc)
                existing.performance = performance
                existing.parameters = params
                existing.backtest = backtest_blob
                existing.signals = extra.get("signals", existing.signals)
                existing.meta = extra.get("meta", existing.meta)
            else:
                session.add(
                    StrategyResult(
                        fingerprint=fingerprint,
                        strategy_type=self.__class__.__name__,
                        computed_at=datetime.now(timezone.utc),
                        performance=performance,
                        parameters=params,
                        backtest=backtest_blob,
                        signals=extra.get("signals"),
                        meta=extra.get("meta"),
                    )
                )

        logger.info(f"Saved {fingerprint}")
        return self

    @classmethod
    def load(cls, **params) -> "Strategy":
        """Load a previously saved strategy from the DB.

        Parameters
        ----------
        **params
            Keyword arguments that match the parameter dict used when
            saving.  If an exact fingerprint match is not found, falls
            back to the latest result for this strategy type whose
            ``parameters->>'index_name'`` matches (if provided).

        Returns
        -------
        Strategy
            Instance with ``book`` populated from stored data so that
            ``.stats()`` and ``.plot()`` work immediately.

        Raises
        ------
        KeyError
            If no matching result is found in the DB.
        """
        from ix.db.conn import Session
        from ix.db.models.strategy_result import StrategyResult, compute_fingerprint

        fingerprint = compute_fingerprint(cls.__name__, params)

        with Session() as session:
            row = (
                session.query(StrategyResult)
                .filter_by(fingerprint=fingerprint)
                .first()
            )

            # Fallback: match by strategy_type + index_name (latest)
            if row is None and "index_name" in params:
                from sqlalchemy import desc, text

                row = (
                    session.query(StrategyResult)
                    .filter(
                        StrategyResult.strategy_type == cls.__name__,
                        StrategyResult.parameters["index_name"].astext
                        == params["index_name"],
                    )
                    .order_by(desc(StrategyResult.computed_at))
                    .first()
                )

            if row is None:
                raise KeyError(
                    f"No StrategyResult found for {cls.__name__} "
                    f"with params {params}"
                )

            # Reconstruct strategy instance
            instance = cls.__new__(cls)

            # Minimal init — set essential attributes without full __init__
            instance.verbose = False
            instance.risk_manager = RiskManager()
            instance.impact_model = None
            instance._tca = None
            instance.portfolio = Portfolio()
            instance.pending_allocation = None
            instance.last_target_weights = pd.Series(dtype=float)
            instance.pxs = pd.DataFrame()
            instance.trade_dates = []

            # Restore universe from stored params or class default
            stored_params = row.parameters or {}
            if hasattr(cls, "universe") and cls.universe:
                instance.universe = cls._normalize_universe_static(cls.universe)
            else:
                instance.universe = {"default": {"code": "default", "weight": 1.0}}
            instance._bm_assets = None

            # Restore book from stored backtest blob
            bt = row.backtest or {}
            cumulative = bt.get("cumulative", {})
            dates_str = cumulative.get("dates", [])
            nav_vals = cumulative.get("nav", [])
            bm_vals = cumulative.get("benchmark", [])

            dates_idx = pd.to_datetime(dates_str) if dates_str else pd.DatetimeIndex([])

            instance.book = {
                "date": list(dates_idx),
                "portfolio_value": [v if v is not None else 0.0 for v in nav_vals],
                "cash": [0.0] * len(dates_idx),
                "positions": [{}] * len(dates_idx),
                "weights": [{}] * len(dates_idx),
                "target_weights": [{}] * len(dates_idx),
                "benchmark_value": [v if v is not None else 0.0 for v in bm_vals],
                "turnover": [0.0] * len(dates_idx),
                "transaction_costs": [0.0] * len(dates_idx),
            }

            # Restore weights if available
            weights_blob = bt.get("weights", {})
            if weights_blob and "dates" in weights_blob:
                w_dates = pd.to_datetime(weights_blob["dates"])
                w_cols = [k for k in weights_blob if k != "dates"]
                if w_cols:
                    # Build weights dicts for each date in the main dates list
                    w_df = pd.DataFrame(
                        {c: weights_blob[c] for c in w_cols}, index=w_dates
                    )
                    # Reindex to match the main dates
                    w_df = w_df.reindex(dates_idx, method="ffill").fillna(0.0)
                    instance.book["weights"] = [
                        row_data.to_dict() for _, row_data in w_df.iterrows()
                    ]

            # Restore turnover if available
            turnover_blob = bt.get("turnover", {})
            if turnover_blob and "dates" in turnover_blob:
                to_series = pd.Series(
                    turnover_blob["values"],
                    index=pd.to_datetime(turnover_blob["dates"]),
                )
                to_series = to_series.reindex(dates_idx, fill_value=0.0)
                instance.book["turnover"] = list(to_series.values)

            if dates_idx.size > 0:
                instance.d = dates_idx[-1]
            else:
                instance.d = pd.Timestamp.now()

            # Store loaded metadata for access
            instance._loaded_performance = row.performance
            instance._loaded_signals = row.signals
            instance._loaded_meta = row.meta
            instance._loaded_params = stored_params
            instance._fingerprint = row.fingerprint

            logger.info(f"Loaded {row.fingerprint}")
            return instance

    @staticmethod
    def _normalize_universe_static(
        universe: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Static version of _normalize_universe for use in load()."""
        from copy import deepcopy

        out: Dict[str, Dict[str, Any]] = {}
        for name, meta in deepcopy(universe).items():
            if isinstance(meta, dict):
                meta_dict = dict(meta)
            else:
                meta_dict = {"code": meta}
            out[name] = {
                "code": meta_dict.get("code", name),
                "weight": meta_dict.get("weight"),
            }
        weights = [v["weight"] for v in out.values()]
        if any(w is None for w in weights) or (sum(w or 0 for w in weights) == 0):
            if out:
                equal = 1.0 / len(out)
                for v in out.values():
                    v["weight"] = equal
        return out


