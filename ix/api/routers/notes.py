from __future__ import annotations

import base64
import uuid
from datetime import datetime
from io import BytesIO
from typing import List, Optional, Any, Dict

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from ix.api.dependencies import get_current_user, get_db
from ix.db.models import InvestmentNote, User

router = APIRouter()

MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB

class NoteBlock(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str  # text, image, chart, link
    value: Optional[str] = None  # For text
    data: Optional[str] = None   # Base64 for images
    filename: Optional[str] = None
    content_type: Optional[str] = None
    url: Optional[str] = None    # For links
    chart_id: Optional[str] = None # For charts
    metadata: Dict[str, Any] = Field(default_factory=dict)

class InvestmentNoteCreate(BaseModel):
    title: str = "Untitled Note"
    body: List[Dict[str, Any]] = Field(default_factory=lambda: [{"type": "text", "value": "", "id": str(uuid.uuid4())}])
    pinned: bool = False

class InvestmentNoteUpdate(BaseModel):
    title: Optional[str] = None
    body: Optional[List[Dict[str, Any]]] = None
    pinned: Optional[bool] = None

class InvestmentNoteSummary(BaseModel):
    id: str
    title: str
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
    body: List[Dict[str, Any]]
    pinned: bool
    version: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

def _assert_note_owner(note: InvestmentNote, user: User) -> None:
    if str(note.user_id) != str(user.id):
        raise HTTPException(status_code=404, detail="Note not found.")

def _get_owned_note(db: Session, note_id: str, user: User) -> InvestmentNote:
    note = db.query(InvestmentNote).filter(InvestmentNote.id == note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found.")
    _assert_note_owner(note, user)
    return note

@router.get("/notes", response_model=List[InvestmentNoteSummary])
def list_notes(
    q: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(InvestmentNote).filter(InvestmentNote.user_id == str(current_user.id))
    
    if q:
        search_text = q.strip()
        # Use our new FTS index logic
        ts_query = func.websearch_to_tsquery("english", search_text)
        # Note: SQLAlchemy might need manual text for complex functional indexes
        query = query.filter(
            or_(
                InvestmentNote.title.ilike(f"%{search_text}%"),
                # Fallback to simple containment check for JSONB if FTS is complex to bind here
                InvestmentNote.body.cast(String).ilike(f"%{search_text}%")
            )
        )

    notes = query.order_by(InvestmentNote.pinned.desc(), InvestmentNote.updated_at.desc()).all()
    
    summaries = []
    for note in notes:
        # Calculate image count from blocks
        img_count = sum(1 for block in (note.body or []) if block.get("type") == "image")
        summaries.append(
            InvestmentNoteSummary(
                id=str(note.id),
                title=note.title or "Untitled Note",
                pinned=bool(note.pinned),
                image_count=img_count,
                created_at=note.created_at,
                updated_at=note.updated_at,
            )
        )
    return summaries

@router.get("/notes/{note_id}", response_model=InvestmentNoteResponse)
def get_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = _get_owned_note(db, note_id, current_user)
    return InvestmentNoteResponse.model_validate(note)

@router.post("/notes", response_model=InvestmentNoteResponse, status_code=201)
def create_note(
    payload: InvestmentNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = InvestmentNote(
        user_id=str(current_user.id),
        title=(payload.title or "Untitled Note").strip()[:255] or "Untitled Note",
        body=payload.body,
        pinned=bool(payload.pinned),
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return InvestmentNoteResponse.model_validate(note)

@router.put("/notes/{note_id}", response_model=InvestmentNoteResponse)
def update_note(
    note_id: str,
    payload: InvestmentNoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = _get_owned_note(db, note_id, current_user)
    if payload.title is not None:
        note.title = payload.title.strip()[:255] or "Untitled Note"
    if payload.body is not None:
        note.body = payload.body
    if payload.pinned is not None:
        note.pinned = bool(payload.pinned)
    
    note.version += 1
    note.updated_at = datetime.utcnow()

    db.add(note)
    db.commit()
    db.refresh(note)
    return InvestmentNoteResponse.model_validate(note)

@router.delete("/notes/{note_id}", status_code=204)
def delete_note(
    note_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = _get_owned_note(db, note_id, current_user)
    db.delete(note)
    db.commit()
    return Response(status_code=204)

@router.post("/notes/{note_id}/images", response_model=Dict[str, Any], status_code=201)
async def upload_note_image(
    note_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = _get_owned_note(db, note_id, current_user)

    content_type = str(file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed.")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Image exceeds 8MB size limit.")

    # Convert to Base64 to store inside the JSON block
    base64_data = base64.b64encode(data).decode("utf-8")
    
    image_block = {
        "id": str(uuid.uuid4()),
        "type": "image",
        "data": base64_data,
        "filename": (file.filename or "note-image")[:255],
        "content_type": content_type[:128],
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Append the image block to the body
    current_body = list(note.body or [])
    current_body.append(image_block)
    note.body = current_body
    
    note.updated_at = datetime.utcnow()
    note.version += 1
    db.add(note)
    db.commit()
    
    return {
        "id": image_block["id"],
        "url": f"/api/notes/images/{image_block['id']}"
    }

@router.get("/notes/images/{image_id}")
def get_note_image(
    image_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Find the note containing this image block
    # In a unified table, we search the body JSON for the block ID
    note = db.query(InvestmentNote).filter(
        InvestmentNote.user_id == str(current_user.id),
        InvestmentNote.body.cast(String).contains(image_id)
    ).first()
    
    if not note:
        raise HTTPException(status_code=404, detail="Image not found.")
    
    # Find the specific block in the body
    image_block = next((b for b in note.body if b.get("id") == image_id), None)
    if not image_block or not image_block.get("data"):
        raise HTTPException(status_code=404, detail="Image data not found.")

    image_bytes = base64.b64decode(image_block["data"])
    safe_name = (image_block.get("filename") or "note-image").replace('"', "")
    
    return StreamingResponse(
        BytesIO(image_bytes),
        media_type=image_block.get("content_type") or "image/png",
        headers={
            "Content-Disposition": f'inline; filename="{safe_name}"',
            "Cache-Control": "private, max-age=604800",
        },
    )

@router.delete("/notes/images/{image_id}", status_code=204)
def delete_note_image(
    image_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = db.query(InvestmentNote).filter(
        InvestmentNote.user_id == str(current_user.id),
        InvestmentNote.body.cast(String).contains(image_id)
    ).first()
    
    if not note:
        raise HTTPException(status_code=404, detail="Image not found.")
    
    # Filter out the image block
    new_body = [b for b in note.body if b.get("id") != image_id]
    note.body = new_body
    note.updated_at = datetime.utcnow()
    note.version += 1
    
    db.add(note)
    db.commit()
    return Response(status_code=204)
