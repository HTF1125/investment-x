"""Strategy Library API — browse, inspect, and trigger backtests.

Serves both production strategies (10 hand-built) and batch strategies
(191 parameterized) from the strategy_result DB table.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as SessionType

from ix.api.dependencies import get_current_admin_user, get_db, get_optional_user
from ix.api.rate_limit import limiter as _limiter
from ix.db.models.strategy_result import StrategyResult
from ix.core.backtesting.strategies import (
    STRATEGY_REGISTRY, get_strategy, get_strategy_meta, list_strategies,
)
from ix.common import get_logger

router = APIRouter()
logger = get_logger(__name__)

_backtest_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="strategy-bt")


# ── List all strategies ──────────────────────────────────────────


@router.get("/strategies/")
@_limiter.limit("30/minute")
def list_strategies_endpoint(
    request: Request,
    family: str | None = None,
    _user=Depends(get_optional_user),
    db: SessionType = Depends(get_db),
):
    """List all strategies (production + batch) with performance from DB."""
    # Get ALL strategy results from DB
    query = db.query(StrategyResult)
    rows = query.all()

    # Deduplicate: keep latest per strategy_type (production) or fingerprint (batch)
    # For BatchStrategy, each config has a unique fingerprint via get_params()
    best: dict[str, StrategyResult] = {}
    for row in rows:
        # Use fingerprint as key (unique per strategy config)
        key = row.fingerprint
        # For production strategies, group by strategy_type (one result per class)
        if row.strategy_type != "BatchStrategy":
            key = row.strategy_type
        existing = best.get(key)
        if existing is None or row.computed_at > existing.computed_at:
            best[key] = row

    strategies = []
    for row in sorted(best.values(), key=lambda r: -(r.performance or {}).get("sharpe", 0)):
        perf = row.performance or {}
        params = row.parameters or {}

        # Get metadata from class (production) or params (batch)
        if row.strategy_type in STRATEGY_REGISTRY:
            meta = get_strategy_meta(row.strategy_type)
            name = row.strategy_type
        else:
            # Batch strategy — metadata from stored params
            name = params.get("id", row.fingerprint)
            meta = {
                "label": params.get("name", name),
                "family": params.get("family", ""),
                "mode": "batch",
                "description": params.get("desc", ""),
                "author": "Batch Research Lab",
                "active": True,
            }

        # Apply family filter
        if family and meta.get("family", "").lower() != family.lower():
            continue

        # Skip old MacroRegimeStrategy entries
        if row.strategy_type == "MacroRegimeStrategy":
            continue

        strategies.append({
            "name": name,
            "label": meta.get("label", name),
            "family": meta.get("family", ""),
            "mode": meta.get("mode", ""),
            "description": meta.get("description", ""),
            "author": meta.get("author", ""),
            "active": meta.get("active", True),
            "sharpe": perf.get("sharpe"),
            "cagr": perf.get("cagr"),
            "max_dd": perf.get("max_dd"),
            "vol": perf.get("vol"),
            "sortino": perf.get("sortino"),
            "alpha": perf.get("alpha"),
            "computed_at": row.computed_at.isoformat() if row.computed_at else None,
        })

    return {"strategies": strategies}


# ── Strategy detail (tearsheet) ──────────────────────────────────


def _build_calendar_returns(backtest_blob: dict | None) -> list[dict] | None:
    """Reconstruct monthly calendar returns from stored NAV curve."""
    if not backtest_blob:
        return None
    cum = backtest_blob.get("cumulative", {})
    dates = cum.get("dates", [])
    nav = cum.get("nav", [])
    if not dates or not nav or len(dates) < 24:
        return None

    try:
        nav_series = pd.Series(
            [v for v in nav if v is not None],
            index=pd.to_datetime([d for d, v in zip(dates, nav) if v is not None]),
        )
        daily_ret = nav_series.pct_change().dropna()
        if daily_ret.empty:
            return None

        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        monthly = daily_ret.groupby([daily_ret.index.year, daily_ret.index.month]).apply(
            lambda x: float((1 + x).prod() - 1)
        )

        years = sorted(set(daily_ret.index.year))
        result = []
        for year in years:
            row: dict = {"year": year}
            for m in range(1, 13):
                key = months[m - 1]
                try:
                    row[key] = round(monthly.loc[(year, m)], 4)
                except KeyError:
                    row[key] = None
            year_data = daily_ret[daily_ret.index.year == year]
            if not year_data.empty:
                row["annual"] = round(float((1 + year_data).prod() - 1), 4)
            result.append(row)
        return result
    except Exception:
        return None


@router.get("/strategies/{name}")
@_limiter.limit("15/minute")
def get_strategy_detail(
    request: Request,
    name: str,
    _user=Depends(get_optional_user),
    db: SessionType = Depends(get_db),
):
    """Full tearsheet data for a single strategy."""
    # Try production strategy first (by strategy_type)
    row = (
        db.query(StrategyResult)
        .filter(StrategyResult.strategy_type == name)
        .order_by(StrategyResult.computed_at.desc())
        .first()
    )

    # Try batch strategy (by params->id)
    if row is None:
        from sqlalchemy import cast, String
        rows = (
            db.query(StrategyResult)
            .filter(StrategyResult.strategy_type == "BatchStrategy")
            .all()
        )
        for r in rows:
            params = r.parameters or {}
            if params.get("id") == name:
                row = r
                break

    if row is None:
        raise HTTPException(404, f"No backtest results for {name}.")

    # Build metadata
    params = row.parameters or {}
    if row.strategy_type in STRATEGY_REGISTRY:
        meta = get_strategy_meta(row.strategy_type)
    else:
        meta = {
            "label": params.get("name", name),
            "family": params.get("family", ""),
            "mode": "batch",
            "description": params.get("desc", ""),
            "author": "Batch Research Lab",
        }

    return {
        "name": name,
        "meta": meta,
        "computed_at": row.computed_at.isoformat(),
        "performance": row.performance,
        "backtest": row.backtest,
        "parameters": row.parameters,
        "calendar_returns": _build_calendar_returns(row.backtest),
    }


# ── Trigger backtest ─────────────────────────────────────────────


def _run_backtest(strategy_name: str):
    """Run backtest in background thread."""
    try:
        if strategy_name in STRATEGY_REGISTRY:
            cls = get_strategy(strategy_name)
            instance = cls()
        else:
            # Try batch strategy
            from ix.core.backtesting.batch import build_batch_registry
            batch = build_batch_registry()
            instance = None
            for s in batch:
                if s.strategy_id == strategy_name:
                    instance = s
                    break
            if instance is None:
                logger.error(f"Strategy not found: {strategy_name}")
                return

        instance.backtest().save()
        logger.info(f"Backtest complete for {strategy_name}")
    except Exception as e:
        logger.error(f"Backtest failed for {strategy_name}: {e}")


@router.post("/strategies/{name}/backtest")
@_limiter.limit("5/minute")
def trigger_backtest(
    request: Request,
    name: str,
    _user=Depends(get_current_admin_user),
):
    """Trigger a backtest for a strategy (admin only). Runs in background."""
    _backtest_executor.submit(_run_backtest, name)
    return {"status": "computing", "strategy": name}
