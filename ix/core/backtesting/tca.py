"""Transaction Cost Analysis (TCA) and execution simulation models.

Provides realistic market impact models, a trade-level cost analyzer,
and execution simulators (TWAP/VWAP) for macro/multi-asset backtesting.
"""

import numpy as np
import pandas as pd
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ----------------------------------------------------------------------
# Market Impact Models
# ----------------------------------------------------------------------
class MarketImpactModel(ABC):
    """Base class for market impact models."""

    @abstractmethod
    def estimate_impact(
        self,
        trade_notional: float,
        adv: float,
        volatility: float,
    ) -> float:
        """Estimate price impact as a fraction (e.g. 0.001 = 10 bps).

        Parameters
        ----------
        trade_notional : float
            Absolute dollar value of the trade.
        adv : float
            Average daily volume in dollar terms.
        volatility : float
            Daily return volatility of the asset (e.g. 0.015 = 1.5%).

        Returns
        -------
        float
            Estimated one-way price impact as a decimal fraction.
        """
        pass

    def cost_for_trade(
        self,
        trade_notional: float,
        adv: float,
        volatility: float,
        commission_bps: float = 0.0,
    ) -> Dict[str, float]:
        """Compute full cost breakdown for a single trade."""
        impact = self.estimate_impact(trade_notional, adv, volatility)
        slippage = abs(trade_notional) * impact
        commission = abs(trade_notional) * (commission_bps / 10_000)
        return {
            "impact_pct": impact,
            "slippage": slippage,
            "commission": commission,
            "total_cost": slippage + commission,
        }


class SquareRootImpact(MarketImpactModel):
    """Square-root law market impact: impact = eta * sigma * sqrt(Q / ADV).

    This is the standard institutional model (Almgren et al.) where impact
    scales with the square root of participation rate.
    """

    def __init__(self, eta: float = 0.5) -> None:
        """eta: participation rate coefficient (default 0.5)."""
        if eta <= 0:
            raise ValueError("eta must be positive")
        self.eta = eta

    def estimate_impact(
        self,
        trade_notional: float,
        adv: float,
        volatility: float,
    ) -> float:
        if adv <= 0 or volatility <= 0:
            return 0.0
        participation = abs(trade_notional) / adv
        return self.eta * volatility * np.sqrt(participation)


class LinearImpact(MarketImpactModel):
    """Linear market impact: impact = eta * (Q / ADV).

    Simpler model where impact scales linearly with participation rate.
    Overestimates for small trades, underestimates for large ones.
    """

    def __init__(self, eta: float = 0.1) -> None:
        """eta: linear impact coefficient (default 0.1)."""
        if eta <= 0:
            raise ValueError("eta must be positive")
        self.eta = eta

    def estimate_impact(
        self,
        trade_notional: float,
        adv: float,
        volatility: float,
    ) -> float:
        if adv <= 0:
            return 0.0
        participation = abs(trade_notional) / adv
        return self.eta * participation


class FlatImpact(MarketImpactModel):
    """Flat basis-point slippage model (backward-compatible with existing engine)."""

    def __init__(self, slippage_bps: float = 5.0) -> None:
        self.slippage_bps = slippage_bps

    def estimate_impact(
        self,
        trade_notional: float,
        adv: float,
        volatility: float,
    ) -> float:
        return self.slippage_bps / 10_000


# ----------------------------------------------------------------------
# Transaction Cost Analyzer
# ----------------------------------------------------------------------
@dataclass
class TradeCostRecord:
    """Single trade cost record."""

    date: pd.Timestamp
    asset: str
    trade_notional: float
    turnover: float
    commission: float
    slippage: float
    total_cost: float
    impact_pct: float


