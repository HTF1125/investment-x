from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, load_only, selectinload

from ix.api.dependencies import get_current_user, get_db
from ix.db.models import InvestmentNote, InvestmentNoteImage, User

router = APIRouter()

MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB


class InvestmentNoteCreate(BaseModel):
    title: str = "Untitled Note"
    content: str = ""
    links: List[str] = Field(default_factory=list)
    pinned: bool = False


class InvestmentNoteUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    links: Optional[List[str]] = None
    pinned: Optional[bool] = None


class NoteImageMeta(BaseModel):
    id: str
    filename: Optional[str] = None
    content_type: str
    created_at: datetime
    url: str

    class Config:
        from_attributes = True


class InvestmentNoteSummary(BaseModel):
    id: str
    title: str
    links: List[str] = Field(default_factory=list)
    pinned: bool
    image_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InvestmentNoteResponse(BaseModel):
    id: str
    user_id: str
    title: str
    content: str
    links: List[str] = Field(default_factory=list)
    pinned: bool
    created_at: datetime
    updated_at: datetime
    images: List[NoteImageMeta] = Field(default_factory=list)

    class Config:
        from_attributes = True


def _normalize_links(links: Optional[List[str]]) -> List[str]:
    if not links:
        return []
    cleaned: List[str] = []
    seen = set()
    for raw in links:
        item = str(raw or "").strip()
        if not item:
            continue
        if item.startswith("chart://"):
            continue
        if "://" not in item and "." in item and " " not in item:
            item = f"https://{item}"
        if item in seen:
            continue
        seen.add(item)
        cleaned.append(item[:2000])
        if len(cleaned) >= 40:
            break
    return cleaned


def _note_to_response(note: InvestmentNote) -> InvestmentNoteResponse:
    images = sorted(note.images or [], key=lambda img: img.created_at or datetime.min)
    return InvestmentNoteResponse(
        id=str(note.id),
        user_id=str(note.user_id),
        title=note.title or "Untitled Note",
        content=note.content or "",
        links=list(note.links or []),
        pinned=bool(note.pinned),
        created_at=note.created_at,
        updated_at=note.updated_at,
        images=[
            NoteImageMeta(
                id=str(img.id),
                filename=img.filename,
                content_type=img.content_type or "image/png",
                created_at=img.created_at,
                url=f"/api/notes/images/{img.id}",
            )
            for img in images
        ],
    )


def _assert_note_owner(note: InvestmentNote, user: User) -> None:
    if str(note.user_id) != str(user.id):
        raise HTTPException(status_code=404, detail="Note not found.")


def _get_owned_note(db: Session, note_id: str, user: User, with_images: bool = False) -> InvestmentNote:
    query = db.query(InvestmentNote).filter(InvestmentNote.id == note_id)
    if with_images:
        # Avoid loading large binary blobs when only image metadata is needed.
        query = query.options(
            selectinload(InvestmentNote.images).load_only(
                InvestmentNoteImage.id,
                InvestmentNoteImage.note_id,
                InvestmentNoteImage.filename,
                InvestmentNoteImage.content_type,
                InvestmentNoteImage.created_at,
            )
        )
    note = query.first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found.")
    _assert_note_owner(note, user)
    return note


@router.get("/notes", response_model=List[InvestmentNoteSummary])
def list_notes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    image_counts = (
        db.query(
            InvestmentNoteImage.note_id.label("note_id"),
            func.count(InvestmentNoteImage.id).label("image_count"),
        )
        .filter(InvestmentNoteImage.user_id == str(current_user.id))
        .group_by(InvestmentNoteImage.note_id)
        .subquery()
    )
    notes = (
        db.query(
            InvestmentNote.id.label("id"),
            InvestmentNote.title.label("title"),
            InvestmentNote.links.label("links"),
            InvestmentNote.pinned.label("pinned"),
            InvestmentNote.created_at.label("created_at"),
            InvestmentNote.updated_at.label("updated_at"),
            func.coalesce(image_counts.c.image_count, 0).label("image_count"),
        )
        .outerjoin(image_counts, image_counts.c.note_id == InvestmentNote.id)
        .filter(InvestmentNote.user_id == str(current_user.id))
        .order_by(InvestmentNote.pinned.desc(), InvestmentNote.updated_at.desc())
        .all()
    )
    return [
        InvestmentNoteSummary(
            id=str(note.id),
            title=note.title or "Untitled Note",
            links=list(note.links or []),
            pinned=bool(note.pinned),
            image_count=int(note.image_count or 0),
            created_at=note.created_at,
            updated_at=note.updated_at,
        )
        for note in notes
    ]


