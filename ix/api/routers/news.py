from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import Optional, Any
from ix.db.conn import get_session
from ix.db.models import TelegramMessage
from ix.db.models.news_item import NewsItem
from ix.db.models.research_report import ResearchReport
from pydantic import BaseModel
from sqlalchemy import func, or_
from ix.api.dependencies import get_current_user
from ix.db.models.user import User

router = APIRouter()


class TelegramMessageSchema(BaseModel):
    id: str
    channel_name: str
    message_id: int
    date: datetime
    message: str | None
    views: int | None
    created_at: datetime

    class Config:
        from_attributes = True


class UnifiedNewsItemSchema(BaseModel):
    id: str
    source: str
    source_name: Optional[str] = None
    source_item_id: Optional[str] = None
    url: Optional[str] = None
    title: str
    summary: Optional[str] = None
    published_at: Optional[datetime] = None
    discovered_at: datetime
    symbols: list[str] = []
    meta: dict[str, Any] = {}

    class Config:
        from_attributes = True


class NewsAggregateResponse(BaseModel):
    generated_at: datetime
    telegram_messages: list[TelegramMessageSchema]


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


# ── News Aggregate ────────────────────────────────────────────────

@router.get("/news", response_model=NewsAggregateResponse)
def get_news_aggregate(db: Session = Depends(get_session)):
    """Unified news endpoint: Telegram messages from last 7 days."""
    telegram_cutoff = _now_utc() - timedelta(days=7)

    telegram_messages = (
        db.query(TelegramMessage)
        .filter(TelegramMessage.date >= telegram_cutoff)
        .order_by(TelegramMessage.date.desc())
        .limit(300)
        .all()
    )

    return NewsAggregateResponse(
        generated_at=_now_utc(),
        telegram_messages=[TelegramMessageSchema.model_validate(m) for m in telegram_messages],
    )


# ── Unified News Items ───────────────────────────────────────────

@router.get("/news/items", response_model=list[UnifiedNewsItemSchema])
def get_unified_news_items(
    limit: int = 100,
    source: Optional[str] = None,
    q: Optional[str] = None,
    db: Session = Depends(get_session),
):
    limit = max(1, min(limit, 500))
    query = db.query(NewsItem)
    if source:
        query = query.filter(NewsItem.source == source)
    if q:
        search_text = q.strip()
        ts_query = func.websearch_to_tsquery("english", search_text)
        fts_filter = NewsItem.__table__.c.title.op("@@")(ts_query) | \
                     NewsItem.__table__.c.summary.op("@@")(ts_query)

        fts_rows = query.filter(fts_filter).limit(limit).all()
        if fts_rows:
            return [UnifiedNewsItemSchema.model_validate(r) for r in fts_rows]

        pattern = f"%{search_text}%"
        query = query.filter(or_(NewsItem.title.ilike(pattern), NewsItem.summary.ilike(pattern)))

    rows = (
        query.order_by(NewsItem.published_at.desc().nullslast(), NewsItem.discovered_at.desc())
        .limit(limit)
        .all()
    )
    return [UnifiedNewsItemSchema.model_validate(r) for r in rows]


# ── Research Reports (from database) ─────────────────────────────

def _is_valid_date(name: str) -> bool:
    if len(name) != 10:
        return False
    try:
        datetime.strptime(name, "%Y-%m-%d")
        return True
    except ValueError:
        return False


@router.get("/news/reports")
def list_research_reports(
    db: Session = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    """List available research report dates from the database."""
    rows = (
        db.query(
            ResearchReport.date,
            ResearchReport.briefing.isnot(None).label("has_briefing"),
            ResearchReport.risk_scorecard.isnot(None).label("has_risk_scorecard"),
            ResearchReport.takeaways.isnot(None).label("has_takeaways"),
            ResearchReport.infographic.isnot(None).label("has_infographic"),
        )
        .order_by(ResearchReport.date.desc())
        .all()
    )
    return [
        {
            "date": r.date.isoformat(),
            "has_briefing": r.has_briefing,
            "has_risk_scorecard": r.has_risk_scorecard,
            "has_takeaways": r.has_takeaways,
            "has_infographic": r.has_infographic,
        }
        for r in rows
    ]


@router.get("/news/reports/{date}")
def get_research_report(
    date: str,
    db: Session = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    """Return the full research report for a given date from the database."""
    if not _is_valid_date(date):
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    report_date = datetime.strptime(date, "%Y-%m-%d").date()
    row = db.query(ResearchReport).filter(ResearchReport.date == report_date).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"No report found for {date}")

    return {
        "date": date,
        "briefing": row.briefing,
        "risk_scorecard": row.risk_scorecard,
        "takeaways": row.takeaways,
        "has_infographic": row.infographic is not None,
        "sources": row.sources or {},
    }


@router.get("/news/reports/{date}/infographic")
def get_research_infographic(
    date: str,
    db: Session = Depends(get_session),
    _current_user: User = Depends(get_current_user),
):
    """Serve the infographic PNG from the database."""
    if not _is_valid_date(date):
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    report_date = datetime.strptime(date, "%Y-%m-%d").date()
    row = (
        db.query(ResearchReport.infographic)
        .filter(ResearchReport.date == report_date)
        .first()
    )
    if not row or not row[0]:
        raise HTTPException(status_code=404, detail=f"No infographic found for {date}")

    return Response(
        content=row[0],
        media_type="image/png",
        headers={"Content-Disposition": f'inline; filename="macro-infographic-{date}.png"'},
    )
