"""
Timeseries router for timeseries data management.

Route handlers and thin HTTP orchestration only.
Heavy computation lives in ix.core.timeseries_processing.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
    UploadFile,
    File,
)
from fastapi.responses import Response, StreamingResponse, FileResponse
from typing import Optional, List, Dict
from pydantic import BaseModel
import json
import pandas as pd
from datetime import datetime, date, timezone

from ix.api.schemas import (
    TimeseriesResponse,
    TimeseriesCreate,
    TimeseriesBulkUpdate,
    TimeseriesDataUpload,
    TimeseriesColumnarUpload,
    TimeseriesUpdate,
)
from ix.api.dependencies import get_db, get_current_admin_user, get_current_user, get_optional_user
from ix.db.models import Timeseries
from ix.db.conn import ensure_connection, Session
from ix.db.models.user import User
from sqlalchemy.orm import joinedload, Session as SessionType
from ix.common import get_logger
from ix.api.rate_limit import limiter as _limiter
from ix.common.security.safe_expression import UnsafeExpressionError

from ix.core.timeseries_processing import (
    BULK_META_FIELDS,
    BULK_EXAMPLE,
    apply_timeseries_updates,
    build_search_filter_and_order,
    generate_export_workbook,
    generate_create_template_workbook,
    generate_download_template_workbook,
    process_bulk_create,
    process_template_upload,
    merge_columnar_to_db,
    process_database_timeseries,
    evaluate_expression,
    execute_code_block,
    format_dataframe_to_column_dict,
    format_favorites_dataframe,
)

logger = get_logger(__name__)

router = APIRouter()


# ────────────────────────────────────────────────────────────────────
# List / Search
# ────────────────────────────────────────────────────────────────────


@router.get("/timeseries", response_model=List[TimeseriesResponse])
def get_timeseries(
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Limit number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    search: Optional[str] = Query(
        None,
        max_length=200,
        description="Search by code/name/source/category/provider/asset class/country",
    ),
    category: Optional[str] = Query(None, max_length=100, description="Filter by category"),
    asset_class: Optional[str] = Query(None, max_length=100, description="Filter by asset class"),
    provider: Optional[str] = Query(None, max_length=100, description="Filter by provider"),
    db: SessionType = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """
    GET /api/timeseries - List all timeseries with optional filtering and pagination.
    """
    ensure_connection()

    timeseries_query = db.query(Timeseries).filter(Timeseries.is_deleted == False)

    if search:
        timeseries_query = build_search_filter_and_order(
            timeseries_query, search, Timeseries
        )

    # Apply filters
    if category:
        timeseries_query = timeseries_query.filter(Timeseries.category == category)
    if asset_class:
        timeseries_query = timeseries_query.filter(
            Timeseries.asset_class == asset_class
        )
    if provider:
        timeseries_query = timeseries_query.filter(Timeseries.provider == provider)

    # Apply pagination
    if offset:
        timeseries_query = timeseries_query.offset(offset)
    if limit:
        timeseries_query = timeseries_query.limit(limit)

    timeseries_list = timeseries_query.all()

    formatted_timeseries = []
    for ts in timeseries_list:
        formatted_ts = TimeseriesResponse(
            id=str(ts.id),
            code=str(ts.code) if ts.code else None,
            name=str(ts.name) if ts.name else None,
            provider=ts.provider,
            asset_class=str(ts.asset_class) if ts.asset_class else None,
            category=ts.category,
            start=ts.start,
            end=ts.end,
            num_data=int(ts.num_data) if ts.num_data is not None else None,
            source=ts.source,
            source_code=getattr(ts, "source_code", None),
            frequency=str(ts.frequency) if ts.frequency else None,
            unit=getattr(ts, "unit", None),
            scale=getattr(ts, "scale", None),
            currency=getattr(ts, "currency", None),
            country=getattr(ts, "country", None),
            remark=str(ts.remark) if ts.remark else None,
            favorite=bool(ts.favorite) if ts.favorite is not None else False,
        )
        formatted_timeseries.append(formatted_ts)

    logger.info("Retrieved %d timeseries records", len(formatted_timeseries))
    return formatted_timeseries


@router.get("/timeseries/sources")
def get_timeseries_sources(
    db: SessionType = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Return distinct source names for timeseries that have source_code set."""
    from sqlalchemy import distinct

    ensure_connection()
    rows = (
        db.query(distinct(Timeseries.source))
        .filter(Timeseries.source_code.isnot(None))
        .filter(Timeseries.source.isnot(None))
        .all()
    )
    return sorted([r[0] for r in rows])


