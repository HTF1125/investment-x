"""Custom charts API router.

Route handlers only — chart rendering, code execution, PDF/HTML export
logic lives in ``ix.common.charting``.
"""
from fastapi import APIRouter, Depends, HTTPException, Form, Response, Request
from sqlalchemy.orm import Session, load_only, joinedload
from sqlalchemy import func, or_
from typing import List, Optional, Any, Dict
from pydantic import BaseModel
from datetime import datetime, timezone
import json
import time
import traceback
import plotly.io as pio

from ix.db.conn import get_session
from ix.db.models import User
from ix.db.models.charts import Charts
from ix.api.dependencies import (
    get_current_user,
    get_optional_user,
    user_role as _user_role,
    is_owner_role as _is_owner,
    is_admin_role as _is_admin,
    user_id_str as _user_id,
)
from ix.common import get_logger
from ix.common.viz.theme import theme_figure_for_delivery as _theme_figure_for_delivery
from ix.common.security.safe_custom_code import UnsafeCustomChartCodeError
from ix.common.viz.charting import (
    json_dumps_fast as _json_dumps_fast,
    prepare_custom_chart_code as _prepare_chart_code,
    execute_custom_code,
    get_clean_figure_json,
    creator_metadata as _creator_metadata,
    generate_pdf_buffer,
    is_pdf_available,
    build_html_export,
    ChartExecutionError,
)

logger = get_logger(__name__)

router = APIRouter()

from ix.api.rate_limit import limiter as _limiter


# ---------------------------------------------------------------------------
# Authorization helpers
# ---------------------------------------------------------------------------

def _is_chart_owner(chart: Charts, user: User) -> bool:
    chart_owner_id = str(getattr(chart, "created_by_user_id", "") or "")
    return bool(chart_owner_id and chart_owner_id == _user_id(user))


def _can_edit_chart(chart: Charts, user: User) -> bool:
    if _is_owner(user):
        return True
    if _is_admin(user):
        return True
    return _is_chart_owner(chart, user)


def _can_view_chart(chart: Charts, user: Optional[User]) -> bool:
    if bool(getattr(chart, "public", False)):
        return True
    if user is None:
        return False
    return _is_owner(user) or _is_admin(user) or _is_chart_owner(chart, user)


def _assert_owner_only(
    user: User, detail: str = "Only owner can perform this action."
) -> None:
    if not _is_owner(user):
        raise HTTPException(status_code=403, detail=detail)


def _assert_can_create_chart(user: User) -> None:
    role = _user_role(user)
    if role == User.ROLE_ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Admin role is refresh-only for chart operations.",
        )


# ---------------------------------------------------------------------------
# Code validation (wraps common.charting with HTTPException)
# ---------------------------------------------------------------------------

def _prepare_custom_chart_code(code: str) -> str:
    """Validate and normalize chart code, raising HTTPException on failure."""
    try:
        return _prepare_chart_code(code)
    except UnsafeCustomChartCodeError as exc:
        logger.warning("Rejected unsafe custom chart code: %s", exc)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Validation Error",
                "message": "Chart code contains forbidden syntax. Please review and try again.",
            },
        ) from exc


def _execute_chart_code(code: str, *, validated: bool = False) -> Any:
    """Execute chart code, translating errors to HTTPException."""
    try:
        return execute_custom_code(code, validated=validated)
    except UnsafeCustomChartCodeError as exc:
        logger.warning("Rejected unsafe custom chart code during execution: %s", exc)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Validation Error",
                "message": "Chart code contains forbidden syntax. Please review and try again.",
            },
        ) from exc
    except ChartExecutionError as exc:
        status = 500 if exc.error_type == "Internal Error" else 400
        raise HTTPException(
            status_code=status,
            detail={"error": exc.error_type, "message": str(exc)},
        ) from exc


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ChartCreate(BaseModel):
    name: str = "Untitled Analysis"
    code: str
    category: Optional[str] = "Personal"
    description: Optional[str] = None
    tags: List[str] = []
    public: bool = True
    chart_style: Optional[str] = None


class ChartUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    public: Optional[bool] = None
    chart_style: Optional[str] = None


