"""Static allocation strategies — fixed weights, no signals."""

import pandas as pd
from ._base import FamilyStrategy
from ix.core.backtesting.batch.constants import ASSET_CODES


class StaticAllocation(FamilyStrategy):
    """Fixed-weight allocation. No rebalancing signals — just hold static weights."""
    family = "Static"

    def __init__(self, weights: dict[str, float], name: str = "", **kw):
        self._weights = weights
        all_assets = list(weights.keys())
        self._build_universe(all_assets, benchmark={"SPY": 0.6, "AGG": 0.4})
        self.label = name or "Static " + "/".join(f"{int(v*100)}% {k}" for k, v in weights.items())
        weight_str = ", ".join(f"{v:.0%} {k}" for k, v in weights.items())
        self.description = (
            f"Fixed-weight buy-and-hold: allocates {weight_str}. "
            f"No tactical signals — weights are static targets. "
            f"Rebalanced monthly back to target weights when drift occurs. "
            f"Benchmark: 60/40 SPY/AGG."
        )
        super().__init__(**kw)

    def generate_signals(self):
        return pd.Series(self._weights).reindex(self.asset_names, fill_value=0.0)

    def get_params(self):
        return {"weights": self._weights}
