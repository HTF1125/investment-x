"""BatchStrategy adapter — wraps weight-function configs into production Strategy."""

import pandas as pd
from copy import deepcopy
from typing import Any

from ix.db.query import Series as DbSeries, MultiSeries
from ix.core.backtesting.engine import Strategy
from .constants import ASSET_CODES, MACRO_CODES


_ASSET_KEYS = ("assets", "risky", "equities", "bonds", "canary", "offensive", "defensive", "satellite")


def _extract_universe(config: dict) -> dict[str, dict[str, Any]]:
    """Build a Strategy universe dict from a batch config."""
    params = config["params"]
    names: set[str] = set()

    # Collect all asset names from various param keys
    for key in _ASSET_KEYS:
        val = params.get(key)
        if isinstance(val, list):
            names.update(val)

    # Equity/bond defaults
    for key in ("equity", "bond", "cash", "fallback", "asset_a", "asset_b"):
        val = params.get(key)
        if isinstance(val, str) and val in ASSET_CODES:
            names.add(val)

    # Static weights
    if "weights" in params and isinstance(params["weights"], dict):
        names.update(params["weights"].keys())

    # Core dict
    if "core" in params and isinstance(params["core"], dict):
        names.update(params["core"].keys())

    # Sectors in params
    if "sectors" in params and isinstance(params["sectors"], list):
        names.update(params["sectors"])

    # Filter to known assets
    names = {n for n in names if n in ASSET_CODES}

    if not names:
        names = {"SPY", "IEF"}

    universe = {}
    for n in sorted(names):
        universe[n] = {"code": ASSET_CODES[n], "weight": 0.0}

    # Set first equity-like asset as benchmark
    for candidate in ["SPY", "QQQ", "IWM"]:
        if candidate in universe:
            universe[candidate]["weight"] = 1.0
            break
    else:
        first = next(iter(universe))
        universe[first]["weight"] = 1.0

    return universe


class BatchStrategy(Strategy):
    """Adapter: wraps a batch weight-function config into a production Strategy.

    Usage::

        configs = _build_configs(macro_data={"ISM_PMI": "ISM_PMI", ...})
        strat = BatchStrategy(configs[0])
        strat.backtest()
    """

    frequency: str = "ME"
    start = pd.Timestamp("2005-01-01")
    commission = 15
    slippage = 5

    def __init__(self, config: dict, **kwargs):
        self._config = config
        self._wf = config["fn"]
        self._params = deepcopy(config["params"])

        # Set metadata from config
        self.label = config.get("name", config["id"])
        self.family = config.get("family", "")
        self.mode = "batch"
        self.description = config.get("desc", "")
        self.author = "Batch Research Lab"

        # Build universe from config
        self.universe = _extract_universe(config)

        # Benchmark: 50% of primary equity asset
        for candidate in ["SPY", "QQQ", "IWM"]:
            if candidate in self.universe:
                self.bm_assets = {candidate: 0.5}
                break
        else:
            first = next(iter(self.universe))
            self.bm_assets = {first: 0.5}

        super().__init__(**kwargs)

    @property
    def strategy_id(self) -> str:
        return self._config["id"]

    def initialize(self) -> None:
        # Build monthly price DataFrame (same format weight functions expect)
        self._monthly = (
            self.pxs
            .rename(columns=self.code_to_name)
            .resample("ME")
            .last()
            .ffill()
        )
        # Resolve any string macro placeholders to actual DB series
        self._resolve_macro_params()

    def _resolve_macro_params(self) -> None:
        """Replace string macro placeholders with actual DB Series."""
        p = self._params

        # Direct macro_data key
        if isinstance(p.get("macro_data"), str):
            code = MACRO_CODES.get(p["macro_data"])
            if code:
                p["macro_data"] = DbSeries(code)

        # Composite macro indicators: list of (series, threshold, lag, weight)
        if "indicators" in p and isinstance(p["indicators"], list):
            resolved = []
            for item in p["indicators"]:
                if isinstance(item[0], str):
                    code = MACRO_CODES.get(item[0])
                    if code:
                        resolved.append((DbSeries(code), *item[1:]))
                    else:
                        resolved.append(item)
                else:
                    resolved.append(item)
            p["indicators"] = resolved

        # RORO signals with macro sub-params
        if "signals" in p and isinstance(p["signals"], list):
            for _sig_type, sig_p in p["signals"]:
                if isinstance(sig_p.get("data"), str):
                    code = MACRO_CODES.get(sig_p["data"])
                    if code:
                        sig_p["data"] = DbSeries(code)

    def generate_signals(self) -> pd.Series:
        hist = self._monthly.loc[:self.d]
        if len(hist) < 2:
            return pd.Series(0.0, index=self.asset_names)
        try:
            weights = self._wf(hist, self.d, self._params)
        except Exception:
            return pd.Series(0.0, index=self.asset_names)
        return weights.reindex(self.asset_names, fill_value=0.0)

    def allocate(self) -> pd.Series:
        weights = self.generate_signals()
        ws = weights.sum()
        if ws > 1e-10:
            return weights / ws
        return pd.Series(0.0, index=self.asset_names)

    def get_params(self) -> dict:
        return {
            "id": self._config["id"],
            "name": self._config["name"],
            "family": self._config["family"],
            "desc": self._config.get("desc", ""),
            "mode": "batch_production",
        }

    def __repr__(self) -> str:
        return f"BatchStrategy({self._config['id']!r})"


# ════════════════════════════════════════════════════════════════════
# REGISTRY BUILDER
# ════════════════════════════════════════════════════════════════════
