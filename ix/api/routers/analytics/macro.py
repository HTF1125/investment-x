"""Macro outlook API -- serves precomputed regime/allocation data.

Endpoints read from the macro_outlook DB table (populated by the scheduler).
The POST /macro/refresh endpoint triggers a background recompute for admins.
"""  # noqa: E501

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends, HTTPException, Request

from sqlalchemy.orm import Session as SessionType

from ix.api.dependencies import get_current_admin_user, get_db, get_optional_user
from ix.api.rate_limit import limiter as _limiter

from ix.db.models.macro_outlook import MacroOutlook
from ix.db.models.macro_regime_strategy import MacroRegimeStrategy
from ix.core.macro.config import TARGET_INDICES
from ix.common import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Bounded executor for background refresh tasks (prevent unbounded thread spawning)
_refresh_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="macro-refresh")


@router.get("/macro/targets")
@_limiter.limit("60/minute")
def list_targets(request: Request, _user=Depends(get_optional_user)):
    """List all available target indices for macro outlook."""
    targets = []
    for name, idx in TARGET_INDICES.items():
        targets.append(
            {
                "name": name,
                "ticker": idx.ticker,
                "region": idx.region,
                "currency": idx.currency,
                "has_sectors": idx.has_sectors,
            }
        )
    return {"targets": targets}


@router.get("/macro/outlook")
@_limiter.limit("30/minute")
def get_outlook(request: Request, target: str = "S&P 500", _user=Depends(get_optional_user), db: SessionType = Depends(get_db)):
    """Return the snapshot JSON for a target index.

    The snapshot contains current regime, probabilities, indicator readings,
    forward projections, transition matrix, and regime statistics.
    """
    row = (
        db.query(MacroOutlook)
        .filter_by(target_name=target)
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=404,
            detail="Macro outlook not computed yet. Admin must trigger computation.",
        )
    return {
        "target_name": row.target_name,
        "computed_at": row.computed_at.isoformat(),
        "snapshot": row.snapshot,
    }


@router.get("/macro/timeseries")
@_limiter.limit("30/minute")
def get_timeseries(request: Request, target: str = "S&P 500", _user=Depends(get_optional_user), db: SessionType = Depends(get_db)):
    """Return the time series JSON for a target index.

    Contains historical composites (growth, inflation, liquidity, tactical),
    allocation weights, regime probabilities, and target prices.
    """
    row = (
        db.query(MacroOutlook)
        .filter_by(target_name=target)
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=404,
            detail="Macro outlook not computed yet. Admin must trigger computation.",
        )
    return {
        "target_name": row.target_name,
        "computed_at": row.computed_at.isoformat(),
        "timeseries": row.timeseries,
    }


@router.get("/macro/backtest")
@_limiter.limit("30/minute")
def get_backtest(request: Request, target: str = "S&P 500", _user=Depends(get_optional_user), db: SessionType = Depends(get_db)):
    """Return the backtest JSON for a target index.

    Contains equity curves (strategy, benchmark, 100% index), allocation
    weight history, and performance statistics.
    """
    row = (
        db.query(MacroOutlook)
        .filter_by(target_name=target)
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=404,
            detail="Macro outlook not computed yet. Admin must trigger computation.",
        )
    return {
        "target_name": row.target_name,
        "computed_at": row.computed_at.isoformat(),
        "backtest": row.backtest,
    }


@router.get("/macro/stress-test")
@_limiter.limit("10/minute")
def get_stress_test(request: Request, target: str = "KOSPI", _user=Depends(get_optional_user)):
    """Compute stress test analysis for a target index.

    Auto-detects historical crash events, computes forward returns at
    standard horizons, and builds recovery curves.
    """
    if target not in TARGET_INDICES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown target '{target}'. Available: {list(TARGET_INDICES.keys())}",
        )
    try:
        from ix.core.stress_test import compute_stress_test

        result = compute_stress_test(target)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logger.exception(f"Stress test failed for {target}")
        raise HTTPException(status_code=500, detail="Stress test computation failed")


