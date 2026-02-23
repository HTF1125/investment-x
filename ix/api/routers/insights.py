from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session, defer
from typing import List, Optional
from pydantic import BaseModel
from datetime import date, datetime
import hashlib
from ix.db.conn import get_session
from ix.db.models import Insights
from ix.api.dependencies import get_current_user
from ix.db.models.user import User
from ix.misc import get_logger

logger = get_logger(__name__)
router = APIRouter()


class InsightSchema(BaseModel):
    id: str
    published_date: Optional[date] = None
    issuer: Optional[str] = "Investment-X"
    name: Optional[str]
    status: Optional[str] = "new"
    summary: Optional[str] = ""
    created: datetime

    class Config:
        from_attributes = True


class PaginatedInsights(BaseModel):
    items: List[InsightSchema]
    total: int


@router.get("/insights", response_model=PaginatedInsights)
def list_insights(
    skip: int = 0,
    limit: int = 50,
    q: Optional[str] = None,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Returns a paginated list of research insights stored in the database.
    """
    try:
        from sqlalchemy import or_

        # defer is now imported at top level

        query = db.query(Insights).options(defer(Insights.pdf_content))

        if q:
            search_filter = or_(
                Insights.name.ilike(f"%{q}%"),
                Insights.issuer.ilike(f"%{q}%"),
                Insights.summary.ilike(f"%{q}%"),
            )
            query = query.filter(search_filter)

        query = query.order_by(Insights.published_date.desc(), Insights.created.desc())
        total = query.count()
        results = query.offset(skip).limit(limit).all()
        return {"items": results, "total": total}
    except Exception as e:
        logger.error(f"Error listing insights: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve insights")


@router.post("/insights/upload")
async def upload_insight(
    file: UploadFile = File(...),
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Uploads a PDF and handles duplicates via SHA-256 hashing.
    If the file content is identical, it updates the existing record metadata instead of creating a new one.
    """
    logger.info(f"Processing upload: {file.filename}")
    try:
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="File is empty")

        # 1. Calculate Content Hash to detect duplicates
        file_hash = hashlib.sha256(content).hexdigest()

        # 2. Check for existing duplicate (defer pdf loading for performance)
        existing = (
            db.query(Insights)
            .options(defer(Insights.pdf_content))
            .filter(Insights.hash == file_hash)
            .first()
        )

        # 3. Parse Metadata (Same logic as before)
        filename = file.filename
        base_name = filename.rsplit(".", 1)[0]
        parts = base_name.split("_")

        pub_date = date.today()
        issuer = "Direct Upload"
        name = base_name
        tags_str = ""

        if len(parts) >= 1:
            first_part = parts[0].strip()
            if len(first_part) == 8 and first_part.isdigit():
                try:
                    pub_date = datetime.strptime(first_part, "%Y%m%d").date()
                except:
                    pass

            if len(parts) >= 2:
                issuer = parts[1].replace("-", " ").title()
                remaining = parts[2:]
                if remaining:
                    last_item = remaining[-1].strip()
                    if last_item.startswith("#"):
                        tags_str = last_item
                        name_val = " ".join(remaining[:-1]).replace("-", " ")
                    else:
                        name_val = " ".join(remaining).replace("-", " ")
                    if name_val.strip():
                        name = name_val

        summary_text = (
            f"Tags: {tags_str}"
            if tags_str
            else f"Ingested {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )

        if existing:
            # Update existing record metadata (Upsert)
            logger.info(
                f"Duplicate detected (hash: {file_hash}). Updating existing record {existing.id}."
            )
            existing.published_date = pub_date
            existing.issuer = issuer
            existing.name = name
            existing.summary = summary_text
            db.commit()
            db.refresh(existing)
            return {
                "id": str(existing.id),
                "name": existing.name,
                "status": "updated",
                "duplicate": True,
            }

        # Create new record
        new_insight = Insights(
            published_date=pub_date,
            issuer=issuer,
            name=name,
            summary=summary_text,
            pdf_content=content,
            hash=file_hash,
            status="new",
        )

        db.add(new_insight)
        db.commit()
        db.refresh(new_insight)

        logger.info(f"Successfully saved new insight {new_insight.id}.")
        return {
            "id": str(new_insight.id),
            "name": new_insight.name,
            "status": "success",
        }

    except Exception as e:
        logger.exception(f"Upload failed: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


class InsightUpdate(BaseModel):
    published_date: Optional[date] = None
    issuer: Optional[str] = None
    name: Optional[str] = None
    summary: Optional[str] = None
    status: Optional[str] = None


@router.patch("/insights/{insight_id}", response_model=InsightSchema)
def update_insight(
    insight_id: str,
    data: InsightUpdate,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Updates metadata for an insight. Restricted to admins."""
    try:
        if current_user.effective_role not in User.ADMIN_ROLES:
            raise HTTPException(status_code=403, detail="Admin permissions required")

        insight = (
            db.query(Insights)
            .options(defer(Insights.pdf_content))
            .filter(Insights.id == insight_id)
            .first()
        )
        if not insight:
            raise HTTPException(status_code=404, detail="Insight not found")

        for key, value in data.dict(exclude_unset=True).items():
            setattr(insight, key, value)

        db.commit()
        # Refresh only non-binary attributes to avoid encoding errors and unnecessary data transfer
        db.refresh(
            insight,
            attribute_names=[
                "published_date",
                "issuer",
                "name",
                "summary",
                "status",
                "created",
            ],
        )
        return insight
    except Exception as e:
        logger.exception(f"Update failed for insight {insight_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Backend Error: {str(e)}")


@router.delete("/insights/{insight_id}")
def delete_insight(
    insight_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Deletes an insight from the database. Restricted to admins."""
    if current_user.effective_role not in User.ADMIN_ROLES:
        raise HTTPException(status_code=403, detail="Admin permissions required")

    insight = (
        db.query(Insights)
        .options(defer(Insights.pdf_content))
        .filter(Insights.id == insight_id)
        .first()
    )
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    db.delete(insight)
    db.commit()
    return {"status": "deleted"}


@router.get("/insights/{insight_id}/pdf")
def get_insight_pdf(
    insight_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the raw PDF content for an insight from the database.
    """
    insight = db.query(Insights).filter(Insights.id == insight_id).first()
    if not insight or not insight.pdf_content:
        raise HTTPException(status_code=404, detail="PDF not found")

    from fastapi.responses import Response

    return Response(content=insight.pdf_content, media_type="application/pdf")