# ────────────────────────────────────────────────────────────────────
# Bulk-create template: download blank / upload filled
# ────────────────────────────────────────────────────────────────────


@router.get("/timeseries/export_all")
def export_all_timeseries(
    db: SessionType = Depends(get_db),
    _current_user: User = Depends(get_current_admin_user),
):
    """Export all timeseries metadata as an Excel file.

    Uses the same column layout as the create template so the file
    can be edited and re-uploaded via /timeseries/create_from_template.
    """
    ensure_connection()
    all_ts = db.query(Timeseries).order_by(Timeseries.code).all()

    buffer = generate_export_workbook(all_ts)
    today = date.today().strftime("%Y%m%d")
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.document",
        headers={
            "Content-Disposition": f'attachment; filename="timeseries_all_{today}.xlsx"'
        },
    )


@router.get("/timeseries/create_template")
def bulk_create_template(
    _current_user: User = Depends(get_current_user),
):
    """Download a blank Excel template for bulk timeseries creation.

    Sheet 1 "Metadata": one row per timeseries (columns = fields).
    Sheet 2 "Data": columnar time-series data (Date | code1 | code2 | ...).
    """
    buffer = generate_create_template_workbook()
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.document",
        headers={
            "Content-Disposition": 'attachment; filename="timeseries_create_template.xlsx"'
        },
    )


@router.post("/timeseries/create_from_template")
@_limiter.limit("10/minute")
async def bulk_create_from_template(
    request: Request,
    file: UploadFile = File(...),
    _current_user: User = Depends(get_current_admin_user),
):
    """Upload a filled bulk-creation template.

    Creates new timeseries from the Metadata sheet and optionally merges
    time-series data from the Data sheet.
    """
    import asyncio

    contents = await file.read()
    if len(contents) > 200 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 200MB size limit")

    try:
        result = await asyncio.to_thread(process_bulk_create, contents)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.get("/timeseries/download_template")
def download_template(
    source: Optional[List[str]] = Query(
        None,
        description="Filter by source(s): Bloomberg, FactSet, Infomax (repeatable)",
    ),
    start_date: Optional[str] = Query(
        None, description="Start date (ISO-8601), default ~2 years ago"
    ),
    end_date: Optional[str] = Query(
        None, description="End date (ISO-8601), default today"
    ),
    db: SessionType = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """Generate an Excel template for data download/upload workflow.

    Produces a .xlsx file with metadata rows and pre-built formulas
    matching the Google Sheets Bloomberg/FactSet/Infomax workflow.
    Accepts multiple source values via repeated query params.
    """
    ensure_connection()

    # Date range
    end_dt = pd.to_datetime(end_date) if end_date else pd.Timestamp.now()
    start_dt = (
        pd.to_datetime(start_date) if start_date else end_dt - pd.DateOffset(years=1)
    )

    # Query timeseries that have source_code set
    query = db.query(Timeseries).filter(Timeseries.source_code.isnot(None))
    if source:
        query = query.filter(Timeseries.source.in_(source))
    all_ts = query.order_by(Timeseries.source, Timeseries.code).all()

    if not all_ts:
        raise HTTPException(
            status_code=404, detail="No timeseries with source_code found."
        )

    # Group by source
    grouped: Dict[str, list] = {}
    for ts in all_ts:
        src = ts.source or "Unknown"
        grouped.setdefault(src, []).append(ts)

    buffer = generate_download_template_workbook(grouped, start_dt, end_dt)

    filename = f"timeseries_template_{end_dt.strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/timeseries/upload_template_data")
@_limiter.limit("10/minute")
async def upload_template_data(
    request: Request,
    file: UploadFile = File(...),
    _current_user: User = Depends(get_current_admin_user),
):
    """Upload filled Excel template and merge into local DB."""
    import asyncio

    contents = await file.read()
    if len(contents) > 200 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File exceeds 200MB size limit")

    try:
        result = await asyncio.to_thread(process_template_upload, contents)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


class _UploadDataJSON(BaseModel):
    """JSON payload for direct data upload from Excel add-in."""
    data: Dict[str, Dict[str, float]]  # {code: {date_str: value}}