def _refresh_target(target_name: str) -> None:
    """Background worker to recompute macro outlook for a single target."""
    try:
        from ix.core.macro.pipeline import compute_and_save

        logger.info(f"Background refresh started for {target_name}")
        compute_and_save(target_name)
        logger.info(f"Background refresh completed for {target_name}")
    except Exception as e:
        logger.warning(f"Background refresh failed for {target_name}: {e}")


@router.post("/macro/refresh")
def refresh_outlook(
    target: str = "S&P 500", _user=Depends(get_current_admin_user)
):
    """Trigger a background recompute of macro outlook for a target index.

    Admin-only. Returns immediately; computation runs in a background thread.
    """
    if target not in TARGET_INDICES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown target '{target}'. Available: {list(TARGET_INDICES.keys())}",
        )

    _refresh_executor.submit(_refresh_target, target)

    return {
        "status": "Computing in background",
        "target": target,
        "message": f"Refresh triggered for {target}. Check /api/macro/outlook?target={target} in a few minutes.",
    }


# ===========================================================================
# REGIME STRATEGY ENDPOINTS
# ===========================================================================


@router.get("/macro/regime-strategy/indices")
@_limiter.limit("30/minute")
def list_regime_strategy_indices(request: Request, _user=Depends(get_optional_user), db: SessionType = Depends(get_db)):
    """List indices with precomputed regime strategy data."""
    rows = db.query(MacroRegimeStrategy.index_name).all()
    return {"indices": [r[0] for r in rows]}


@router.get("/macro/regime-strategy/backtest")
@_limiter.limit("30/minute")
def get_regime_strategy_backtest(request: Request, index: str = "ACWI", _user=Depends(get_optional_user), db: SessionType = Depends(get_db)):
    """Return precomputed walk-forward backtest results for a single index."""
    row = (
        db.query(MacroRegimeStrategy)
        .filter_by(index_name=index)
        .first()
    )
    if not row:
        raise HTTPException(404, f"No regime strategy data for '{index}'.")
    return {
        "index_name": row.index_name,
        "computed_at": row.computed_at.isoformat(),
        "backtest": row.backtest,
    }


@router.get("/macro/regime-strategy/factors")
@_limiter.limit("30/minute")
def get_regime_strategy_factors(request: Request, index: str = "ACWI", _user=Depends(get_optional_user), db: SessionType = Depends(get_db)):
    """Return factor selection history for a single index."""
    row = (
        db.query(MacroRegimeStrategy)
        .filter_by(index_name=index)
        .first()
    )
    if not row:
        raise HTTPException(404, f"No regime strategy data for '{index}'.")
    return {
        "index_name": row.index_name,
        "computed_at": row.computed_at.isoformat(),
        "factors": row.factors,
    }


@router.get("/macro/regime-strategy/signal")
@_limiter.limit("30/minute")
def get_regime_strategy_signal(request: Request, index: str = "ACWI", _user=Depends(get_optional_user), db: SessionType = Depends(get_db)):
    """Return current signal readings for a single index."""
    row = (
        db.query(MacroRegimeStrategy)
        .filter_by(index_name=index)
        .first()
    )
    if not row:
        raise HTTPException(404, f"No regime strategy data for '{index}'.")
    return {
        "index_name": row.index_name,
        "computed_at": row.computed_at.isoformat(),
        "current_signal": row.current_signal,
    }