class TransactionCostAnalyzer:
    """Analyzes transaction costs across a trade schedule using a given impact model."""

    def __init__(
        self,
        impact_model: MarketImpactModel,
        commission_bps: float = 15.0,
    ) -> None:
        self.impact_model = impact_model
        self.commission_bps = commission_bps
        self._records: List[TradeCostRecord] = []

    def analyze_rebalance(
        self,
        date: pd.Timestamp,
        target_weights: pd.Series,
        current_weights: pd.Series,
        portfolio_value: float,
        prices: pd.Series,
        volume: Optional[pd.Series] = None,
        volatility: Optional[pd.Series] = None,
    ) -> pd.DataFrame:
        """Analyze costs for a single rebalance event.

        Parameters
        ----------
        date : pd.Timestamp
            Trade date.
        target_weights, current_weights : pd.Series
            Asset-indexed weight vectors.
        portfolio_value : float
            Current portfolio NAV.
        prices : pd.Series
            Asset prices on trade date.
        volume : pd.Series, optional
            Dollar volume per asset. If None, assumes infinite liquidity (flat impact).
        volatility : pd.Series, optional
            Daily return volatility per asset. If None, defaults to 1.5%.
        """
        all_assets = target_weights.index.union(current_weights.index)
        tw = target_weights.reindex(all_assets, fill_value=0.0)
        cw = current_weights.reindex(all_assets, fill_value=0.0)

        weight_delta = tw - cw
        records = []

        for asset in all_assets:
            delta_w = weight_delta.get(asset, 0.0)
            if abs(delta_w) < 1e-8:
                continue

            trade_notional = abs(delta_w) * portfolio_value
            turnover = abs(delta_w)

            # Volume: use provided or assume large (effectively flat impact)
            adv = volume.get(asset, 1e12) if volume is not None else 1e12
            # Volatility: use provided or default 1.5% daily
            vol = volatility.get(asset, 0.015) if volatility is not None else 0.015

            costs = self.impact_model.cost_for_trade(
                trade_notional, adv, vol, self.commission_bps
            )

            rec = TradeCostRecord(
                date=date,
                asset=asset,
                trade_notional=trade_notional,
                turnover=turnover,
                commission=costs["commission"],
                slippage=costs["slippage"],
                total_cost=costs["total_cost"],
                impact_pct=costs["impact_pct"],
            )
            records.append(rec)
            self._records.append(rec)

        if not records:
            return pd.DataFrame()

        return pd.DataFrame([r.__dict__ for r in records])

    def total_cost_for_rebalance(
        self,
        target_weights: pd.Series,
        current_weights: pd.Series,
        portfolio_value: float,
        prices: pd.Series,
        volume: Optional[pd.Series] = None,
        volatility: Optional[pd.Series] = None,
    ) -> float:
        """Return total dollar cost for a rebalance (used by the backtesting engine)."""
        all_assets = target_weights.index.union(current_weights.index)
        tw = target_weights.reindex(all_assets, fill_value=0.0)
        cw = current_weights.reindex(all_assets, fill_value=0.0)

        weight_delta = tw - cw
        total = 0.0

        for asset in all_assets:
            delta_w = weight_delta.get(asset, 0.0)
            if abs(delta_w) < 1e-8:
                continue

            trade_notional = abs(delta_w) * portfolio_value
            adv = volume.get(asset, 1e12) if volume is not None else 1e12
            vol = volatility.get(asset, 0.015) if volatility is not None else 0.015

            costs = self.impact_model.cost_for_trade(
                trade_notional, adv, vol, self.commission_bps
            )
            total += costs["total_cost"]

        return total

    def get_trade_log(self) -> pd.DataFrame:
        """Return full trade-level cost log as a DataFrame."""
        if not self._records:
            return pd.DataFrame(
                columns=[
                    "date", "asset", "trade_notional", "turnover",
                    "commission", "slippage", "total_cost", "impact_pct",
                ]
            )
        return pd.DataFrame([r.__dict__ for r in self._records])

    def summary(self, portfolio_value: Optional[float] = None) -> Dict[str, float]:
        """Summary statistics across all recorded trades."""
        if not self._records:
            return {
                "total_cost": 0.0,
                "total_commission": 0.0,
                "total_slippage": 0.0,
                "num_trades": 0,
                "avg_cost_per_trade": 0.0,
                "avg_impact_bps": 0.0,
                "cost_pct_of_portfolio": 0.0,
            }

        total_cost = sum(r.total_cost for r in self._records)
        total_comm = sum(r.commission for r in self._records)
        total_slip = sum(r.slippage for r in self._records)
        n = len(self._records)
        avg_impact = np.mean([r.impact_pct for r in self._records]) * 10_000

        return {
            "total_cost": total_cost,
            "total_commission": total_comm,
            "total_slippage": total_slip,
            "num_trades": n,
            "avg_cost_per_trade": total_cost / n if n > 0 else 0.0,
            "avg_impact_bps": avg_impact,
            "cost_pct_of_portfolio": (
                total_cost / portfolio_value if portfolio_value else 0.0
            ),
        }

    def reset(self) -> None:
        """Clear all recorded trades."""
        self._records.clear()


