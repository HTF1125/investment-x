from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

from ix.db.conn import get_session
from ix.db.models.chart_pack import ChartPack
from ix.db.models import User
from ix.api.dependencies import get_current_user, get_optional_user
from ix.api.rate_limit import limiter as _limiter
from ix.misc import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ── Pydantic schemas ──


class PackSummary(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    chart_count: int
    is_published: bool = False
    creator_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PackDetail(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    charts: list
    is_published: bool = False
    creator_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PackCreate(BaseModel):
    name: str = "Untitled Pack"
    description: Optional[str] = None
    charts: list = Field(default_factory=list)


class PackUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    charts: Optional[list] = None
    is_published: Optional[bool] = None


class PackAddChart(BaseModel):
    """Add a single chart config to an existing pack."""
    chart: dict


# ── Endpoints ──


@router.get("/chart-packs", response_model=List[PackSummary])
def list_packs(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    rows = (
        db.query(
            ChartPack.id, ChartPack.name, ChartPack.description,
            ChartPack.is_published,
            ChartPack.created_at, ChartPack.updated_at,
            sa_func.jsonb_array_length(ChartPack.charts).label("chart_count"),
        )
        .filter(ChartPack.user_id == str(user.id))
        .order_by(ChartPack.updated_at.desc())
        .all()
    )
    return [
        PackSummary(
            id=str(r.id),
            name=r.name,
            description=r.description,
            chart_count=r.chart_count or 0,
            is_published=r.is_published or False,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.get("/chart-packs/published", response_model=List[PackSummary])
def list_published_packs(
    request: Request,
    db: Session = Depends(get_session),
):
    """List all published chart packs (public, no auth required)."""
    rows = (
        db.query(
            ChartPack.id, ChartPack.name, ChartPack.description,
            ChartPack.is_published,
            ChartPack.created_at, ChartPack.updated_at,
            sa_func.jsonb_array_length(ChartPack.charts).label("chart_count"),
            User.first_name, User.last_name,
        )
        .join(User, User.id == ChartPack.user_id)
        .filter(ChartPack.is_published == True)
        .order_by(ChartPack.updated_at.desc())
        .all()
    )
    return [
        PackSummary(
            id=str(r.id),
            name=r.name,
            description=r.description,
            chart_count=r.chart_count or 0,
            is_published=True,
            creator_name=f"{r.first_name or ''} {r.last_name or ''}".strip() or None,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.post("/chart-packs", response_model=PackDetail, status_code=201)
@_limiter.limit("30/minute")
def create_pack(
    request: Request,
    payload: PackCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    pack = ChartPack(
        user_id=str(user.id),
        name=payload.name,
        description=payload.description,
        charts=payload.charts,
    )
    db.add(pack)
    db.flush()
    db.refresh(pack)
    return PackDetail(
        id=str(pack.id),
        user_id=str(pack.user_id),
        name=pack.name,
        description=pack.description,
        charts=pack.charts or [],
        is_published=pack.is_published or False,
        created_at=pack.created_at,
        updated_at=pack.updated_at,
    )


@router.get("/chart-packs/{pack_id}", response_model=PackDetail)
def get_pack(
    request: Request,
    pack_id: str,
    user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_session),
):
    pack = db.query(ChartPack).filter(ChartPack.id == pack_id).first()
    if not pack:
        raise HTTPException(status_code=404, detail="Chart pack not found")
    # Allow access if user owns the pack or it's published
    is_owner = user and str(user.id) == str(pack.user_id)
    if not is_owner and not pack.is_published:
        raise HTTPException(status_code=404, detail="Chart pack not found")
    creator = pack.creator
    creator_name = None
    if creator:
        creator_name = f"{creator.first_name or ''} {creator.last_name or ''}".strip() or None
    return PackDetail(
        id=str(pack.id),
        user_id=str(pack.user_id),
        name=pack.name,
        description=pack.description,
        charts=pack.charts or [],
        is_published=pack.is_published or False,
        creator_name=creator_name,
        created_at=pack.created_at,
        updated_at=pack.updated_at,
    )


@router.put("/chart-packs/{pack_id}", response_model=PackDetail)
@_limiter.limit("30/minute")
def update_pack(
    request: Request,
    pack_id: str,
    payload: PackUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    pack = (
        db.query(ChartPack)
        .filter(ChartPack.id == pack_id, ChartPack.user_id == str(user.id))
        .first()
    )
    if not pack:
        raise HTTPException(status_code=404, detail="Chart pack not found")
    if payload.name is not None:
        pack.name = payload.name
    if payload.description is not None:
        pack.description = payload.description
    if payload.charts is not None:
        pack.charts = payload.charts
    if payload.is_published is not None:
        pack.is_published = payload.is_published
    db.flush()
    db.refresh(pack)
    return PackDetail(
        id=str(pack.id),
        user_id=str(pack.user_id),
        name=pack.name,
        description=pack.description,
        charts=pack.charts or [],
        is_published=pack.is_published or False,
        created_at=pack.created_at,
        updated_at=pack.updated_at,
    )


@router.post("/chart-packs/{pack_id}/charts", response_model=PackDetail)
@_limiter.limit("30/minute")
def add_chart_to_pack(
    request: Request,
    pack_id: str,
    payload: PackAddChart,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """Append a single chart config to an existing pack."""
    pack = (
        db.query(ChartPack)
        .filter(ChartPack.id == pack_id, ChartPack.user_id == str(user.id))
        .first()
    )
    if not pack:
        raise HTTPException(status_code=404, detail="Chart pack not found")
    charts = list(pack.charts or [])
    charts.append(payload.chart)
    pack.charts = charts
    db.flush()
    db.refresh(pack)
    return PackDetail(
        id=str(pack.id),
        user_id=str(pack.user_id),
        name=pack.name,
        description=pack.description,
        charts=pack.charts or [],
        is_published=pack.is_published or False,
        created_at=pack.created_at,
        updated_at=pack.updated_at,
    )


@router.delete("/chart-packs/{pack_id}")
@_limiter.limit("30/minute")
def delete_pack(
    request: Request,
    pack_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    pack = (
        db.query(ChartPack)
        .filter(ChartPack.id == pack_id, ChartPack.user_id == str(user.id))
        .first()
    )
    if not pack:
        raise HTTPException(status_code=404, detail="Chart pack not found")
    db.delete(pack)
    db.flush()
    return {"ok": True}