class PublicToggle(BaseModel):
    """Toggle public flag for one or more charts."""
    ids: List[str]
    public: bool


class ChartResponse(BaseModel):
    id: str
    name: Optional[str]
    code: str
    category: Optional[str]
    description: Optional[str]
    tags: List[str]
    figure: Optional[Dict[str, Any]]
    chart_style: Optional[str] = None
    public: bool = True
    rank: int = 0
    created_by_user_id: Optional[str] = None
    created_by_email: Optional[str] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChartListItemResponse(BaseModel):
    id: str
    name: Optional[str]
    category: Optional[str]
    description: Optional[str]
    tags: List[str]
    public: bool = True
    rank: int = 0
    created_by_user_id: Optional[str] = None
    created_by_email: Optional[str] = None
    created_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    code: Optional[str] = None
    figure: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class CodePreviewRequest(BaseModel):
    code: str


class ChartReorderItem(BaseModel):
    id: str


class ReorderRequest(BaseModel):
    items: List[ChartReorderItem]


class PDFExportRequest(BaseModel):
    items: List[str]
    theme: str = "light"


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------

def _to_custom_chart_response(chart: Charts):
    payload = ChartResponse.from_orm(chart)
    payload.figure = _theme_figure_for_delivery(chart.figure)
    meta = _creator_metadata(chart)
    payload.created_by_user_id = meta["created_by_user_id"]
    payload.created_by_email = meta["created_by_email"]
    payload.created_by_name = meta["created_by_name"]
    return payload


def _to_custom_chart_list_item(
    chart: Charts,
    include_code: bool = False,
    include_figure: bool = False,
) -> ChartListItemResponse:
    meta = _creator_metadata(chart)
    payload: Dict[str, Any] = {
        "id": str(chart.id),
        "name": chart.name,
        "category": chart.category,
        "description": chart.description,
        "tags": chart.tags or [],
        "public": bool(chart.public),
        "rank": int(chart.rank or 0),
        "created_by_user_id": meta["created_by_user_id"],
        "created_by_email": meta["created_by_email"],
        "created_by_name": meta["created_by_name"],
        "created_at": chart.created_at,
        "updated_at": chart.updated_at,
    }
    if include_code:
        payload["code"] = chart.code
    if include_figure:
        payload["figure"] = _theme_figure_for_delivery(chart.figure)
    return ChartListItemResponse(**payload)


def _load_explicit_export_charts(
    db: Session,
    current_user: User,
    requested_ids: List[str],
    *columns: Any,
) -> List[Any]:
    if not requested_ids:
        return []
    query = db.query(*columns) if columns else db.query(Charts)
    charts = query.filter(Charts.id.in_(requested_ids)).all()
    chart_map = {str(chart.id): chart for chart in charts}
    missing_ids = [cid for cid in requested_ids if cid not in chart_map]
    if missing_ids:
        raise HTTPException(status_code=404, detail="Chart not found")
    ordered = [chart_map[cid] for cid in requested_ids]
    if any(not _can_view_chart(chart, current_user) for chart in ordered):
        raise HTTPException(status_code=404, detail="Chart not found")
    return ordered


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/custom/preview")
@_limiter.limit("10/minute")
def preview_custom_chart(
    request: Request,
    body: CodePreviewRequest,
    current_user: User = Depends(get_current_user),
):
    """Execute code and return figure JSON without saving."""
    start_time = time.time()
    logger.info("Previewing custom chart. Code length: %d", len(body.code))

    try:
        validated_code = _prepare_custom_chart_code(body.code)
        fig = _execute_chart_code(validated_code, validated=True)
        exec_duration = time.time() - start_time
        logger.info("Chart execution completed in %.2fs", exec_duration)
    except Exception as e:
        exec_duration = time.time() - start_time
        logger.error("Execution failed after %.2fs: %s", exec_duration, e)
        if isinstance(e, HTTPException):
            raise e
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=400,
            detail={"error": "Execution Error", "message": str(e)},
        )

    try:
        serial_start = time.time()
        json_str = _json_dumps_fast(fig) if isinstance(fig, dict) else pio.to_json(fig)
        total_duration = time.time() - start_time
        logger.info(
            "Chart preview complete. exec=%.2fs serial=%.2fs total=%.2fs size=%d bytes",
            exec_duration,
            time.time() - serial_start,
            total_duration,
            len(json_str),
        )
        return Response(content=json_str, media_type="application/json")
    except Exception as e:
        logger.error("Failed to serialize figure: %s", e)
        raise HTTPException(
            status_code=500, detail="Failed to serialize figure to JSON"
        )