@router.post("/timeseries/upload_data")
@_limiter.limit("10/minute")
def upload_data_json(
    request: Request,
    payload: _UploadDataJSON,
    _current_user: User = Depends(get_current_admin_user),
    db: SessionType = Depends(get_db),
):
    """Merge timeseries data from JSON (Excel add-in).

    Accepts ``{data: {code: {date: value, ...}, ...}}``.
    """
    from ix.core.ts.bulk_upload import merge_columnar_to_db

    if not payload.data:
        raise HTTPException(status_code=400, detail="No data provided")

    # Build a date-indexed DataFrame from the nested dict
    frames = {}
    for code, date_vals in payload.data.items():
        if not date_vals:
            continue
        s = pd.Series(date_vals, dtype=float)
        s.index = pd.to_datetime(s.index, errors="coerce")
        s = s.dropna()
        if not s.empty:
            frames[code] = s

    if not frames:
        raise HTTPException(status_code=400, detail="No valid data points found")

    df = pd.DataFrame(frames)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()

    result = merge_columnar_to_db(df, db)
    return {
        "message": f"Merged {result['points']} points for {len(result['updated'])} codes.",
        "db_updated": result["updated"],
        "db_points_merged": result["points"],
        "warning": f"Codes not found: {result['not_found']}" if result["not_found"] else None,
    }


# ────────────────────────────────────────────────────────────────────
# CRUD: create / update / delete / get
# ────────────────────────────────────────────────────────────────────


@router.post("/timeseries")
@_limiter.limit("10/minute")
def create_or_update_timeseries_bulk(
    request: Request,
    payload: List[TimeseriesCreate],
    db: SessionType = Depends(get_db),
    _current_user: User = Depends(get_current_admin_user),
):
    """
    POST /api/timeseries - Create new or update existing timeseries metadata (bulk).

    Request body: List of timeseries objects. Each object can have:
    - id: Optional UUID string to update existing timeseries by ID
    - code: Required for new timeseries, optional if id is provided
    - Other fields: name, provider, asset_class, category, etc.

    Update logic:
    1. If 'id' is provided, find by ID first
    2. If not found by ID and 'code' is provided, find by code
    3. If not found, create new (requires 'code')
    """
    ensure_connection()

    if not payload:
        raise HTTPException(status_code=400, detail="Empty payload provided.")

    updated_codes = []
    created_codes = []
    errors = []

    # Pre-fetch existing timeseries
    payload_ids = [str(ts.id) for ts in payload if ts.id]
    payload_codes = [ts.code for ts in payload if ts.code]

    existing_by_id = {}
    if payload_ids:
        for ts in db.query(Timeseries).filter(Timeseries.id.in_(payload_ids)).all():
            existing_by_id[str(ts.id)] = ts

    existing_by_code = {}
    if payload_codes:
        for ts in db.query(Timeseries).filter(Timeseries.code.in_(payload_codes)).all():
            existing_by_code[str(ts.code)] = ts

    for ts_data in payload:
        try:
            ts = None

            # If ID is provided, try to find by ID first
            if ts_data.id:
                ts = existing_by_id.get(str(ts_data.id))
                if ts:
                    updated_codes.append(ts.code if ts.code else str(ts_data.id))

            # If not found by ID, try to find by code
            if ts is None and ts_data.code:
                ts = existing_by_code.get(str(ts_data.code))
                if ts:
                    updated_codes.append(ts_data.code)

            # If still not found, create new (requires code)
            if ts is None:
                if not ts_data.code:
                    errors.append(
                        "Either 'id' or 'code' is required to create/update timeseries"
                    )
                    continue
                # Normalize code: append :PX_LAST if no field suffix
                new_code = ts_data.code
                if ":" not in new_code:
                    new_code = f"{new_code}:PX_LAST"
                # Create new timeseries
                ts = Timeseries(code=new_code)
                db.add(ts)
                existing_by_code[str(new_code)] = (
                    ts  # Register for subsequent lookups
                )
                created_codes.append(new_code)

            # Update fields using canonical helper (exclude_unset avoids
            # overwriting with Pydantic defaults like scale=1, favorite=False)
            apply_timeseries_updates(ts, ts_data.model_dump(exclude_unset=True))

            # We use a nested transaction (SAVEPOINT) to safely catch individual loop errors
            # without breaking the entire batch transaction.
            try:
                with db.begin_nested():
                    db.flush()
            except Exception as nested_e:
                raise nested_e

        except Exception as e:
            identifier = ts_data.id or ts_data.code or "unknown"
            logger.error("Error updating timeseries %s: %s", identifier, e)
            errors.append(f"Error updating {identifier}: {str(e)}")
            continue

    try:
        db.commit()
    except Exception as e:
        logger.error("Error committing bulk update: %s", e)
        db.rollback()
        errors.append(f"Transaction failed: {str(e)}")

    response = {
        "message": f"Successfully processed {len(payload)} timeseries objects.",
        "created_codes": created_codes,
        "created_count": len(created_codes),
        "updated_codes": updated_codes,
        "updated_count": len(updated_codes),
    }

    if errors:
        response["errors"] = errors
        response["error_count"] = len(errors)

    return response


