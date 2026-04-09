from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from ix.db.conn import get_session
from ix.db.models.report import Report
from ix.db.models import User
from ix.api.dependencies import get_current_user
from ix.api.rate_limit import limiter as _limiter
from ix.common import get_logger

logger = get_logger(__name__)

router = APIRouter()


# ── Pydantic schemas ──


class ReportSummary(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    slide_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportDetail(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    slides: list
    settings: dict = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReportCreate(BaseModel):
    name: str = "Untitled Report"
    description: Optional[str] = None
    slides: list = Field(default_factory=list)
    settings: dict = Field(default_factory=dict)


class ReportUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    slides: Optional[list] = None
    settings: Optional[dict] = None


# ── Endpoints ──


@router.get("/reports", response_model=List[ReportSummary])
@_limiter.limit("30/minute")
def list_reports(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    rows = (
        db.query(
            Report.id, Report.name, Report.description,
            Report.created_at, Report.updated_at,
            sa_func.jsonb_array_length(Report.slides).label("slide_count"),
        )
        .filter(Report.user_id == str(user.id), Report.is_deleted == False)
        .order_by(Report.updated_at.desc())
        .all()
    )
    return [
        ReportSummary(
            id=str(r.id),
            name=r.name,
            description=r.description,
            slide_count=r.slide_count or 0,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.post("/reports", response_model=ReportDetail, status_code=201)
@_limiter.limit("30/minute")
def create_report(
    request: Request,
    payload: ReportCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    report = Report(
        user_id=str(user.id),
        name=payload.name,
        description=payload.description,
        slides=payload.slides,
        settings=payload.settings,
    )
    db.add(report)
    db.flush()
    db.refresh(report)
    return ReportDetail(
        id=str(report.id),
        user_id=str(report.user_id),
        name=report.name,
        description=report.description,
        slides=report.active_slides,
        settings=report.settings or {},
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


@router.get("/reports/{report_id}", response_model=ReportDetail)
@_limiter.limit("30/minute")
def get_report(
    request: Request,
    report_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.user_id == str(user.id), Report.is_deleted == False)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return ReportDetail(
        id=str(report.id),
        user_id=str(report.user_id),
        name=report.name,
        description=report.description,
        slides=report.active_slides,
        settings=report.settings or {},
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


@router.put("/reports/{report_id}", response_model=ReportDetail)
@_limiter.limit("60/minute")
def update_report(
    request: Request,
    report_id: str,
    payload: ReportUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.user_id == str(user.id), Report.is_deleted == False)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if payload.name is not None:
        report.name = payload.name
    if payload.description is not None:
        report.description = payload.description
    if payload.slides is not None:
        report.slides = payload.slides
    if payload.settings is not None:
        report.settings = payload.settings
    db.flush()
    db.refresh(report)
    return ReportDetail(
        id=str(report.id),
        user_id=str(report.user_id),
        name=report.name,
        description=report.description,
        slides=report.active_slides,
        settings=report.settings or {},
        created_at=report.created_at,
        updated_at=report.updated_at,
    )


@router.delete("/reports/{report_id}")
@_limiter.limit("30/minute")
def delete_report(
    request: Request,
    report_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    report = (
        db.query(Report)
        .filter(Report.id == report_id, Report.user_id == str(user.id), Report.is_deleted == False)
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    report.is_deleted = True
    report.deleted_at = datetime.now(timezone.utc)
    db.flush()
    return {"ok": True}