@router.post("/custom", response_model=ChartResponse)
@_limiter.limit("10/minute")
def create_custom_chart(
    request: Request,
    chart_data: ChartCreate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Create a new custom chart."""
    _assert_can_create_chart(current_user)
    logger.info("Creating new chart with name: '%s'", chart_data.name)
    normalized_code = _prepare_custom_chart_code(chart_data.code)

    try:
        fig = _execute_chart_code(normalized_code, validated=True)
        figure_json = get_clean_figure_json(fig)
    except Exception as exc:
        logger.debug(
            "Initial figure render failed for new chart '%s': %s",
            chart_data.name,
            exc,
        )
        figure_json = None

    max_rank = db.query(func.max(Charts.rank)).scalar() or 0
    next_rank = max_rank + 1

    new_chart = Charts(
        name=chart_data.name,
        code=normalized_code,
        category=chart_data.category,
        description=chart_data.description,
        tags=chart_data.tags,
        figure=figure_json,
        chart_style=chart_data.chart_style,
        public=chart_data.public,
        rank=next_rank,
        created_by_user_id=_user_id(current_user) or None,
    )

    db.add(new_chart)
    try:
        db.commit()
        db.refresh(new_chart)
    except Exception:
        db.rollback()
        logger.error("DB commit failed while creating chart '%s'", chart_data.name)
        raise HTTPException(status_code=500, detail="Failed to save chart")
    logger.info(
        "New chart created with ID: %s, Name: '%s'", new_chart.id, new_chart.name
    )
    return _to_custom_chart_response(new_chart)


@router.get("/custom", response_model=List[ChartListItemResponse])
def list_custom_charts(
    response: Response,
    include_code: bool = False,
    include_figure: bool = False,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """List all custom charts (shared across admins)."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    query = (
        db.query(Charts)
        .options(
            joinedload(Charts.creator).load_only(
                User.id, User.email, User.first_name, User.last_name,
            )
        )
        .filter(Charts.is_deleted == False)
    )
    if not (_is_owner(current_user) or _is_admin(current_user)):
        query = query.filter(
            or_(
                Charts.created_by_user_id == _user_id(current_user),
                Charts.public == True,
            )
        )

    # Column-level load_only — only fetch what's needed
    _base_cols = [
        Charts.id, Charts.name, Charts.category, Charts.description,
        Charts.tags, Charts.public, Charts.rank, Charts.created_by_user_id,
        Charts.created_at, Charts.updated_at,
    ]
    extra = []
    if include_code:
        extra.append(Charts.code)
    if include_figure:
        extra.append(Charts.figure)
    if not (include_code and include_figure):
        query = query.options(load_only(*_base_cols, *extra))

    charts = query.order_by(Charts.rank.asc(), Charts.created_at.desc()).all()
    return [
        _to_custom_chart_list_item(
            chart, include_code=include_code, include_figure=include_figure,
        )
        for chart in charts
    ]


