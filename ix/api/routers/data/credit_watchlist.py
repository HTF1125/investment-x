"""
Credit Watchlist API — CRUD for entities under credit surveillance.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime
from sqlalchemy.orm import Session as SessionType
from sqlalchemy import case, or_

from ix.api.dependencies import get_db, get_current_admin_user, get_current_user
from ix.db.models.credit_event import CreditWatchlist
from ix.db.models.user import User
from ix.db.conn import ensure_connection
from ix.common import get_logger
from ix.api.rate_limit import limiter as _limiter

logger = get_logger(__name__)

router = APIRouter()


# ── Pydantic Schemas ────────────────────────────────────────────────

class WatchlistResponse(BaseModel):
    id: str
    entity: str
    entity_type: Optional[str] = None
    sector: Optional[str] = None
    region: Optional[str] = None
    current_rating: Optional[str] = None
    watch_reason: Optional[str] = None
    risk_level: str = "medium"
    signal_count: int = 0
    last_signal: Optional[str] = None
    cra_summary: Optional[str] = None
    added_by: Optional[str] = None
    active: bool = True
    notes: Optional[list] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class WatchlistCreate(BaseModel):
    entity: str
    entity_type: Optional[str] = None
    sector: Optional[str] = None
    region: Optional[str] = None
    current_rating: Optional[str] = None
    watch_reason: Optional[str] = None
    cra_summary: Optional[str] = None
    risk_level: str = "medium"
    added_by: str = "manual"


class WatchlistUpdate(BaseModel):
    entity: Optional[str] = None
    entity_type: Optional[str] = None
    sector: Optional[str] = None
    region: Optional[str] = None
    current_rating: Optional[str] = None
    watch_reason: Optional[str] = None
    cra_summary: Optional[str] = None
    risk_level: Optional[str] = None
    signal_count: Optional[int] = None
    last_signal: Optional[str] = None
    active: Optional[bool] = None
    notes: Optional[list] = None


# ── Helpers ─────────────────────────────────────────────────────────

def _to_response(w: CreditWatchlist) -> WatchlistResponse:
    return WatchlistResponse(
        id=str(w.id),
        entity=w.entity or "",
        entity_type=w.entity_type,
        sector=w.sector,
        region=w.region,
        current_rating=w.current_rating,
        watch_reason=w.watch_reason,
        risk_level=w.risk_level or "medium",
        signal_count=w.signal_count or 0,
        last_signal=w.last_signal,
        cra_summary=w.cra_summary,
        added_by=w.added_by,
        active=w.active if w.active is not None else True,
        notes=w.notes or [],
        created_at=w.created_at.isoformat() if w.created_at else None,
        updated_at=w.updated_at.isoformat() if w.updated_at else None,
    )


# ── Endpoints ───────────────────────────────────────────────────────

@router.get("/credit-watchlist", response_model=List[WatchlistResponse])
@_limiter.limit("120/minute")
def list_watchlist(
    request: Request,
    search: Optional[str] = Query(None, description="Search by entity, sector, or region"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level"),
    active_only: bool = Query(True, description="Show only active entries"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: SessionType = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List credit watchlist entities with search and pagination. Readable by any authenticated user; mutations remain admin-only."""
    ensure_connection()

    query = db.query(CreditWatchlist)

    if active_only:
        query = query.filter(CreditWatchlist.active == True)

    if search:
        term = search.strip()
        if term:
            pattern = f"%{term}%"
            query = query.filter(
                or_(
                    CreditWatchlist.entity.ilike(pattern),
                    CreditWatchlist.sector.ilike(pattern),
                    CreditWatchlist.region.ilike(pattern),
                    CreditWatchlist.current_rating.ilike(pattern),
                )
            )

    if risk_level:
        query = query.filter(CreditWatchlist.risk_level == risk_level.lower())

    # Sort: risk level (critical → high → medium → low), then most recently updated
    risk_order = case(
        (CreditWatchlist.risk_level == "critical", 0),
        (CreditWatchlist.risk_level == "high", 1),
        (CreditWatchlist.risk_level == "medium", 2),
        (CreditWatchlist.risk_level == "low", 3),
        else_=4,
    )
    items = (
        query.order_by(
            CreditWatchlist.active.desc(),
            risk_order.asc(),
            CreditWatchlist.updated_at.desc().nulls_last(),
            CreditWatchlist.created_at.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [_to_response(w) for w in items]


@router.post("/credit-watchlist", response_model=WatchlistResponse, status_code=201)
@_limiter.limit("30/minute")
def create_watchlist_entry(
    request: Request,
    payload: WatchlistCreate,
    db: SessionType = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Create a new watchlist entry."""
    ensure_connection()

    existing = db.query(CreditWatchlist).filter(
        CreditWatchlist.entity == payload.entity.strip()
    ).first()

    if existing:
        if existing.active:
            raise HTTPException(
                status_code=409,
                detail=f"'{payload.entity}' is already on the watchlist",
            )
        # Re-activate soft-deleted entry
        existing.active = True
        existing.entity_type = payload.entity_type or existing.entity_type
        existing.sector = payload.sector or existing.sector
        existing.region = payload.region or existing.region
        existing.current_rating = payload.current_rating or existing.current_rating
        existing.watch_reason = payload.watch_reason or existing.watch_reason
        existing.cra_summary = payload.cra_summary or existing.cra_summary
        existing.risk_level = payload.risk_level or existing.risk_level
        existing.added_by = payload.added_by or "manual"
        existing.signal_count = 0
        existing.updated_at = datetime.now()
        db.commit()
        db.refresh(existing)
        logger.info("Admin %s re-activated watchlist: %s", current_user.email, payload.entity)
        return _to_response(existing)

    try:
        entry = CreditWatchlist(
            entity=payload.entity.strip(),
            entity_type=payload.entity_type,
            sector=payload.sector,
            region=payload.region,
            current_rating=payload.current_rating,
            watch_reason=payload.watch_reason,
            cra_summary=payload.cra_summary,
            risk_level=payload.risk_level or "medium",
            added_by=payload.added_by or "manual",
            signal_count=0,
            notes=[],
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        logger.info("Admin %s added to watchlist: %s", current_user.email, payload.entity)
        return _to_response(entry)
    except Exception as e:
        db.rollback()
        logger.error("Failed to create watchlist entry: %s", e)
        raise HTTPException(status_code=500, detail="Failed to create watchlist entry")


@router.put("/credit-watchlist/{entry_id}", response_model=WatchlistResponse)
@_limiter.limit("30/minute")
def update_watchlist_entry(
    request: Request,
    entry_id: str,
    payload: WatchlistUpdate,
    db: SessionType = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Update a watchlist entry."""
    ensure_connection()

    entry = db.query(CreditWatchlist).filter(CreditWatchlist.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Watchlist entry not found")

    update_fields = payload.model_dump(exclude_unset=True)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    try:
        for field, value in update_fields.items():
            if hasattr(entry, field):
                setattr(entry, field, value)
        entry.updated_at = datetime.now()
        db.commit()
        db.refresh(entry)
        logger.info("Admin %s updated watchlist: %s", current_user.email, entry.entity)
        return _to_response(entry)
    except Exception as e:
        db.rollback()
        logger.error("Failed to update watchlist entry %s: %s", entry_id, e)
        raise HTTPException(status_code=500, detail="Failed to update watchlist entry")


@router.delete("/credit-watchlist/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
@_limiter.limit("10/minute")
def delete_watchlist_entry(
    request: Request,
    entry_id: str,
    db: SessionType = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """Soft-delete a watchlist entry (sets active=False)."""
    ensure_connection()

    entry = db.query(CreditWatchlist).filter(CreditWatchlist.id == entry_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Watchlist entry not found")

    try:
        entry.active = False
        entry.updated_at = datetime.now()
        db.commit()
        logger.info("Admin %s soft-deleted watchlist: %s", current_user.email, entry.entity)
    except Exception as e:
        db.rollback()
        logger.error("Failed to delete watchlist entry %s: %s", entry_id, e)
        raise HTTPException(status_code=500, detail="Failed to delete watchlist entry")
