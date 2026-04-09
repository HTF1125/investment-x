import pandas as pd
from typing import Dict, Optional


class RiskManager:
    """Handles position sizing, risk limits, and constraints."""

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

