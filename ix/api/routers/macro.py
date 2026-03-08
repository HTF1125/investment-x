"""Macro outlook API -- serves precomputed regime/allocation data.

Endpoints read from the macro_outlook DB table (populated by the scheduler).
The POST /macro/refresh endpoint triggers a background recompute for admins.
"""

import threading

from fastapi import APIRouter, Depends, HTTPException

from ix.api.dependencies import get_current_user, get_current_admin_user
from ix.db.conn import Session as SessionCtx
from ix.db.models.macro_outlook import MacroOutlook
from ix.core.macro.config import TARGET_INDICES
from ix.misc import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/macro/targets")
def list_targets(_user=Depends(get_current_user)):
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
def get_outlook(target: str = "S&P 500", _user=Depends(get_current_user)):
    """Return the snapshot JSON for a target index.

    The snapshot contains current regime, probabilities, indicator readings,
    forward projections, transition matrix, and regime statistics.
    """
    with SessionCtx() as session:
        row = (
            session.query(MacroOutlook)
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
def get_timeseries(target: str = "S&P 500", _user=Depends(get_current_user)):
    """Return the time series JSON for a target index.

    Contains historical composites (growth, inflation, liquidity, tactical),
    allocation weights, regime probabilities, and target prices.
    """
    with SessionCtx() as session:
        row = (
            session.query(MacroOutlook)
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
def get_backtest(target: str = "S&P 500", _user=Depends(get_current_user)):
    """Return the backtest JSON for a target index.

    Contains equity curves (strategy, benchmark, 100% index), allocation
    weight history, and performance statistics.
    """
    with SessionCtx() as session:
        row = (
            session.query(MacroOutlook)
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

    thread = threading.Thread(
        target=_refresh_target,
        args=(target,),
        daemon=True,
        name=f"macro-refresh-{target}",
    )
    thread.start()

    return {
        "status": "Computing in background",
        "target": target,
        "message": f"Refresh triggered for {target}. Check /api/macro/outlook?target={target} in a few minutes.",
    }
