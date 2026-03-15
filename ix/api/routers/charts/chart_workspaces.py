from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime

from ix.db.conn import get_session
from ix.db.models.chart_workspace import ChartWorkspace
from ix.db.models import User
from ix.api.dependencies import get_current_user
from ix.api.rate_limit import limiter as _limiter
from ix.misc import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ── Pydantic schemas ──


class WorkspaceSummary(BaseModel):
    id: str
    name: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkspaceDetail(BaseModel):
    id: str
    user_id: str
    name: str
    config: dict
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WorkspaceCreate(BaseModel):
    name: str = "Untitled"
    config: dict = Field(default_factory=dict)


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    config: Optional[dict] = None


# ── Endpoints ──


@router.get("/chart-workspaces", response_model=List[WorkspaceSummary])
def list_workspaces(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """List user's chart workspaces."""
    rows = (
        db.query(ChartWorkspace)
        .filter(
            ChartWorkspace.user_id == str(user.id),
        )
        .order_by(ChartWorkspace.updated_at.desc())
        .all()
    )
    return [
        WorkspaceSummary(
            id=str(r.id),
            name=r.name,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.post("/chart-workspaces", response_model=WorkspaceDetail, status_code=201)
@_limiter.limit("30/minute")
def create_workspace(
    request: Request,
    payload: WorkspaceCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """Create a new chart workspace."""
    ws = ChartWorkspace(
        user_id=str(user.id),
        name=payload.name,
        config=payload.config,
    )
    db.add(ws)
    db.flush()
    db.refresh(ws)
    return WorkspaceDetail(
        id=str(ws.id),
        user_id=str(ws.user_id),
        name=ws.name,
        config=ws.config,
        created_at=ws.created_at,
        updated_at=ws.updated_at,
    )


@router.get("/chart-workspaces/{workspace_id}", response_model=WorkspaceDetail)
def get_workspace(
    request: Request,
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """Get a chart workspace with full config."""
    ws = (
        db.query(ChartWorkspace)
        .filter(
            ChartWorkspace.id == workspace_id,
            ChartWorkspace.user_id == str(user.id),
        )
        .first()
    )
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return WorkspaceDetail(
        id=str(ws.id),
        user_id=str(ws.user_id),
        name=ws.name,
        config=ws.config or {},
        created_at=ws.created_at,
        updated_at=ws.updated_at,
    )


@router.put("/chart-workspaces/{workspace_id}", response_model=WorkspaceDetail)
@_limiter.limit("30/minute")
def update_workspace(
    request: Request,
    workspace_id: str,
    payload: WorkspaceUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """Update a chart workspace."""
    ws = (
        db.query(ChartWorkspace)
        .filter(
            ChartWorkspace.id == workspace_id,
            ChartWorkspace.user_id == str(user.id),
        )
        .first()
    )
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if payload.name is not None:
        ws.name = payload.name
    if payload.config is not None:
        ws.config = payload.config
    db.flush()
    db.refresh(ws)
    return WorkspaceDetail(
        id=str(ws.id),
        user_id=str(ws.user_id),
        name=ws.name,
        config=ws.config or {},
        created_at=ws.created_at,
        updated_at=ws.updated_at,
    )


@router.delete("/chart-workspaces/{workspace_id}")
@_limiter.limit("30/minute")
def delete_workspace(
    request: Request,
    workspace_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """Delete a chart workspace."""
    ws = (
        db.query(ChartWorkspace)
        .filter(
            ChartWorkspace.id == workspace_id,
            ChartWorkspace.user_id == str(user.id),
        )
        .first()
    )
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    db.delete(ws)
    db.flush()
    return {"ok": True}