@router.put("/timeseries/{code}", response_model=TimeseriesResponse)
@_limiter.limit("30/minute")
def update_timeseries(
    request: Request,
    code: str,
    payload: TimeseriesUpdate,
    db: SessionType = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    """
    PUT /api/timeseries/{code} - Update a single timeseries metadata entry.

    This endpoint follows REST best practices by using PUT for updates.
    Only provided fields are updated (no payload -> 400).
    """
    ensure_connection()

    ts = db.query(Timeseries).filter(Timeseries.code == code).first()
    if not ts:
        raise HTTPException(
            status_code=404, detail=f"Timeseries with code '{code}' not found"
        )

    update_fields = payload.model_dump(exclude_unset=True)
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields provided to update.")

    try:
        # Apply changes
        try:
            apply_timeseries_updates(ts, update_fields)
        except (TypeError, ValueError):
            raise HTTPException(
                status_code=400, detail="Invalid field type in payload."
            )

        ts.updated = datetime.now()
        db.commit()
        db.refresh(ts)

        return TimeseriesResponse(
            id=str(ts.id),
            code=ts.code,
            name=ts.name,
            provider=ts.provider,
            asset_class=ts.asset_class,
            category=ts.category,
            start=ts.start,
            end=ts.end,
            num_data=ts.num_data,
            source=ts.source,
            source_code=getattr(ts, "source_code", None),
            frequency=ts.frequency,
            unit=getattr(ts, "unit", None),
            scale=getattr(ts, "scale", None),
            currency=getattr(ts, "currency", None),
            country=getattr(ts, "country", None),
            remark=getattr(ts, "remark", None),
            favorite=getattr(ts, "favorite", False),
        )
    except HTTPException:
        # Already constructed, just re-raise
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error("Failed to update timeseries %s: %s", code, e)
        raise HTTPException(
            status_code=500, detail=f"Failed to update timeseries '{code}'"
        )


@router.post("/timeseries/{code}", response_model=TimeseriesResponse, status_code=201)
@_limiter.limit("10/minute")
def create_timeseries(
    request: Request,
    code: str,
    payload: TimeseriesCreate,
    db: SessionType = Depends(get_db),
    _current_user: User = Depends(get_current_admin_user),
):
    """
    POST /api/timeseries/{code} - Create a single timeseries metadata entry.

    - Returns 409 if the code already exists.
    - Body fields mirror the bulk create schema; path code overrides body code.
    """
    ensure_connection()

    # Normalize code: append :PX_LAST if no field suffix
    if ":" not in code:
        code = f"{code}:PX_LAST"

    # Validate existence
    existing = db.query(Timeseries).filter(Timeseries.code == code).first()
    if existing:
        raise HTTPException(
            status_code=409, detail=f"Timeseries with code '{code}' already exists"
        )

    # Build data from payload with path code taking precedence
    create_data = payload.model_dump(exclude_unset=True)
    create_data["code"] = code  # enforce path code

    try:
        ts = Timeseries(code=code)
        apply_timeseries_updates(ts, create_data)
        ts.created = datetime.now()
        ts.updated = datetime.now()

        db.add(ts)
        db.commit()
        db.refresh(ts)

        return TimeseriesResponse(
            id=str(ts.id),
            code=ts.code,
            name=ts.name,
            provider=ts.provider,
            asset_class=ts.asset_class,
            category=ts.category,
            start=ts.start,
            end=ts.end,
            num_data=ts.num_data,
            source=ts.source,
            source_code=getattr(ts, "source_code", None),
            frequency=ts.frequency,
            unit=getattr(ts, "unit", None),
            scale=getattr(ts, "scale", None),
            currency=getattr(ts, "currency", None),
            country=getattr(ts, "country", None),
            remark=getattr(ts, "remark", None),
            favorite=getattr(ts, "favorite", False),
        )
    except Exception as e:
        db.rollback()
        logger.error("Failed to create timeseries %s: %s", code, e)
        raise HTTPException(
            status_code=500, detail=f"Failed to create timeseries '{code}'"
        )


@router.delete("/timeseries/{code}", status_code=status.HTTP_204_NO_CONTENT)
@_limiter.limit("10/minute")
def delete_timeseries(
    request: Request,
    code: str,
    db: SessionType = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """
    DELETE /api/timeseries/{code} - Delete a timeseries by code.

    Admin-only endpoint.
    """
    ensure_connection()

    ts = db.query(Timeseries).filter(Timeseries.code == code).first()
    if not ts:
        raise HTTPException(
            status_code=404, detail=f"Timeseries with code '{code}' not found"
        )

    try:
        ts.is_deleted = True
        ts.deleted_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("Admin %s soft-deleted timeseries: %s", current_user.email, code)
        return
    except Exception as e:
        db.rollback()
        logger.error("Failed to delete timeseries %s: %s", code, e)
        raise HTTPException(
            status_code=500, detail=f"Failed to delete timeseries '{code}'"
        )


@router.get("/timeseries/{timeseries_id}", response_model=TimeseriesResponse)
def get_timeseries_by_id(
    timeseries_id: str,
    db: SessionType = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """
    GET /api/timeseries/{id} - Get detailed timeseries information by ID (code) with full data.
    """
    ensure_connection()

    ts = db.query(Timeseries).filter(Timeseries.code == timeseries_id).first()

    if not ts:
        raise HTTPException(status_code=404, detail="Timeseries not found")

    return TimeseriesResponse(
        id=str(ts.id),
        code=ts.code,
        name=ts.name,
        provider=ts.provider,
        asset_class=ts.asset_class,
        category=ts.category,
        start=ts.start,
        end=ts.end,
        num_data=ts.num_data,
        source=ts.source,
        source_code=getattr(ts, "source_code", None),
        frequency=ts.frequency,
        unit=getattr(ts, "unit", None),
        scale=getattr(ts, "scale", None),
        currency=getattr(ts, "currency", None),
        country=getattr(ts, "country", None),
        remark=getattr(ts, "remark", None),
        favorite=getattr(ts, "favorite", False),
    )


@router.get("/timeseries/code/{code}", response_model=TimeseriesResponse)
def get_timeseries_by_code(
    code: str,
    db: SessionType = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """
    GET /api/timeseries/code/{code} - Get timeseries by its code.
    """
    ensure_connection()

    ts = db.query(Timeseries).filter(Timeseries.code == code).first()

    if not ts:
        raise HTTPException(
            status_code=404, detail=f"Timeseries with code '{code}' not found"
        )

    return TimeseriesResponse(
        id=str(ts.id),
        code=ts.code,
        name=ts.name,
        provider=ts.provider,
        asset_class=ts.asset_class,
        category=ts.category,
        start=ts.start,
        end=ts.end,
        num_data=ts.num_data,
        source=ts.source,
        source_code=getattr(ts, "source_code", None),
        frequency=ts.frequency,
        unit=getattr(ts, "unit", None),
        scale=getattr(ts, "scale", None),
        currency=getattr(ts, "currency", None),
        country=getattr(ts, "country", None),
        remark=getattr(ts, "remark", None),
        favorite=getattr(ts, "favorite", False),
    )


# ────────────────────────────────────────────────────────────────────
# Favorites
# ────────────────────────────────────────────────────────────────────


@router.get("/timeseries/favorites")
def get_favorite_timeseries_data(
    start_date: Optional[str] = Query(None, description="Start date (ISO-8601)"),
    end_date: Optional[str] = Query(None, description="End date (ISO-8601)"),
    db: SessionType = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """
    GET /api/timeseries/favorites - Get all favorite timeseries data as a concatenated DataFrame.

    Returns column-oriented JSON format with dates sorted descending.
    """
    ensure_connection()

    try:
        favorite_timeseries = (
            db.query(Timeseries)
            .filter(Timeseries.favorite == True)
            .all()
        )

        if not favorite_timeseries:
            return Response(
                content=json.dumps({"Date": []}, ensure_ascii=False),
                media_type="application/json",
            )

        # Collect all series data
        series_list = []
        for ts in favorite_timeseries:
            try:
                ts_data = process_database_timeseries(ts, db)
                if ts_data is not None:
                    series_list.append(ts_data)
            except Exception as e:
                logger.warning("Error processing favorite timeseries %s: %s", ts.code, e)
                continue

        column_dict = format_favorites_dataframe(series_list, start_date, end_date)
        return Response(
            content=json.dumps(column_dict, ensure_ascii=False),
            media_type="application/json",
        )

    except Exception as e:
        logger.exception("Error retrieving favorite timeseries: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


# ────────────────────────────────────────────────────────────────────
# Custom timeseries (expression evaluation)
# ────────────────────────────────────────────────────────────────────


async def _parse_codes_from_request(request: Request) -> List[str]:
    """Parse codes from request body, query parameters, or X-Codes header."""
    codes = []

    # Try to get from request body (works for POST, and GET with body in some clients)
    try:
        body = await request.json()
        if isinstance(body, list):
            codes = [str(c).strip() for c in body if str(c).strip()]
        elif isinstance(body, dict) and body:
            raw_codes = body.get("codes")
            if isinstance(raw_codes, list):
                codes = [str(c).strip() for c in raw_codes if str(c).strip()]
            elif isinstance(raw_codes, str):
                codes = [c.strip() for c in raw_codes.split(",") if c.strip()]
    except Exception:
        pass

    # Fallback to query parameters (for GET requests)
    if not codes:
        query_codes = request.query_params.get("codes")
        if query_codes:
            codes = [c.strip() for c in query_codes.split(",") if c.strip()]

    # Fallback to header if body and query didn't work
    if not codes:
        header_codes = request.headers.get("X-Codes")
        if header_codes:
            # Try to parse as JSON first (handles codes with commas and special chars)
            try:
                parsed = json.loads(header_codes)
                if isinstance(parsed, list):
                    codes = [str(c).strip() for c in parsed if str(c).strip()]
                    logger.debug(
                        f"Parsed {len(codes)} codes from JSON array in X-Codes header"
                    )
                elif isinstance(parsed, dict) and "codes" in parsed:
                    codes_list = parsed["codes"]
                    if isinstance(codes_list, list):
                        codes = [str(c).strip() for c in codes_list if str(c).strip()]
                        logger.debug(
                            f"Parsed {len(codes)} codes from JSON dict in X-Codes header"
                        )
                    elif isinstance(codes_list, str):
                        codes = [c.strip() for c in codes_list.split(",") if c.strip()]
                        logger.warning(
                            "X-Codes header contains dict with string 'codes' - using comma-split (may break)"
                        )
                else:
                    logger.warning(
                        f"X-Codes JSON parsed but unexpected format: {type(parsed)}"
                    )
            except (json.JSONDecodeError, ValueError) as e:
                # Check if header looks like it might contain complex expressions with commas
                has_complex_expressions = any(
                    char in header_codes
                    for char in [
                        "(",
                        ")",
                        "{",
                        "}",
                        '"',
                        "'",
                        "Series(",
                        "MultiSeries(",
                    ]
                )

                if has_complex_expressions:
                    logger.error(
                        f"X-Codes header contains complex expressions but is not valid JSON. "
                        f'Please send codes as JSON array: ["code1", "code2"]. '
                        f"Error: {e}. Header preview: {header_codes[:200]}..."
                    )
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "X-Codes header must be a JSON array when codes contain commas or special characters. "
                            'Example: X-Codes: ["CODE1", "Series(\'CODE2\').pct_change()"]'
                        ),
                    )

                # Fallback to comma-separated for simple codes only
                logger.warning(
                    f"X-Codes header is not valid JSON (falling back to comma-separated): {e}. "
                    f"Header value starts with: {header_codes[:100]}..."
                )
                codes = [c.strip() for c in header_codes.split(",") if c.strip()]

    if not codes:
        raise HTTPException(
            status_code=400,
            detail="No codes provided. Provide JSON body with 'codes' list, 'codes' query parameter, or 'X-Codes' header.",
        )

    # Filter out reserved column names
    RESERVED_NAMES = {"Date", "date"}  # Reserved for index column
    codes = [c for c in codes if c not in RESERVED_NAMES]

    if not codes:
        raise HTTPException(
            status_code=400,
            detail="No valid codes provided after filtering reserved names.",
        )

    # Deduplicate while preserving order
    seen_codes = set()
    unique_codes = []
    for code in codes:
        if code not in seen_codes:
            unique_codes.append(code)
            seen_codes.add(code)

    return unique_codes


@router.get("/timeseries.custom")
@router.post("/timeseries.custom")
@_limiter.limit("60/minute")
async def get_custom_timeseries_data(
    request: Request,
    start_date: Optional[str] = Query(None, description="Start date (ISO-8601)"),
    end_date: Optional[str] = Query(None, description="End date (ISO-8601)"),
    db: SessionType = Depends(get_db),
    _current_user: Optional[User] = Depends(get_optional_user),
):
    """
    GET/POST /api/timeseries.custom - Get selected timeseries data based on provided codes.

    Accepts JSON body (not in URL):
    { "codes": ["CODE1", "CODE2", ...] }
    or
    { "codes": "CODE1, CODE2, ..." }

    Also accepts X-Codes header:
    - JSON format (recommended for codes with commas): X-Codes: ["CODE1", "CODE2, WITH COMMA", "CODE3"]
    - Comma-separated (legacy, breaks if codes contain commas): X-Codes: CODE1, CODE2, CODE3

    Behavior:
    - Queries each code one by one from the Timeseries table
    - If code is found in database, uses stored data
    - If code is NOT found, attempts to evaluate it as a Python expression (e.g., Series('CODE'))
    - Supports mixing database timeseries with dynamically computed series

    Examples:
    - ["AAPL", "MSFT"] - database codes
    - ["AAPL", "Series('SPY')"] - mix of database and expression
    - ["Series('AAPL').pct_change()"] - pure expression

    Note: For codes containing commas or special characters, use JSON body or JSON in X-Codes header.

    Returns column-oriented format with dates sorted descending.
    """
    ensure_connection()

    try:
        codes = await _parse_codes_from_request(request)
        logger.debug("Processing %d codes: %s", len(codes), codes)

        def _process_all_codes_sync():
            series_list = []

            # Batch-fetch all codes in one query instead of N sequential queries
            all_ts = (
                db.query(Timeseries)
                .options(joinedload(Timeseries.data_record))
                .filter(Timeseries.code.in_(codes))
                .all()
            )
            found = {ts.code: ts for ts in all_ts}

            for code in codes:
                try:
                    ts = found.get(code)
                    if ts:
                        ts_data = process_database_timeseries(ts, db)
                        if ts_data is not None:
                            series_list.append(ts_data)
                    else:
                        evaluated_series = evaluate_expression(
                            code, start_date, end_date
                        )
                        series_list.extend(evaluated_series)
                except Exception as e:
                    logger.warning("Error processing custom timeseries %s: %s", code, e)
                    continue

            if series_list:
                df = pd.concat(series_list, axis=1)
                column_dict = format_dataframe_to_column_dict(
                    df, series_list, start_date, end_date
                )
                return Response(
                    content=json.dumps(column_dict, ensure_ascii=False),
                    media_type="application/json",
                    headers={"Cache-Control": "private, max-age=60"},
                )
            else:
                return Response(
                    content=json.dumps({"Date": []}, ensure_ascii=False),
                    media_type="application/json",
                )

        import asyncio

        return await asyncio.to_thread(_process_all_codes_sync)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error retrieving custom timeseries: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/timeseries.exec")
@_limiter.limit("20/minute")
async def exec_code_block(
    request: Request,
    _current_user: Optional[User] = Depends(get_optional_user),
):
    """
    POST /api/timeseries.exec -- Execute a multi-line code block that produces
    a DataFrame or Series.  The code must assign its output to ``result``.

    Body: ``{ "code": "..." }``

    Example:
        code = '''
        spy = Series("SPY US EQUITY:PX_LAST")
        qqq = Series("QQQ US EQUITY:PX_LAST")
        result = pd.concat([spy, qqq], axis=1)
        '''

    Returns column-oriented JSON ``{ "Date": [...], "col1": [...], ... }``.
    """
    try:
        body = await request.json()
        code = body.get("code", "")
        if not code or not code.strip():
            raise HTTPException(status_code=400, detail="Empty code block")

        import asyncio

        result = await asyncio.to_thread(execute_code_block, code)
        return result

    except UnsafeExpressionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error executing code block: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# ────────────────────────────────────────────────────────────────────
# Market.xlsm Download
# ────────────────────────────────────────────────────────────────────
import pathlib as _pathlib

_MARKET_FILE = _pathlib.Path(__file__).resolve().parents[4] / "Market.xlsm"
_XLAM_FILE = _pathlib.Path(__file__).resolve().parents[4] / "scripts" / "office" / "InvestmentX.xlam"


@router.get("/download/market")
def download_market_file(
    _current_user: User = Depends(get_current_user),
):
    """Download Market.xlsm Excel macro workbook."""
    if not _MARKET_FILE.is_file():
        raise HTTPException(status_code=404, detail="Market.xlsm not found on server")
    resp = FileResponse(
        path=str(_MARKET_FILE),
        media_type="application/vnd.ms-excel.sheet.macroEnabled.12",
        filename="Market.xlsm",
    )
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp


@router.get("/download/addin")
def download_excel_addin(
    _current_user: User = Depends(get_current_user),
):
    """Download InvestmentX.xlam Excel add-in."""
    if not _XLAM_FILE.is_file():
        raise HTTPException(status_code=404, detail="InvestmentX.xlam not found on server")
    resp = FileResponse(
        path=str(_XLAM_FILE),
        media_type="application/vnd.ms-excel.addin.macroEnabled.12",
        filename="InvestmentX.xlam",
    )
    resp.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return resp


# ────────────────────────────────────────────────────────────────────
# Data upload endpoints
# ────────────────────────────────────────────────────────────────────


@router.post("/upload_data")
@_limiter.limit("10/minute")
def upload_data(
    request: Request,
    payload: TimeseriesDataUpload,
    db: SessionType = Depends(get_db),
    _current_user: User = Depends(get_current_admin_user),
):
    """POST /api/upload_data - Upload timeseries data and merge into local DB."""
    if not payload.data:
        raise HTTPException(status_code=400, detail="No data provided")

    records = [{"date": d.date, "code": d.code, "value": d.value} for d in payload.data]

    ensure_connection()
    df = pd.DataFrame(records)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["value", "date", "code"])
    if df.empty:
        raise HTTPException(status_code=400, detail="No valid records after cleaning.")

    pivoted = df.pivot(index="date", columns="code", values="value").sort_index()
    pivoted = pivoted.dropna(how="all", axis=1).dropna(how="all", axis=0)
    pivoted.index = pd.to_datetime(pivoted.index)

    result = merge_columnar_to_db(pivoted, db)
    response = {"message": f"Merged {result['points']} points for {len(result['updated'])} codes.", "db_updated": result["updated"], "db_points_merged": result["points"]}
    if result["not_found"]:
        response["warning"] = f"Codes not found in database: {result['not_found']}"

    return response


@router.post("/upload_data_columnar")
@_limiter.limit("10/minute")
def upload_data_columnar(
    request: Request,
    payload: TimeseriesColumnarUpload,
    db: SessionType = Depends(get_db),
    _current_user: User = Depends(get_current_admin_user),
):
    """POST /api/upload_data_columnar - Upload columnar timeseries data and merge into local DB."""
    if not payload.dates or not payload.columns:
        raise HTTPException(status_code=400, detail="No data provided")

    ensure_connection()
    dates_index = pd.to_datetime(payload.dates, errors="coerce")
    df = pd.DataFrame(payload.columns, index=dates_index)
    df = df.dropna(how="all", axis=0).dropna(how="all", axis=1)
    if df.empty:
        raise HTTPException(status_code=400, detail="No valid records after cleaning.")

    result = merge_columnar_to_db(df, db)
    response = {"message": f"Merged {result['points']} points for {len(result['updated'])} codes.", "db_updated": result["updated"], "db_points_merged": result["points"]}
    if result["not_found"]:
        response["warning"] = f"Codes not found in database: {result['not_found']}"

    return response
