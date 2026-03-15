"""
Unified research source API endpoints.

All routes are sync (`def`) with `Depends(get_current_user)` auth.
"""

import json as _json
import re as _re
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from ix.api.dependencies import get_current_user
from ix.api.rate_limit import limiter
from ix.db.conn import get_session
from ix.db.models.research_source import ResearchSource
from ix.db.models.user import User

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────


class SourceListItem(BaseModel):
    id: str
    source_type: str
    source_name: Optional[str] = None
    dedup_key: str
    title: str
    url: Optional[str] = None
    summary: Optional[str] = None
    meta: dict[str, Any] = {}
    symbols: list = []
    topics: list = []
    report_id: Optional[str] = None
    published_at: Optional[datetime] = None
    ingested_at: datetime

    class Config:
        from_attributes = True


class SourceDetail(SourceListItem):
    content_text: Optional[str] = None


class SourceStats(BaseModel):
    total: int
    by_type: dict[str, int]
    date_range: dict[str, Optional[str]]
    latest_ingestion: Optional[datetime] = None


# ── GET /sources ─────────────────────────────────────────────────


@router.get("/sources", response_model=list[SourceListItem])
@limiter.limit("60/minute")
def list_sources(
    request: Request,
    type: Optional[str] = None,
    q: Optional[str] = None,
    topic: Optional[str] = None,
    symbol: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    """List research sources (content_text excluded)."""
    query = db.query(
        ResearchSource.id,
        ResearchSource.source_type,
        ResearchSource.source_name,
        ResearchSource.dedup_key,
        ResearchSource.title,
        ResearchSource.url,
        ResearchSource.summary,
        ResearchSource.meta,
        ResearchSource.symbols,
        ResearchSource.topics,
        ResearchSource.report_id,
        ResearchSource.published_at,
        ResearchSource.ingested_at,
    )

    if type:
        query = query.filter(ResearchSource.source_type == type)

    if q:
        safe_q = _re.sub(r"[*:()!&|<>\\]", " ", q.strip())
        safe_q = " ".join(safe_q.split())
        if safe_q:
            ts_query = func.websearch_to_tsquery("english", safe_q)
            fts_col = text(
                "to_tsvector('english', "
                "coalesce(title, '') || ' ' || "
                "coalesce(content_text, '') || ' ' || "
                "coalesce(summary, ''))"
            )
            fts_rows = (
                query.filter(fts_col.op("@@")(ts_query))
                .order_by(ResearchSource.published_at.desc().nullslast())
                .limit(limit)
                .all()
            )
            if fts_rows:
                return [SourceListItem.model_validate(r) for r in fts_rows]

            # Fallback to ILIKE
            pattern = f"%{safe_q}%"
            query = query.filter(ResearchSource.title.ilike(pattern))

    if topic:
        query = query.filter(
            ResearchSource.topics.op("@>")(_json.dumps([topic]))
        )

    if symbol:
        query = query.filter(
            ResearchSource.symbols.op("@>")(_json.dumps([symbol]))
        )

    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            query = query.filter(ResearchSource.published_at >= since_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid 'since' date format")

    if until:
        try:
            until_dt = datetime.fromisoformat(until)
            query = query.filter(ResearchSource.published_at <= until_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid 'until' date format")

    rows = (
        query.order_by(ResearchSource.published_at.desc().nullslast())
        .limit(limit)
        .all()
    )
    return [SourceListItem.model_validate(r) for r in rows]


# ── GET /sources/stats ───────────────────────────────────────────


@router.get("/sources/stats", response_model=SourceStats)
@limiter.limit("30/minute")
def get_source_stats(
    request: Request,
    db: Session = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    """Counts by source_type, date range, latest ingestion."""
    total = db.query(func.count(ResearchSource.id)).scalar() or 0

    type_counts = (
        db.query(ResearchSource.source_type, func.count(ResearchSource.id))
        .group_by(ResearchSource.source_type)
        .all()
    )

    min_date = db.query(func.min(ResearchSource.published_at)).scalar()
    max_date = db.query(func.max(ResearchSource.published_at)).scalar()
    latest_ingest = db.query(func.max(ResearchSource.ingested_at)).scalar()

    return SourceStats(
        total=total,
        by_type={t: c for t, c in type_counts},
        date_range={
            "earliest": min_date.isoformat() if min_date else None,
            "latest": max_date.isoformat() if max_date else None,
        },
        latest_ingestion=latest_ingest,
    )


# ── GET /sources/context ────────────────────────────────────────


@router.get("/sources/context")
@limiter.limit("10/minute")
def get_source_context(
    request: Request,
    q: Optional[str] = None,
    type: Optional[str] = None,
    topic: Optional[str] = None,
    symbol: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    limit: int = Query(default=30, ge=1, le=100),
    max_chars: int = Query(default=100000, ge=1000, le=500000),
    db: Session = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    """Concatenated markdown of matching sources for Claude consumption."""
    query = db.query(ResearchSource)

    if type:
        query = query.filter(ResearchSource.source_type == type)

    if q:
        safe_q = _re.sub(r"[*:()!&|<>\\]", " ", q.strip())
        safe_q = " ".join(safe_q.split())
        if safe_q:
            ts_query = func.websearch_to_tsquery("english", safe_q)
            fts_col = text(
                "to_tsvector('english', "
                "coalesce(title, '') || ' ' || "
                "coalesce(content_text, '') || ' ' || "
                "coalesce(summary, ''))"
            )
            query = query.filter(fts_col.op("@@")(ts_query))

    if topic:
        query = query.filter(
            ResearchSource.topics.op("@>")(_json.dumps([topic]))
        )

    if symbol:
        query = query.filter(
            ResearchSource.symbols.op("@>")(_json.dumps([symbol]))
        )

    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            query = query.filter(ResearchSource.published_at >= since_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid 'since' date format")

    if until:
        try:
            until_dt = datetime.fromisoformat(until)
            query = query.filter(ResearchSource.published_at <= until_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid 'until' date format")

    rows = (
        query.order_by(ResearchSource.published_at.desc().nullslast())
        .limit(limit)
        .all()
    )

    parts = []
    total_chars = 0
    for src in rows:
        date_str = src.published_at.strftime("%Y-%m-%d") if src.published_at else "unknown"
        header = f"### [{src.source_type}] {src.title} ({date_str})"
        if src.source_name:
            header += f" -- {src.source_name}"

        body = src.content_text or src.summary or ""
        block = f"{header}\n{body}\n---"

        if total_chars + len(block) > max_chars:
            # Truncate last block to fit
            remaining = max_chars - total_chars
            if remaining > 100:
                parts.append(block[:remaining] + "\n...[truncated]")
            break

        parts.append(block)
        total_chars += len(block)

    return {
        "count": len(parts),
        "total_available": len(rows),
        "content": "\n\n".join(parts),
    }


# ── GET /sources/{id} ───────────────────────────────────────────


@router.get("/sources/{source_id}", response_model=SourceDetail)
@limiter.limit("60/minute")
def get_source_detail(
    source_id: str,
    request: Request,
    db: Session = Depends(get_session),
    _user: User = Depends(get_current_user),
):
    """Full source with content_text."""
    src = db.query(ResearchSource).filter(ResearchSource.id == source_id).first()
    if not src:
        raise HTTPException(status_code=404, detail="Source not found")
    return SourceDetail.model_validate(src)
