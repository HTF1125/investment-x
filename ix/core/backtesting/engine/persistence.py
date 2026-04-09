"""StrategySaver mixin — save/load strategy results to/from DB.

Mixed into ``Strategy`` via multiple inheritance so that
``strat.save()`` and ``Strategy.load()`` work on any strategy instance.
"""

import numpy as np
import pandas as pd
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

from ix.common import get_logger
from .portfolio import Portfolio
from .risk import RiskManager

logger = get_logger(__name__)


class StrategySaver:
    """Mixin providing DB persistence for strategy backtest results.

    Expects the host class to expose:
    - ``self.nav`` — pd.Series of portfolio values
    - ``self.benchmark`` — pd.Series of benchmark values
    - ``self.dates`` — pd.DatetimeIndex
    - ``self.book`` — dict with backtest history
    - ``self.weights_history`` — pd.DataFrame of asset weights
    - ``self.universe`` — dict of universe config
    - ``self.calculate_metrics()`` — from StrategyAnalytics mixin
    - ``self.get_params()`` — parameter dict for fingerprinting
    """

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------

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

        s_dates, s_nav = self._subsample(dates_raw, nav_raw)
        _, s_bm = self._subsample(dates_raw, bm_raw)

        dd = (self.nav / self.nav.cummax()) - 1
        dd_raw = [sf(v) for v in dd.values]
        dd_dates, dd_vals = self._subsample(dates_raw, dd_raw)

        wh = self.weights_history
        wh_dict: Dict[str, Any] = {}
        if not wh.empty:
            wh_dates = [d.strftime("%Y-%m-%d") for d in wh.index]
            wh_sub_dates, _ = self._subsample(wh_dates, wh_dates)
            wh_idx = [wh_dates.index(d) for d in wh_sub_dates]
            wh_dict["dates"] = wh_sub_dates
            for col in wh.columns:
                wh_dict[col] = [sf(wh[col].iloc[i]) for i in wh_idx]

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

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def save(self, **extra) -> "StrategySaver":
        """Persist backtest results to the ``strategy_result`` table.

        Returns ``self`` for chaining: ``strat.backtest().save()``.
        """
        from datetime import datetime, timezone
        from ix.db.conn import Session
        from ix.db.models.strategy_result import StrategyResult, compute_fingerprint

        params = self.get_params()
        fingerprint = compute_fingerprint(self.__class__.__name__, params)
        performance = self._build_performance()
        backtest_blob = self._serialize_backtest()

        with Session() as session:
            existing = session.query(StrategyResult).filter_by(fingerprint=fingerprint).first()
            if existing:
                existing.computed_at = datetime.now(timezone.utc)
                existing.performance = performance
                existing.parameters = params
                existing.backtest = backtest_blob
                existing.signals = extra.get("signals", existing.signals)
                existing.meta = extra.get("meta", existing.meta)
            else:
                session.add(StrategyResult(
                    fingerprint=fingerprint,
                    strategy_type=self.__class__.__name__,
                    computed_at=datetime.now(timezone.utc),
                    performance=performance,
                    parameters=params,
                    backtest=backtest_blob,
                    signals=extra.get("signals"),
                    meta=extra.get("meta"),
                ))

        logger.info(f"Saved {fingerprint}")
        return self

    # ------------------------------------------------------------------
    # Load
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, **params) -> "StrategySaver":
        """Load a previously saved strategy from the DB.

        Returns instance with ``book`` populated so ``.stats()`` and
        ``.plot()`` work immediately.
        """
        from ix.db.conn import Session
        from ix.db.models.strategy_result import StrategyResult, compute_fingerprint

        fingerprint = compute_fingerprint(cls.__name__, params)

        with Session() as session:
            row = session.query(StrategyResult).filter_by(fingerprint=fingerprint).first()

            if row is None and "index_name" in params:
                from sqlalchemy import desc
                row = (
                    session.query(StrategyResult)
                    .filter(
                        StrategyResult.strategy_type == cls.__name__,
                        StrategyResult.parameters["index_name"].astext == params["index_name"],
                    )
                    .order_by(desc(StrategyResult.computed_at))
                    .first()
                )

            if row is None:
                raise KeyError(f"No StrategyResult found for {cls.__name__} with params {params}")

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

            # Restore universe
            if hasattr(cls, "universe") and cls.universe:
                instance.universe = _normalize_universe_static(cls.universe)
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
                    w_df = pd.DataFrame({c: weights_blob[c] for c in w_cols}, index=w_dates)
                    w_df = w_df.reindex(dates_idx, method="ffill").fillna(0.0)
                    instance.book["weights"] = [row_data.to_dict() for _, row_data in w_df.iterrows()]

            # Restore turnover if available
            turnover_blob = bt.get("turnover", {})
            if turnover_blob and "dates" in turnover_blob:
                to_series = pd.Series(turnover_blob["values"], index=pd.to_datetime(turnover_blob["dates"]))
                to_series = to_series.reindex(dates_idx, fill_value=0.0)
                instance.book["turnover"] = list(to_series.values)

            instance.d = dates_idx[-1] if dates_idx.size > 0 else pd.Timestamp.now()
            instance._loaded_performance = row.performance
            instance._loaded_signals = row.signals
            instance._loaded_meta = row.meta
            instance._loaded_params = row.parameters or {}
            instance._fingerprint = row.fingerprint

            logger.info(f"Loaded {row.fingerprint}")
            return instance


def _normalize_universe_static(universe: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Static version of universe normalization for use in load()."""
    out: Dict[str, Dict[str, Any]] = {}
    for name, meta in deepcopy(universe).items():
        if isinstance(meta, dict):
            meta_dict = dict(meta)
        else:
            meta_dict = {"code": meta}
        out[name] = {"code": meta_dict.get("code", name), "weight": meta_dict.get("weight")}
    weights = [v["weight"] for v in out.values()]
    if any(w is None for w in weights) or (sum(w or 0 for w in weights) == 0):
        if out:
            equal = 1.0 / len(out)
            for v in out.values():
                v["weight"] = equal
    return out
