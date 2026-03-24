"""Research library — upload / list / serve / delete institutional research PDFs (DB-backed)."""

import hashlib
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session, defer

from ix.api.dependencies import get_current_admin_user, get_current_user, get_optional_user
from ix.db.conn import get_session as get_db
from ix.db.models import ResearchFile
from ix.db.models.user import User
from ix.misc import get_logger

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
    }


# ── List ──────────────────────────────────────────────────────────────────────


@router.get("", response_model=List[LibraryItem])
@_limiter.limit("60/minute")
def list_research(
    request: Request,
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(ResearchFile).options(defer(ResearchFile.content))
    if q:
        query = query.filter(ResearchFile.filename.ilike(f"%{q}%"))
    rows = query.order_by(ResearchFile.filename.desc()).all()
    return [_to_item(r) for r in rows]


# ── Upload ────────────────────────────────────────────────────────────────────


@router.post("/upload", response_model=LibraryItem)
@_limiter.limit("20/minute")
def upload_research(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
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
    db.delete(row)
    db.commit()
    logger.info(f"Research deleted: {name} by {current_user.email}")
    return {"ok": True}
