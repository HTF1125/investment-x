"""MacroRegimeStrategy — wraps the walk-forward macro regime engine
into the general-purpose ``Strategy`` base class.

Usage
-----
>>> from ix.core.backtesting import MacroRegimeStrategy
>>> strat = MacroRegimeStrategy(index_name="ACWI").backtest().save()
>>> strat.stats()
>>> strat.plot()

>>> # Load from DB (no recompute)
>>> strat = MacroRegimeStrategy.load(index_name="ACWI")
>>> strat.stats()
"""

from __future__ import annotations

from typing import Any, Dict

import numpy as np
import pandas as pd

from ix.core.backtesting.portfolio import Strategy
from ix.core.macro.wf_backtest import run_full_wf_pipeline
from ix.core.macro.wf_compute import OPTIMIZED_PARAMS
from ix.core.macro.strategy_utils import INDEX_MAP
from ix.misc import get_logger

logger = get_logger(__name__)


class MacroRegimeStrategy(Strategy):
    """Binary macro regime strategy for a single target index.

    Runs the walk-forward pipeline from ``ix.core.macro``, using the
    binary Growth×Inflation regime signal (90/70/30/10 allocation)
    for the primary equity weight.  The ``Strategy`` base class handles
    portfolio simulation, transaction costs, and performance reporting.

    Parameters
    ----------
    index_name : str
        Key into ``INDEX_MAP`` (e.g. ``"ACWI"``, ``"S&P 500"``).
    **pipeline_kwargs
        Overrides for ``OPTIMIZED_PARAMS`` (lookback_years, rebal_weeks, etc.).
    """

    frequency: str = "W-FRI"
    commission: int = 10
    slippage: int = 0
    start: pd.Timestamp = pd.Timestamp("2005-01-01")

    def __init__(self, index_name: str = "ACWI", **pipeline_kwargs):
        if index_name not in INDEX_MAP:
            raise ValueError(
                f"Unknown index: {index_name}. "
                f"Available: {list(INDEX_MAP.keys())}"
            )

        equity_code = INDEX_MAP[index_name]
        self.universe = {
            "Equity": {"code": equity_code, "weight": 0.5},
            "Cash": {"code": "SHY US EQUITY:PX_LAST", "weight": 0.5},
        }

        self._index_name = index_name
        self._pipeline_kwargs = {**OPTIMIZED_PARAMS, **pipeline_kwargs}
        self._pipeline_result: dict | None = None
        self._eq_weights: pd.Series | None = None

        super().__init__()

    # ------------------------------------------------------------------
    # Strategy interface
    # ------------------------------------------------------------------

    def get_params(self) -> Dict[str, Any]:
        """Full parameter dict for fingerprinting."""
        return {"index_name": self._index_name, **self._pipeline_kwargs}

    def initialize(self) -> None:
        """Run walk-forward pipeline and extract equity weight series."""
        logger.info(f"Running macro pipeline for {self._index_name}...")
        result = run_full_wf_pipeline(
            index_name=self._index_name, **self._pipeline_kwargs
        )

        if "error" in result:
            raise RuntimeError(
                f"Pipeline error for {self._index_name}: {result['error']}"
            )

        self._pipeline_result = result

        # Prefer Regime (binary switching) — research shows real alpha
        # comes from drawdown avoidance, not continuous tilts.
        regime = result.get("wf_results", {}).get("Regime")
        if regime is not None and "bt_df" in regime:
            self._eq_weights = regime["bt_df"]["eq_weight"].copy()
        else:
            # Fallback: Blended continuous signal
            blended = result.get("wf_results", {}).get("Blended")
            if blended is not None and "bt_df" in blended:
                self._eq_weights = blended["bt_df"]["eq_weight"].copy()
            else:
                # Last resort: first available category
                wf_histories = result.get("wf_histories", {})
                for cat in ("Growth", "Liquidity", "Tactical", "Inflation"):
                    hist = wf_histories.get(cat, [])
                    if hist:
                        dates = [h["date"] for h in hist]
                        weights = [h["eq_weight"] for h in hist]
                        self._eq_weights = pd.Series(
                            weights, index=pd.DatetimeIndex(dates)
                        )
                        break

        if self._eq_weights is None:
            logger.warning(
                f"No equity weights produced for {self._index_name}; "
                f"defaulting to 50%"
            )
            self._eq_weights = pd.Series(dtype=float)

        logger.info(
            f"Pipeline complete: {len(self._eq_weights)} weight observations"
        )

    def generate_signals(self) -> pd.Series:
        """Return equity/cash allocation for current date."""
        eq_wt = 0.5
        if self._eq_weights is not None and not self._eq_weights.empty:
            val = self._eq_weights.asof(self.d)
            if not pd.isna(val):
                eq_wt = float(val)
        return pd.Series({"Equity": eq_wt, "Cash": 1.0 - eq_wt})

    def allocate(self) -> pd.Series:
        """Signals ARE the allocation — no conversion needed."""
        return self.generate_signals()

    def save(self, **extra) -> "MacroRegimeStrategy":
        """Save with macro-specific signals & meta from the pipeline."""
        if self._pipeline_result:
            from ix.core.macro.wf_compute import serialize_current_signal, serialize_factors

            extra.setdefault(
                "signals", serialize_current_signal(self._pipeline_result)
            )
            extra.setdefault("meta", serialize_factors(self._pipeline_result))
        return super().save(**extra)

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def index_name(self) -> str:
        return self._index_name

    @property
    def pipeline_result(self) -> dict | None:
        """Raw pipeline output (available after backtest, not after load)."""
        return self._pipeline_result
