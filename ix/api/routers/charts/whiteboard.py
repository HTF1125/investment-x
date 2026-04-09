from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session, defer
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

from ix.db.conn import get_session
from ix.db.models import Whiteboard, User
from ix.api.dependencies import get_current_user
from ix.api.rate_limit import limiter as _limiter
from ix.common import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ── Pydantic schemas ──


class WhiteboardSummary(BaseModel):
    id: str
    title: str
    thumbnail: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WhiteboardDetail(BaseModel):
    id: str
    user_id: str
    title: str
    scene_data: dict
    thumbnail: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WhiteboardCreate(BaseModel):
    title: str = "Untitled"
    scene_data: dict = Field(default_factory=dict)


class WhiteboardUpdate(BaseModel):
    title: Optional[str] = None
    scene_data: Optional[dict] = None
    thumbnail: Optional[str] = None


# ── Endpoints ──


@router.get("/whiteboards", response_model=List[WhiteboardSummary])
def list_whiteboards(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """List user's whiteboards (lightweight, no scene_data)."""
    rows = (
        db.query(Whiteboard)
        .options(defer(Whiteboard.scene_data))
        .filter(
            Whiteboard.user_id == str(user.id),
            Whiteboard.is_deleted == False,
        )
        .order_by(Whiteboard.updated_at.desc())
        .all()
    )
    return [
        WhiteboardSummary(
            id=str(r.id),
            title=r.title,
            thumbnail=r.thumbnail,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.post("/whiteboards", response_model=WhiteboardDetail, status_code=201)
@_limiter.limit("30/minute")
def create_whiteboard(
    request: Request,
    payload: WhiteboardCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """Create a new whiteboard."""
    wb = Whiteboard(
        user_id=str(user.id),
        title=payload.title,
        scene_data=payload.scene_data,
    )
    db.add(wb)
    db.commit()
    db.refresh(wb)
    return WhiteboardDetail(
        id=str(wb.id),
        user_id=str(wb.user_id),
        title=wb.title,
        scene_data=wb.scene_data,
        thumbnail=wb.thumbnail,
        created_at=wb.created_at,
        updated_at=wb.updated_at,
    )


@router.get("/whiteboards/{whiteboard_id}", response_model=WhiteboardDetail)
def get_whiteboard(
    request: Request,
    whiteboard_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """Get a whiteboard with full scene data."""
    wb = (
        db.query(Whiteboard)
        .filter(
            Whiteboard.id == whiteboard_id,
            Whiteboard.user_id == str(user.id),
            Whiteboard.is_deleted == False,
        )
        .first()
    )
    if not wb:
        raise HTTPException(status_code=404, detail="Whiteboard not found")
    return WhiteboardDetail(
        id=str(wb.id),
        user_id=str(wb.user_id),
        title=wb.title,
        scene_data=wb.scene_data or {},
        thumbnail=wb.thumbnail,
        created_at=wb.created_at,
        updated_at=wb.updated_at,
    )


@router.put("/whiteboards/{whiteboard_id}", response_model=WhiteboardDetail)
@_limiter.limit("60/minute")
def update_whiteboard(
    request: Request,
    whiteboard_id: str,
    payload: WhiteboardUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """Update a whiteboard (title, scene_data, thumbnail)."""
    wb = (
        db.query(Whiteboard)
        .filter(
            Whiteboard.id == whiteboard_id,
            Whiteboard.user_id == str(user.id),
            Whiteboard.is_deleted == False,
        )
        .first()
    )
    if not wb:
        raise HTTPException(status_code=404, detail="Whiteboard not found")

    if payload.title is not None:
        wb.title = payload.title
    if payload.scene_data is not None:
        wb.scene_data = payload.scene_data
    if payload.thumbnail is not None:
        wb.thumbnail = payload.thumbnail

    db.commit()
    db.refresh(wb)
    return WhiteboardDetail(
        id=str(wb.id),
        user_id=str(wb.user_id),
        title=wb.title,
        scene_data=wb.scene_data or {},
        thumbnail=wb.thumbnail,
        created_at=wb.created_at,
        updated_at=wb.updated_at,
    )


@router.delete("/whiteboards/{whiteboard_id}", status_code=204)
@_limiter.limit("30/minute")
def delete_whiteboard(
    request: Request,
    whiteboard_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """Soft-delete a whiteboard."""
    wb = (
        db.query(Whiteboard)
        .filter(
            Whiteboard.id == whiteboard_id,
            Whiteboard.user_id == str(user.id),
            Whiteboard.is_deleted == False,
        )
        .first()
    )
    if not wb:
        raise HTTPException(status_code=404, detail="Whiteboard not found")

    wb.is_deleted = True
    wb.deleted_at = datetime.utcnow()
    db.commit()
    return None