@router.get("/macro/regime-strategy/summary")
@_limiter.limit("30/minute")
def get_regime_strategy_summary(request: Request, _user=Depends(get_optional_user), db: SessionType = Depends(get_db)):
    """Compact summary of all indices -- for dashboard widget."""
    rows = db.query(MacroRegimeStrategy).all()
    if not rows:
        raise HTTPException(404, "No regime strategy data computed yet.")
    indices = []
    for row in rows:
        sig = row.current_signal or {}
        cat_sigs = sig.get("category_signals", {})
        # Pick the Blended or first available signal for headline
        headline = cat_sigs.get("Blended") or cat_sigs.get("Growth") or {}
        regime_sig = cat_sigs.get("Regime", {})
        # Extract backtest performance from Blended strategy
        bt = row.backtest or {}
        strats = bt.get("strategies", {})
        blended = strats.get("Blended") or next(iter(strats.values()), {})

        indices.append({
            "index_name": row.index_name,
            "computed_at": row.computed_at.isoformat(),
            "eq_weight": headline.get("eq_weight"),
            "label": headline.get("label", ""),
            "regime": regime_sig.get("regime", ""),
            "growth_pctile": regime_sig.get("growth_pctile"),
            "inflation_pctile": regime_sig.get("inflation_pctile"),
            "category_signals": cat_sigs,
            "sharpe": blended.get("sharpe"),
            "alpha": blended.get("alpha"),
            "max_dd": blended.get("max_dd"),
            "ann_return": blended.get("ann_return"),
        })
    return {"indices": indices}


@router.post("/macro/regime-strategy/refresh")
@_limiter.limit("5/minute")
def refresh_regime_strategy(
    request: Request, index: str = "ACWI", _user=Depends(get_current_admin_user)
):
    """Admin-only: trigger background recompute for a single index."""
    from ix.core.macro.wf_backtest import INDEX_MAP

    if index not in INDEX_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown index '{index}'. Available: {list(INDEX_MAP.keys())}",
        )

    def _worker(idx: str):
        try:
            from ix.core.macro.wf_compute import compute_and_save
            compute_and_save(idx)
        except Exception as e:
            logger.warning(f"Regime strategy refresh failed for {idx}: {e}")

    _refresh_executor.submit(_worker, index)
    return {"status": "Computing in background", "index": index}


# ===========================================================================
# TECHNICALS (delegates to ix.core.technical.vams_technicals)
# ===========================================================================


@router.get("/macro/technicals")
@_limiter.limit("30/minute")
def get_technicals(request: Request, index: str | None = None, _user=Depends(get_optional_user)):
    """VAMS momentum regime data."""
    if index:
        from ix.core.technical.vams_technicals import get_or_compute_index

        result = get_or_compute_index(index)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Index '{index}' not found")
        return result

    from ix.core.technical.vams_technicals import get_summary

    return get_summary()


@router.get("/macro/technicals/summary")
@_limiter.limit("30/minute")
def macro_technicals_summary(request: Request, _user=Depends(get_optional_user)):
    """Lightweight summary of all indices — no chart data."""
    from ix.core.technical.vams_technicals import get_summary

    return get_summary()


@router.get("/macro/technicals/detail")
@_limiter.limit("30/minute")
def macro_technicals_detail(request: Request, index: str, _user=Depends(get_optional_user)):
    """Chart data (daily_prices, weekly_vams, vomo history) for a single index."""
    from ix.core.technical.vams_technicals import get_detail

    result = get_detail(index)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Index '{index}' not found")
    return result


@router.post("/macro/technicals/refresh")
@_limiter.limit("5/minute")
def refresh_technicals(request: Request, index: str, _user=Depends(get_current_admin_user)):
    """Refresh a single index's technical data."""
    from ix.core.technical.vams_technicals import refresh_single

    return refresh_single(index)


@router.get("/macro/cacri-history")
@_limiter.limit("30/minute")
def get_cacri_history(request: Request, _user=Depends(get_optional_user), db: SessionType = Depends(get_db)):
    """Historical CACRI timeseries."""
    from ix.db.models.api_cache import ApiCache

    entry = db.query(ApiCache).get("cacri-history")
    if entry and entry.value:
        return entry.value

    from ix.core.technical.vams_technicals import compute_cacri_history

    return compute_cacri_history()