@router.put("/custom/reorder")
@_limiter.limit("10/minute")
def reorder_custom_charts(
    request: Request,
    order_data: ReorderRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Reorder custom charts based on list of IDs."""
    _assert_owner_only(current_user)
    ids = [item.id for item in order_data.items]
    charts = db.query(Charts).filter(Charts.id.in_(ids)).all()
    chart_map = {str(c.id): c for c in charts}
    for index, chart_id in enumerate(ids):
        if str(chart_id) in chart_map:
            chart_map[str(chart_id)].rank = index
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.error("DB commit failed while reordering charts")
        raise HTTPException(status_code=500, detail="Failed to reorder charts")
    return {"message": "Reordered successfully"}


@router.patch("/custom/public")
@_limiter.limit("10/minute")
def toggle_public(
    request: Request,
    data: PublicToggle,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Toggle the public flag for one or more charts."""
    _assert_owner_only(current_user)
    db.query(Charts).filter(Charts.id.in_(data.ids)).update(
        {Charts.public: data.public}, synchronize_session="fetch"
    )
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.error("DB commit failed while toggling public flag")
        raise HTTPException(
            status_code=500, detail="Failed to update chart visibility"
        )
    return {"message": f"Updated {len(data.ids)} chart(s)"}


@router.post("/custom/pdf")
@_limiter.limit("5/minute")
def export_custom_charts_pdf(
    request: Request,
    items: str = Form(default="[]"),
    theme: str = Form(default="light"),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Generate a PDF of charts marked for export, in rank order."""
    if not is_pdf_available():
        raise HTTPException(
            status_code=503,
            detail="PDF export dependency is unavailable. Install `xhtml2pdf` and redeploy.",
        )

    try:
        items_list = json.loads(items)
        if not isinstance(items_list, list):
            items_list = []
    except json.JSONDecodeError:
        items_list = []
    requested_ids = [str(item) for item in items_list if item]

    try:
        if requested_ids:
            ordered_charts = _load_explicit_export_charts(
                db, current_user, requested_ids
            )
        else:
            ordered_charts = (
                db.query(Charts)
                .filter(Charts.public.is_(True))
                .order_by(Charts.rank.asc())
                .all()
            )

        if not ordered_charts:
            raise HTTPException(
                status_code=404, detail="No public charts found for PDF export"
            )

        pdf_buffer = generate_pdf_buffer(ordered_charts, theme=theme)
        filename = f"InvestmentX_Report_{datetime.now().strftime('%Y%m%d')}.pdf"

        return Response(
            content=pdf_buffer.read(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error("PDF Export failed: %s", e)
        raise HTTPException(status_code=500, detail="PDF export failed")


@router.post("/custom/html")
@_limiter.limit("5/minute")
def export_custom_charts_html(
    request: Request,
    items: str = Form(default="[]"),
    theme: str = Form(default="light"),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Generate a standalone HTML portfolio of charts marked for export."""
    try:
        items_list = json.loads(items)
        if not isinstance(items_list, list):
            items_list = []
    except json.JSONDecodeError:
        items_list = []
    requested_ids = [str(item) for item in items_list if item]

    try:
        chart_columns = (
            Charts.id,
            Charts.name,
            Charts.category,
            Charts.description,
            Charts.public,
            Charts.created_by_user_id,
            Charts.updated_at,
            Charts.figure,
        )

        if requested_ids:
            ordered_charts = _load_explicit_export_charts(
                db, current_user, requested_ids, *chart_columns,
            )
        else:
            ordered_charts = (
                db.query(*chart_columns)
                .filter(Charts.public.is_(True))
                .order_by(Charts.rank.asc())
                .all()
            )

        if not ordered_charts:
            raise HTTPException(
                status_code=404, detail="No charts marked for export"
            )

        full_html = build_html_export(ordered_charts, theme=theme)
        filename = (
            f"InvestmentX_Portfolio_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
        )

        return Response(
            content=full_html,
            media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        logger.error("HTML Export failed: %s", e)
        raise HTTPException(status_code=500, detail="HTML export failed")


@router.get("/custom/{chart_id}", response_model=ChartResponse)
def get_custom_chart(
    chart_id: str,
    response: Response,
    db: Session = Depends(get_session),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Get a specific custom chart (public charts viewable without login)."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    chart = db.query(Charts).filter(Charts.id == chart_id).first()
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    if not _can_view_chart(chart, current_user):
        raise HTTPException(status_code=404, detail="Chart not found")
    return _to_custom_chart_response(chart)


@router.post("/custom/{chart_id}/refresh", response_model=ChartResponse)
@_limiter.limit("10/minute")
def refresh_custom_chart(
    request: Request,
    chart_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Re-execute chart code and persist refreshed figure."""
    chart = db.query(Charts).filter(Charts.id == chart_id).first()
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")

    can_refresh = (
        _is_owner(current_user)
        or _is_admin(current_user)
        or _is_chart_owner(chart, current_user)
    )
    if not can_refresh:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    if not chart.code:
        raise HTTPException(status_code=400, detail="Chart code is missing")

    try:
        fig = _execute_chart_code(chart.code)
        chart.figure = get_clean_figure_json(fig)
    except Exception as e:
        logger.error("Failed to refresh figure for chart %s: %s", chart_id, e)
        logger.debug(
            "Refresh traceback for chart %s:\n%s",
            chart_id,
            traceback.format_exc(),
        )
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=400,
            detail={"error": "Execution Error", "message": str(e)},
        )

    try:
        db.commit()
        db.refresh(chart)
    except Exception:
        db.rollback()
        logger.error("DB commit failed while refreshing chart %s", chart_id)
        raise HTTPException(
            status_code=500, detail="Failed to save refreshed chart"
        )
    return _to_custom_chart_response(chart)


@router.put("/custom/{chart_id}", response_model=ChartResponse)
@_limiter.limit("10/minute")
def update_custom_chart(
    request: Request,
    chart_id: str,
    update_data: ChartUpdate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update a custom chart."""
    chart = db.query(Charts).filter(Charts.id == chart_id).first()
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    if not _can_edit_chart(chart, current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    old_code_len = len(chart.code) if chart.code else 0
    code_len = len(update_data.code) if update_data.code is not None else "N/A"
    logger.info(
        "PUT /custom/%s - New Code Len: %s, Old Code Len: %s",
        chart_id,
        code_len,
        old_code_len,
    )

    if update_data.name is not None:
        logger.info(
            "Setting chart name from '%s' to '%s'", chart.name, update_data.name
        )
        chart.name = update_data.name
    if update_data.category is not None:
        chart.category = update_data.category
    if update_data.description is not None:
        chart.description = update_data.description
    if update_data.tags is not None:
        chart.tags = update_data.tags
    if update_data.public is not None:
        chart.public = update_data.public
    if update_data.chart_style is not None:
        chart.chart_style = update_data.chart_style

    if update_data.code is not None:
        normalized_code = _prepare_custom_chart_code(update_data.code)
        try:
            logger.info("Re-executing code for chart %s...", chart_id)
            fig = _execute_chart_code(normalized_code, validated=True)
            figure_json = get_clean_figure_json(fig)
            chart.code = normalized_code
            chart.figure = figure_json

            fig_str = json.dumps(figure_json)[:200]
            logger.info(
                "Generated new figure for %s. Snippet: %s...", chart_id, fig_str
            )
        except Exception as e:
            logger.error(
                "Failed to update figure for chart %s: %s", chart_id, e
            )
            logger.debug(
                "Update traceback for chart %s:\n%s",
                chart_id,
                traceback.format_exc(),
            )
            if isinstance(e, HTTPException):
                raise e
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Execution Error",
                    "message": f"Code update rejected because figure generation failed: {str(e)}",
                },
            )

    try:
        db.commit()
        db.refresh(chart)
    except Exception:
        db.rollback()
        logger.error("DB commit failed while updating chart %s", chart_id)
        raise HTTPException(status_code=500, detail="Failed to save chart update")
    logger.info(
        "Chart %s updated successfully. Figure updated: %s",
        chart.id,
        update_data.code is not None,
    )
    return _to_custom_chart_response(chart)


@router.delete("/custom/{chart_id}")
@_limiter.limit("10/minute")
def delete_custom_chart(
    request: Request,
    chart_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Delete a custom chart."""
    chart = db.query(Charts).filter(Charts.id == chart_id).first()
    if not chart:
        raise HTTPException(status_code=404, detail="Chart not found")
    if not _can_edit_chart(chart, current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    chart.is_deleted = True
    chart.deleted_at = datetime.now(timezone.utc)
    try:
        db.commit()
    except Exception:
        db.rollback()
        logger.error("DB commit failed while soft-deleting chart %s", chart_id)
        raise HTTPException(status_code=500, detail="Failed to delete chart")
    return {"message": "Chart deleted successfully"}