@router.get("/notes/{note_id}", response_model=InvestmentNoteResponse)
def get_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = _get_owned_note(db, note_id, current_user, with_images=True)
    return _note_to_response(note)


@router.post("/notes", response_model=InvestmentNoteResponse, status_code=201)
def create_note(
    payload: InvestmentNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = InvestmentNote(
        user_id=str(current_user.id),
        title=(payload.title or "Untitled Note").strip()[:255] or "Untitled Note",
        content=payload.content or "",
        links=_normalize_links(payload.links),
        pinned=bool(payload.pinned),
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return _note_to_response(note)


@router.put("/notes/{note_id}", response_model=InvestmentNoteResponse)
def update_note(
    note_id: str,
    payload: InvestmentNoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = _get_owned_note(db, note_id, current_user, with_images=True)
    if payload.title is not None:
        note.title = payload.title.strip()[:255] or "Untitled Note"
    if payload.content is not None:
        note.content = payload.content
    if payload.links is not None:
        note.links = _normalize_links(payload.links)
    if payload.pinned is not None:
        note.pinned = bool(payload.pinned)
    note.updated_at = datetime.utcnow()

    db.add(note)
    db.commit()
    db.refresh(note)
    return _note_to_response(note)


@router.delete("/notes/{note_id}", status_code=204)
def delete_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = _get_owned_note(db, note_id, current_user, with_images=False)
    db.delete(note)
    db.commit()
    return Response(status_code=204)


@router.post("/notes/{note_id}/images", response_model=NoteImageMeta, status_code=201)
async def upload_note_image(
    note_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = _get_owned_note(db, note_id, current_user, with_images=False)

    content_type = str(file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed.")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Image exceeds 8MB size limit.")

    image = InvestmentNoteImage(
        note_id=str(note.id),
        user_id=str(current_user.id),
        filename=(file.filename or "note-image")[:255],
        content_type=content_type[:128],
        data=data,
    )
    note.updated_at = datetime.utcnow()
    db.add(image)
    db.add(note)
    db.commit()
    db.refresh(image)

    return NoteImageMeta(
        id=str(image.id),
        filename=image.filename,
        content_type=image.content_type,
        created_at=image.created_at,
        url=f"/api/notes/images/{image.id}",
    )


@router.delete("/notes/images/{image_id}", status_code=204)
def delete_note_image(
    image_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    image = (
        db.query(InvestmentNoteImage)
        .options(
            load_only(
                InvestmentNoteImage.id,
                InvestmentNoteImage.user_id,
                InvestmentNoteImage.note_id,
            ),
            selectinload(InvestmentNoteImage.note).load_only(
                InvestmentNote.id,
                InvestmentNote.updated_at,
            ),
        )
        .filter(InvestmentNoteImage.id == image_id)
        .first()
    )
    if not image:
        raise HTTPException(status_code=404, detail="Image not found.")
    if str(image.user_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="Image not found.")

    note = image.note
    if note is not None:
        note.updated_at = datetime.utcnow()
        db.add(note)
    db.delete(image)
    db.commit()
    return Response(status_code=204)


@router.get("/notes/images/{image_id}")
def get_note_image(
    image_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    image = (
        db.query(InvestmentNoteImage)
        .filter(InvestmentNoteImage.id == image_id)
        .first()
    )
    if not image or str(image.user_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="Image not found.")

    safe_name = (image.filename or "note-image").replace('"', "")
    return StreamingResponse(
        BytesIO(image.data),
        media_type=image.content_type or "image/png",
        headers={
            "Content-Disposition": f'inline; filename="{safe_name}"',
            "Cache-Control": "private, max-age=604800",
        },
    )
