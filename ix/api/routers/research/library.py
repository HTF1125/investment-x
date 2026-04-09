"""Research library — upload / list / serve / delete institutional research PDFs (DB-backed)."""

import hashlib
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session, defer

from ix.api.dependencies import get_current_admin_user, get_current_user, get_optional_user
from ix.db.conn import get_session as get_db
from ix.db.models import ResearchFile
from ix.db.models.user import User
from ix.common import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/research/library", tags=["Research Library"])

_limiter = Limiter(key_func=get_remote_address)


# ── Schemas ───────────────────────────────────────────────────────────────────


class LibraryItem(BaseModel):
    id: str
    filename: str
    title: str
    size_bytes: int
    uploaded_by: Optional[str] = None
    created_at: str
    summary: Optional[str] = None


class PaginatedLibrary(BaseModel):
    items: List[LibraryItem]
    total: int


def _to_item(row: ResearchFile) -> dict:
    stem = row.filename
    if stem.lower().endswith(".pdf"):
        stem = stem[:-4]
    return {
        "id": row.id,
        "filename": row.filename,
        "title": stem.replace("_", " "),
        "size_bytes": row.size_bytes,
        "uploaded_by": row.uploaded_by,
        "created_at": row.created_at.isoformat() if row.created_at else "",
        "summary": row.summary,
    }


# ── List ──────────────────────────────────────────────────────────────────────


@router.get("", response_model=PaginatedLibrary)
@_limiter.limit("60/minute")
def list_research(
    request: Request,
    q: Optional[str] = None,
    limit: int = Query(25, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base = db.query(ResearchFile).options(defer(ResearchFile.content)).filter(ResearchFile.is_deleted == False)
    if q:
        pattern = f"%{q}%"
        base = base.filter(ResearchFile.filename.ilike(pattern) | ResearchFile.summary.ilike(pattern))
    total = base.count()
    rows = base.order_by(ResearchFile.filename.desc()).offset(offset).limit(limit).all()
    return {"items": [_to_item(r) for r in rows], "total": total}


# ── Upload ────────────────────────────────────────────────────────────────────


@router.post("/upload", response_model=LibraryItem)
@_limiter.limit("20/minute")
def upload_research(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are accepted")

    content = file.file.read()
    if len(content) > 100 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 100MB)")

    row = ResearchFile(
        filename=file.filename,
        size_bytes=len(content),
        content=content,
        uploaded_by=current_user.email,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    logger.info(f"Research uploaded: {row.filename} ({row.size_bytes} bytes) by {current_user.email}")
    return _to_item(row)


# ── View PDF ──────────────────────────────────────────────────────────────────


@router.get("/view/{file_id}")
@_limiter.limit("60/minute")
def view_research(
    request: Request,
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_optional_user),
):
    row = db.query(ResearchFile).filter(ResearchFile.id == file_id).first()
    if not row:
        raise HTTPException(404, "File not found")
    return Response(
        content=row.content,
        media_type="application/pdf",
        headers={"Content-Disposition": "inline"},
    )


# ── Rename ───────────────────────────────────────────────────────────────


class RenameRequest(BaseModel):
    title: str


@router.patch("/{file_id}")
@_limiter.limit("30/minute")
def rename_research(
    request: Request,
    file_id: str,
    body: RenameRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    row = db.query(ResearchFile).filter(ResearchFile.id == file_id).first()
    if not row:
        raise HTTPException(404, "File not found")
    new_title = body.title.strip()
    if not new_title:
        raise HTTPException(400, "Title cannot be empty")
    old_name = row.filename
    row.filename = new_title if new_title.lower().endswith(".pdf") else new_title + ".pdf"
    db.commit()
    db.refresh(row)
    logger.info(f"Research renamed: {old_name} -> {row.filename} by {current_user.email}")
    return _to_item(row)


# ── Delete ────────────────────────────────────────────────────────────────────


@router.delete("/{file_id}")
@_limiter.limit("20/minute")
def delete_research(
    request: Request,
    file_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    row = db.query(ResearchFile).filter(ResearchFile.id == file_id).first()
    if not row:
        raise HTTPException(404, "File not found")
    name = row.filename
    row.is_deleted = True
    row.deleted_at = datetime.now(timezone.utc)
    db.commit()
    logger.info(f"Research soft-deleted: {name} by {current_user.email}")
    return {"ok": True}
