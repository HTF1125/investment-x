from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session, load_only
from typing import Optional, List, Dict, Any, Tuple
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from ix.db.conn import get_session
from ix.db.models.chart_pack import ChartPack
from ix.db.models import User
from ix.api.dependencies import get_current_user, get_optional_user
from ix.api.rate_limit import limiter as _limiter
from ix.api.routers.charts.pack_reports import (
    _require_pdf_dep,
    _resolve_chart_figure,
    generate_pack_report_pdf,
    generate_pack_report_pptx,
    _generate_slides_pdf,
)
from ix.common import get_logger

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


class PackReportRequest(BaseModel):
    pack_ids: List[str] = Field(..., min_length=1, max_length=20)
    theme: str = Field(default="light", pattern=r"^(light|dark)$")


class SlideData(BaseModel):
    """Layout-aware slide data for export."""
    layout: str = "chart_full"
    title: str = ""
    subtitle: str = ""
    narrative: str = ""
    figure: Optional[dict] = None
    figure2: Optional[dict] = None
    figure3: Optional[dict] = None
    kpis: Optional[List[dict]] = None
    agendaItems: Optional[List[str]] = Field(default=None, alias="agendaItems")
    columns: Optional[List[str]] = None

    class Config:
        populate_by_name = True


class PptxReportRequest(BaseModel):
    slides: List[SlideData] = Field(..., min_length=1, max_length=200)
    theme: str = Field(default="light", pattern=r"^(light|dark)$")
    report_title: str = Field(default="Investment-X Report")
    subtitle: str = Field(default="")
    author: str = Field(default="")
    classification: str = Field(default="For Internal Use Only")
    report_date: Optional[str] = Field(default=None)
    disclaimer: Optional[str] = Field(default=None)




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
        .filter(ChartPack.user_id == str(user.id), ChartPack.is_deleted == False)
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
        .filter(ChartPack.is_published == True, ChartPack.is_deleted == False)
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
    if not pack or pack.is_deleted:
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
        charts=pack.active_charts,
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
    if not pack or pack.is_deleted:
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
        charts=pack.active_charts,
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
    if not pack or pack.is_deleted:
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
        charts=pack.active_charts,
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
    if not pack or pack.is_deleted:
        raise HTTPException(status_code=404, detail="Chart pack not found")
    pack.is_deleted = True
    pack.deleted_at = datetime.now(timezone.utc)
    db.flush()
    return {"ok": True}


@router.post("/chart-packs/report")
@_limiter.limit("5/minute")
def generate_pack_report(
    request: Request,
    payload: PackReportRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    """Generate a PDF report from selected chart packs (in order)."""
    _require_pdf_dep()

    # Load all requested packs in one query
    packs = (
        db.query(ChartPack)
        .filter(ChartPack.id.in_(payload.pack_ids), ChartPack.is_deleted == False)
        .all()
    )
    packs_by_id = {str(p.id): p for p in packs}

    # Validate access and preserve requested order
    ordered_packs: List[ChartPack] = []
    for pid in payload.pack_ids:
        pack = packs_by_id.get(pid)
        if not pack:
            raise HTTPException(status_code=404, detail=f"Pack not found: {pid}")
        is_owner = str(user.id) == str(pack.user_id)
        if not is_owner and not pack.is_published:
            raise HTTPException(status_code=404, detail=f"Pack not found: {pid}")
        ordered_packs.append(pack)

    charts_by_id: Dict[str, Any] = {}

    # Resolve all chart figures
    pack_sections: List[Tuple[str, str, List[Dict[str, Any]]]] = []
    for pack in ordered_packs:
        chart_infos = []
        for c in (pack.active_charts or []):
            fig = _resolve_chart_figure(c, charts_by_id)
            if fig is None:
                continue
            chart_infos.append({
                "title": c.get("title") or c.get("name") or "",
                "description": c.get("description") or "",
                "figure": fig,
            })
        pack_sections.append((pack.name, pack.description or "", chart_infos))

    # Generate PDF
    pdf_buffer = generate_pack_report_pdf(pack_sections, theme=payload.theme)
    if pdf_buffer.getbuffer().nbytes == 0:
        raise HTTPException(status_code=422, detail="No renderable charts found in selected packs")

    filename = f"InvestmentX_PackReport_{datetime.now().strftime('%Y%m%d')}.pdf"
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/chart-packs/report/pptx")
@_limiter.limit("5/minute")
def generate_pack_report_pptx_endpoint(
    request: Request,
    payload: PptxReportRequest,
    user: User = Depends(get_current_user),
):
    """Generate a PPTX report from editor slide data."""
    slides_data = [s.model_dump(by_alias=True) for s in payload.slides]
    if not slides_data:
        raise HTTPException(status_code=422, detail="No slides provided")

    pptx_buffer = generate_pack_report_pptx(
        slides_data,
        theme=payload.theme,
        report_title=payload.report_title,
        classification=payload.classification,
    )
    if pptx_buffer.getbuffer().nbytes == 0:
        raise HTTPException(status_code=500, detail="PPTX generation failed")

    filename = f"InvestmentX_Report_{datetime.now().strftime('%Y%m%d')}.pptx"
    return Response(
        content=pptx_buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/chart-packs/report/pdf")
@_limiter.limit("5/minute")
def generate_slides_pdf_endpoint(
    request: Request,
    payload: PptxReportRequest,
    user: User = Depends(get_current_user),
):
    """Generate a PDF report from editor slide data."""
    slides_data = [s.model_dump(by_alias=True) for s in payload.slides]
    if not slides_data:
        raise HTTPException(status_code=422, detail="No slides provided")

    pdf_buffer = _generate_slides_pdf(
        slides_data,
        theme=payload.theme,
        report_title=payload.report_title,
        subtitle=payload.subtitle,
        author=payload.author,
        classification=payload.classification,
        report_date=payload.report_date,
        disclaimer=payload.disclaimer,
    )
    if pdf_buffer.getbuffer().nbytes == 0:
        raise HTTPException(status_code=500, detail="PDF generation failed")

    filename = f"InvestmentX_Report_{datetime.now().strftime('%Y%m%d')}.pdf"
    return Response(
        content=pdf_buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