# ----------------------------------------------------------------------
# Execution Simulators
# ----------------------------------------------------------------------
class ExecutionSimulator:
    """Simulates slicing a parent order into child orders to reduce impact.

    Both TWAP and VWAP spread the trade across N periods; impact is
    computed per-slice using the chosen MarketImpactModel.
    """

    def __init__(
        self,
        impact_model: MarketImpactModel,
        n_slices: int = 5,
    ) -> None:
        """
        Parameters
        ----------
        impact_model : MarketImpactModel
            The impact model applied to each child slice.
        n_slices : int
            Number of time slices to divide the order into (default 5).
        """
        if n_slices < 1:
            raise ValueError("n_slices must be >= 1")
        self.impact_model = impact_model
        self.n_slices = n_slices

    def twap(
        self,
        trade_notional: float,
        adv: float,
        volatility: float,
    ) -> Dict[str, float]:
        """Simulate TWAP execution: equal slices over N periods.

        Returns total impact cost and effective impact percentage.
        """
        slice_size = abs(trade_notional) / self.n_slices
        total_impact_cost = 0.0

        for _ in range(self.n_slices):
            impact_pct = self.impact_model.estimate_impact(slice_size, adv, volatility)
            total_impact_cost += slice_size * impact_pct

        effective_impact = (
            total_impact_cost / abs(trade_notional) if trade_notional != 0 else 0.0
        )

        return {
            "total_impact_cost": total_impact_cost,
            "effective_impact_pct": effective_impact,
            "n_slices": self.n_slices,
            "slice_size": slice_size,
            "strategy": "TWAP",
        }

    def vwap(
        self,
        trade_notional: float,
        adv: float,
        volatility: float,
        volume_profile: Optional[np.ndarray] = None,
    ) -> Dict[str, float]:
        """Simulate VWAP execution: slices weighted by intraday volume profile.

        Parameters
        ----------
        volume_profile : np.ndarray, optional
            Relative volume weights per slice (sums to 1). If None, uses
            a U-shaped profile typical of equity markets.
        """
        if volume_profile is None:
            # U-shaped intraday volume: heavier at open/close
            raw = np.array([
                2.0, 1.2, 0.8, 0.6, 0.5,
                0.5, 0.6, 0.8, 1.2, 2.0,
            ])
            # Resample to n_slices
            indices = np.linspace(0, len(raw) - 1, self.n_slices)
            profile = np.interp(indices, np.arange(len(raw)), raw)
            profile = profile / profile.sum()
        else:
            if len(volume_profile) != self.n_slices:
                raise ValueError(
                    f"volume_profile length ({len(volume_profile)}) "
                    f"must match n_slices ({self.n_slices})"
                )
            profile = volume_profile / volume_profile.sum()

        total_impact_cost = 0.0

        for i in range(self.n_slices):
            slice_size = abs(trade_notional) * profile[i]
            # Volume available in this slice is proportional to profile weight
            slice_adv = adv * profile[i]
            impact_pct = self.impact_model.estimate_impact(
                slice_size, slice_adv, volatility
            )
            total_impact_cost += slice_size * impact_pct

        effective_impact = (
            total_impact_cost / abs(trade_notional) if trade_notional != 0 else 0.0
        )

        return {
            "total_impact_cost": total_impact_cost,
            "effective_impact_pct": effective_impact,
            "n_slices": self.n_slices,
            "volume_profile": profile.tolist(),
            "strategy": "VWAP",
        }

    def compare(
        self,
        trade_notional: float,
        adv: float,
        volatility: float,
    ) -> pd.DataFrame:
        """Compare TWAP vs VWAP vs single-shot execution for a trade."""
        # Single-shot (full order at once)
        single_impact = self.impact_model.estimate_impact(
            trade_notional, adv, volatility
        )
        single_cost = abs(trade_notional) * single_impact

        twap_result = self.twap(trade_notional, adv, volatility)
        vwap_result = self.vwap(trade_notional, adv, volatility)

        rows = [
            {
                "strategy": "Single",
                "total_impact_cost": single_cost,
                "effective_impact_bps": single_impact * 10_000,
                "cost_reduction_pct": 0.0,
            },
            {
                "strategy": "TWAP",
                "total_impact_cost": twap_result["total_impact_cost"],
                "effective_impact_bps": twap_result["effective_impact_pct"] * 10_000,
                "cost_reduction_pct": (
                    1 - twap_result["total_impact_cost"] / single_cost
                    if single_cost > 0
                    else 0.0
                ),
            },
            {
                "strategy": "VWAP",
                "total_impact_cost": vwap_result["total_impact_cost"],
                "effective_impact_bps": vwap_result["effective_impact_pct"] * 10_000,
                "cost_reduction_pct": (
                    1 - vwap_result["total_impact_cost"] / single_cost
                    if single_cost > 0
                    else 0.0
                ),
            },
        ]

        return pd.DataFrame(rows).set_index("strategy")
