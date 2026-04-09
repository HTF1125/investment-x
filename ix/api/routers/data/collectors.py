"""Admin API endpoints for manual collector triggers and data access."""

from typing import Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends, Request
from sqlalchemy.orm import Session as SessionType
from ix.api.dependencies import get_current_user, get_current_admin_user, get_db, user_id_str
from ix.db.models.user import User
from ix.common import get_logger
from ix.api.rate_limit import limiter as _limiter

logger = get_logger(__name__)

router = APIRouter(prefix="/collectors", tags=["Collectors"])


# ═══════════════════════════════════════════════════════════
# Background task wrappers
# ═══════════════════════════════════════════════════════════


def _run_collector_task(collector_name: str, user_id: str = None):
    """Run a single collector."""
    from ix.collectors.registry import get_collector

    collector = get_collector(collector_name)
    if not collector:
        return

    try:
        result = collector.collect()
        logger.info(f"Collector {collector_name} completed: {result.get('message', 'OK')}")
    except Exception as e:
        logger.exception(f"Collector {collector_name} failed: {e}")


def _run_all_collectors_task(user_id: str = None):
    """Run all collectors sequentially."""
    from ix.collectors.registry import get_all_collectors

    collectors = get_all_collectors()

    for i, collector in enumerate(collectors):
        try:
            result = collector.collect()
            logger.info(f"Collector {collector.name} ({i + 1}/{len(collectors)}): {result.get('message', 'OK')}")
        except Exception as e:
            logger.error(f"Collector {collector.name} failed: {e}")


# ═══════════════════════════════════════════════════════════
# Endpoints
# ═══════════════════════════════════════════════════════════


@router.post("/run/{collector_name}")
def run_collector(
    collector_name: str,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin_user),
):
    """Trigger a single collector manually. Admin only."""
    from ix.collectors.registry import get_collector

    collector = get_collector(collector_name)
    if not collector:
        raise HTTPException(400, f"Unknown collector: {collector_name}")

    uid = user_id_str(current_user)
    background_tasks.add_task(_run_collector_task, collector_name, uid)
    return {"message": f"{collector.display_name} triggered", "status": "started"}


@router.post("/run-all")
def run_all_collectors(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_admin_user),
):
    """Trigger all collectors sequentially. Admin only."""
    uid = user_id_str(current_user)
    background_tasks.add_task(_run_all_collectors_task, uid)
    return {"message": "All collectors triggered", "status": "started"}


@router.get("/status")
@_limiter.limit("30/minute")
def get_collector_statuses(request: Request, current_user: User = Depends(get_current_user), db: SessionType = Depends(get_db)):
    """Return status of all collectors."""
    from ix.collectors.registry import get_all_collectors
    from ix.db.models.collector_state import CollectorState

    collectors = get_all_collectors()
    statuses = []

    for c in collectors:
        state = (
            db.query(CollectorState)
            .filter(CollectorState.collector_name == c.name)
            .first()
        )
        statuses.append({
            "name": c.name,
            "display_name": c.display_name,
            "category": c.category,
            "schedule": c.schedule,
            "last_fetch_at": str(state.last_fetch_at) if state and state.last_fetch_at else None,
            "last_success_at": str(state.last_success_at) if state and state.last_success_at else None,
            "last_error": state.last_error if state else None,
            "last_data_date": state.last_data_date if state else None,
            "fetch_count": state.fetch_count if state else 0,
            "error_count": state.error_count if state else 0,
        })

    return {"collectors": statuses}


@router.get("/status/{collector_name}")
def get_collector_status(
    collector_name: str,
    current_user: User = Depends(get_current_user),
    db: SessionType = Depends(get_db),
):
    """Return status of a specific collector."""
    from ix.collectors.registry import get_collector
    from ix.db.models.collector_state import CollectorState

    collector = get_collector(collector_name)
    if not collector:
        raise HTTPException(404, f"Unknown collector: {collector_name}")

    state = (
        db.query(CollectorState)
        .filter(CollectorState.collector_name == collector_name)
        .first()
    )

    return {
        "name": collector.name,
        "display_name": collector.display_name,
        "category": collector.category,
        "schedule": collector.schedule,
        "last_fetch_at": str(state.last_fetch_at) if state and state.last_fetch_at else None,
        "last_success_at": str(state.last_success_at) if state and state.last_success_at else None,
        "last_error": state.last_error if state else None,
        "last_data_date": state.last_data_date if state else None,
        "fetch_count": state.fetch_count if state else 0,
        "error_count": state.error_count if state else 0,
        "state": dict(state.state) if state and state.state else {},
    }


@router.get("/13f/holdings")
def get_13f_holdings(
    fund: Optional[str] = None,
    symbol: Optional[str] = None,
    quarter: Optional[str] = None,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: SessionType = Depends(get_db),
):
    """Query 13-F institutional holdings with optional filters."""
    from ix.db.models.institutional_holding import InstitutionalHolding

    q = db.query(InstitutionalHolding)

    if fund:
        q = q.filter(InstitutionalHolding.fund_name.ilike(f"%{fund}%"))
    if symbol:
        q = q.filter(InstitutionalHolding.symbol == symbol.upper())
    if quarter:
        # Parse "2025-Q4" → date range
        import re
        match = re.match(r"(\d{4})-Q(\d)", quarter)
        if match:
            year, qtr = int(match.group(1)), int(match.group(2))
            from datetime import date
            q_start = date(year, (qtr - 1) * 3 + 1, 1)
            q_end = date(year, qtr * 3, 28)
            q = q.filter(
                InstitutionalHolding.report_date.between(q_start, q_end)
            )

    q = q.order_by(
        InstitutionalHolding.report_date.desc(),
        InstitutionalHolding.value_usd.desc(),
    )

    holdings = q.limit(limit).all()

    return {
        "holdings": [
            {
                "fund_name": h.fund_name,
                "cik": h.cik,
                "report_date": str(h.report_date),
                "filed_date": str(h.filed_date) if h.filed_date else None,
                "cusip": h.cusip,
                "symbol": h.symbol,
                "security_name": h.security_name,
                "shares": h.shares,
                "value_usd": h.value_usd,
                "put_call": h.put_call,
                "shares_change": h.shares_change,
                "shares_change_pct": h.shares_change_pct,
                "action": h.action,
            }
            for h in holdings
        ],
        "count": len(holdings),
    }


@router.get("/positioning")
@_limiter.limit("30/minute")
def get_positioning_overview(request: Request, current_user: User = Depends(get_current_user), db: SessionType = Depends(get_db)):
    """Aggregated positioning/sentiment data — latest values for all indicators."""
    from ix.db.models import Timeseries

    positioning_sources = ["CFTC", "AAII", "CBOE", "GoogleTrends", "Reddit", "FINRA"]
    result = {}

    series_list = (
        db.query(Timeseries)
        .filter(Timeseries.source.in_(positioning_sources))
        .all()
    )

    for ts in series_list:
        result[ts.code] = {
            "name": ts.name,
            "source": ts.source,
            "category": ts.category,
            "latest_value": ts.latest_value,
            "last_date": str(ts.end) if ts.end else None,
            "num_data": ts.num_data,
        }

    return {"positioning": result}
