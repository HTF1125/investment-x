import pandas as pd
from dataclasses import dataclass, field
from typing import Dict


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
        """Update all positions based on current prices."""
        invested = sum(
            pos.shares * prices.get(asset, 0) for asset, pos in self.positions.items()
        )
        total_val = self.cash + invested
        for asset, pos in self.positions.items():
            if asset in prices.index:
                pos.update(prices[asset], total_val)
