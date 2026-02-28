from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Any
from ix.db.conn import get_session
from ix.db.models import TelegramMessage
from ix.db.models.news_item import NewsItem
from ix.db.models.youtube_intel import YouTubeIntel
from ix.db.conn import ensure_connection, conn
from pydantic import BaseModel
import json
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from xml.etree import ElementTree as ET
import re
from sqlalchemy import text, func, or_
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


class YouTubeVideoIntel(BaseModel):
    video_id: str
    channel: str
    title: str
    published_at: datetime
    updated_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    is_new: bool = False
    url: str
    summary: Optional[str] = None


class YouTubeIntelResponse(BaseModel):
    generated_at: datetime
    videos: list[YouTubeVideoIntel]
    page: int = 1
    page_size: int = 8
    total: int = 0
    total_pages: int = 0
    note: Optional[str] = None


class AddYouTubeVideoRequest(BaseModel):
    url: str


class UpdateYouTubeSummaryRequest(BaseModel):
    summary: str


class NewsAggregateResponse(BaseModel):
    generated_at: datetime
    telegram_messages: list[TelegramMessageSchema]
    video_summaries: list[YouTubeVideoIntel]


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


_ATOM_NS = {
    "a": "http://www.w3.org/2005/Atom",
    "m": "http://search.yahoo.com/mrss/",
    "yt": "http://www.youtube.com/xml/schemas/2015",
}
_MIN_VIDEO_SECONDS = 300
_YOUTUBE_CHANNEL_URLS = [
    "https://www.youtube.com/@RaoulPalTJM",
    "https://www.youtube.com/@RealVisionFinance",
    "https://www.youtube.com/@42Macro",
    "https://www.youtube.com/@ForwardGuidanceBW",
    "https://www.youtube.com/@themarketradar",
    "https://www.youtube.com/@ARKInvest2015",
]


def _now_utc() -> datetime:
    return datetime.utcnow()


def _parse_iso8601(s: str) -> datetime:
    text = (s or "").strip()
    if not text:
        raise ValueError("Missing ISO-8601 datetime")
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _resolve_youtube_channel_ids() -> list[str]:
    # Resolve fixed channel URLs (handles or /channel/ links) to channel IDs.
    raw_urls = ",".join(_YOUTUBE_CHANNEL_URLS)
    ids: list[str] = []

    def _extract_channel_id_from_html(page_html: str) -> str:
        # Prefer canonical/og channel URL first; handle pages can contain unrelated IDs.
        patterns = [
            r'<link rel="canonical" href="https://www\.youtube\.com/channel/(UC[\w-]{20,})"',
            r'property="og:url" content="https://www\.youtube\.com/channel/(UC[\w-]{20,})"',
            r'"externalId":"(UC[\w-]{20,})"',
            r'"channelId":"(UC[\w-]{20,})"',
        ]
        for pattern in patterns:
            m = re.search(pattern, page_html)
            if m:
                return m.group(1)
        return ""

    for u in [x.strip() for x in raw_urls.split(",") if x.strip()]:
        try:
            p = urlparse(u)
            parts = [part for part in p.path.split("/") if part]
            if len(parts) >= 2 and parts[0] == "channel":
                ids.append(parts[1])
                continue
            # Handle URLs like /@handle: resolve page and extract channelId from HTML.
            req = Request(u, headers={"User-Agent": "Mozilla/5.0 (investment-x/1.0)"})
            with urlopen(req, timeout=15) as resp:
                page_html = resp.read().decode("utf-8", errors="ignore")
            resolved_id = _extract_channel_id_from_html(page_html)
            if resolved_id:
                ids.append(resolved_id)
        except Exception:
            continue
    # Deduplicate while preserving order.
    seen = set()
    out: list[str] = []
    for cid in ids:
        if cid in seen:
            continue
        seen.add(cid)
        out.append(cid)
    return out


def _extract_video_id_from_url(url: str) -> str:
    u = (url or "").strip()
    if not u:
        return ""
    # raw video id
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", u):
        return u
    m = re.search(r"(?:v=|/shorts/|youtu\.be/)([A-Za-z0-9_-]{11})", u)
    if m:
        return m.group(1)
    return ""


def _fetch_video_info(video_id: str) -> dict[str, Any]:
    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    duration_seconds = _fetch_video_duration_seconds(video_id)
    published_at = _fetch_video_published_at(video_id)
    if published_at is None:
        raise ValueError("Unable to resolve canonical published_at for video")
    # Try oEmbed first (title + author_name).
    try:
        oembed_url = (
            "https://www.youtube.com/oembed?"
            f"url={watch_url}&format=json"
        )
        req = Request(oembed_url, headers={"User-Agent": "investment-x/1.0"})
        with urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        title = str(data.get("title", "")).strip()
        channel = str(data.get("author_name", "")).strip() or "YouTube"
        return {
            "video_id": video_id,
            "channel": channel,
            "title": title or f"Video {video_id}",
            "published_at": published_at,
            "url": watch_url,
            "description": "",
            "duration_seconds": duration_seconds,
        }
    except Exception:
        pass
    return {
        "video_id": video_id,
        "channel": "YouTube",
        "title": f"Video {video_id}",
        "published_at": published_at,
        "url": watch_url,
        "description": "",
        "duration_seconds": duration_seconds,
    }


def _fetch_video_published_at(video_id: str) -> Optional[datetime]:
    try:
        feed_url = f"https://www.youtube.com/feeds/videos.xml?video_id={video_id}"
        req = Request(feed_url, headers={"User-Agent": "Mozilla/5.0 (investment-x/1.0)"})
        with urlopen(req, timeout=12) as resp:
            xml_data = resp.read()
        root = ET.fromstring(xml_data)
        entry = root.find("a:entry", _ATOM_NS)
        if entry is None:
            return None
        published_raw = entry.findtext("a:published", default="", namespaces=_ATOM_NS)
        if not published_raw:
            raise ValueError("Missing published in video feed")
        return _parse_iso8601(published_raw)
    except Exception:
        # Fallback: parse publish timestamp from watch page metadata.
        try:
            watch_url = f"https://www.youtube.com/watch?v={video_id}"
            req = Request(watch_url, headers={"User-Agent": "Mozilla/5.0 (investment-x/1.0)"})
            with urlopen(req, timeout=12) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            # Preferred pattern from player microformat JSON.
            m = re.search(r'"publishDate":"([0-9T:\-+\.Z]+)"', html)
            if m:
                raw = m.group(1).strip()
                return _parse_iso8601(raw)

            # Secondary pattern: date-only upload date.
            m = re.search(r'"uploadDate":"([0-9]{4}-[0-9]{2}-[0-9]{2})"', html)
            if m:
                raw = f"{m.group(1)}T00:00:00+00:00"
                return _parse_iso8601(raw)
        except Exception:
            return None
        return None


def _fetch_video_duration_seconds(video_id: str) -> Optional[int]:
    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        req = Request(watch_url, headers={"User-Agent": "Mozilla/5.0 (investment-x/1.0)"})
        with urlopen(req, timeout=12) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
        m = re.search(r'"lengthSeconds":"(\d+)"', html)
        if m:
            return int(m.group(1))
        m = re.search(r'"approxDurationMs":"(\d+)"', html)
        if m:
            return int(m.group(1)) // 1000
    except Exception:
        return None
    return None


def _ensure_youtube_intel_table() -> None:
    if not ensure_connection():
        raise RuntimeError("Failed to establish database connection")
    YouTubeIntel.__table__.create(bind=conn.engine, checkfirst=True)
    # Backward-compat migration: drop deprecated implications column if present.
    with conn.engine.begin() as c:
        c.execute(text("ALTER TABLE youtube_intel DROP COLUMN IF EXISTS implications"))
        c.execute(
            text(
                "ALTER TABLE youtube_intel "
                "ADD COLUMN IF NOT EXISTS duration_seconds INTEGER"
            )
        )
        c.execute(
            text(
                "ALTER TABLE youtube_intel "
                "ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE"
            )
        )
        c.execute(
            text(
                "ALTER TABLE youtube_intel "
                "ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP NULL"
            )
        )


def _fetch_channel_feed(channel_id: str) -> list[dict[str, Any]]:
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    req = Request(feed_url, headers={"User-Agent": "investment-x/1.0"})
    with urlopen(req, timeout=15) as resp:
        xml_data = resp.read()
    root = ET.fromstring(xml_data)
    out: list[dict[str, Any]] = []
    for entry in root.findall("a:entry", _ATOM_NS):
        try:
            vid = (
                entry.findtext("a:id", default="", namespaces=_ATOM_NS)
                .replace("yt:video:", "")
                .strip()
            )
            if not vid:
                continue

            title = entry.findtext("a:title", default="", namespaces=_ATOM_NS).strip()
            link_node = entry.find("a:link", _ATOM_NS)
            link = ""
            if link_node is not None:
                link = link_node.attrib.get("href", "")

            published_raw = entry.findtext("a:published", default="", namespaces=_ATOM_NS)
            published = _parse_iso8601(published_raw)

            channel_name = entry.findtext(
                "a:author/a:name", default="", namespaces=_ATOM_NS
            ).strip()
            desc = entry.findtext("m:group/m:description", default="", namespaces=_ATOM_NS).strip()

            duration_seconds = None
            duration_node = entry.find("m:group/yt:duration", _ATOM_NS)
            if duration_node is not None:
                raw_seconds = duration_node.attrib.get("seconds")
                if raw_seconds and raw_seconds.isdigit():
                    duration_seconds = int(raw_seconds)

            out.append(
                {
                    "video_id": vid,
                    "channel": channel_name or channel_id,
                    "title": title,
                    "published_at": published,
                    "url": link or f"https://www.youtube.com/watch?v={vid}",
                    "description": desc,
                    "duration_seconds": duration_seconds,
                }
            )
        except Exception:
            # Skip malformed entries instead of poisoning the full channel sync.
            continue
    return out


def _is_short_video(v: dict[str, Any]) -> bool:
    title = (v.get("title") or "").lower()
    desc = (v.get("description") or "").lower()
    url = (v.get("url") or "").lower()
    # RSS does not always provide duration; use robust heuristics.
    return (
        "/shorts/" in url
        or "#shorts" in title
        or "#shorts" in desc
        or title.endswith("shorts")
        or title.startswith("shorts:")
    )

def _upsert_video_stub(db: Session, video: dict[str, Any]) -> YouTubeIntel:
    row = db.query(YouTubeIntel).filter(YouTubeIntel.video_id == video["video_id"]).first()
    if row is None:
        row = YouTubeIntel(
            video_id=video["video_id"],
            channel=video["channel"],
            title=video["title"],
            url=video["url"],
            published_at=video["published_at"],
            duration_seconds=video.get("duration_seconds"),
            summary=None,
        )
        db.add(row)
        db.flush()
        return row

    if bool(getattr(row, "is_deleted", False)):
        # Persist deletion intent: never resurrect this video on background sync.
        return row

    row.channel = video["channel"]
    row.title = video["title"]
    row.url = video["url"]
    # Keep original published_at immutable after first insert.
    if row.published_at is None:
        row.published_at = video["published_at"]
    row.duration_seconds = video.get("duration_seconds")
    return row


def _delete_under_5_minute_videos(db: Session) -> int:
    deleted = (
        db.query(YouTubeIntel)
        .filter(YouTubeIntel.is_deleted.is_(False))
        .filter(
            or_(
                YouTubeIntel.duration_seconds < _MIN_VIDEO_SECONDS,
                func.lower(YouTubeIntel.url).like("%/shorts/%"),
                func.lower(YouTubeIntel.title).like("%#shorts%"),
                func.lower(YouTubeIntel.title).like("shorts:%"),
                func.lower(YouTubeIntel.title).like("% shorts"),
            )
        )
        .delete(synchronize_session=False)
    )
    return int(deleted or 0)


def _backfill_suspicious_published_dates(db: Session, limit_rows: int = 40) -> int:
    """
    Correct rows likely saved with fallback `published_at=now` from older manual ingest logic.
    We only inspect recent rows where published_at is very close to created_at.
    """
    now = _now_utc()
    suspicious = (
        db.query(YouTubeIntel)
        .filter(YouTubeIntel.is_deleted.is_(False))
        .filter(YouTubeIntel.created_at.isnot(None))
        .filter(YouTubeIntel.published_at.isnot(None))
        .filter(YouTubeIntel.created_at >= now - timedelta(days=365))
        .all()
    )
    updated = 0
    checked = 0
    for row in suspicious:
        if checked >= limit_rows:
            break
        if not row.video_id:
            continue
        # Suspicious patterns:
        # 1) published_at almost equal to created_at (manual fallback pattern)
        # 2) published_at set very recently even though we already have an older created row
        delta = abs((row.created_at - row.published_at).total_seconds())
        very_recent_published = row.published_at >= now - timedelta(days=3)
        if delta > 7 * 24 * 3600 and not very_recent_published:
            continue
        checked += 1
        real_published = _fetch_video_published_at(row.video_id)
        if real_published is None:
            continue
        # Only overwrite when we detect materially different actual publish date.
        if abs((real_published - row.published_at).total_seconds()) >= 3600:
            row.published_at = real_published
            updated += 1
    return updated


def _to_video_schema(row: YouTubeIntel) -> YouTubeVideoIntel:
    now = _now_utc()
    cutoff = now - timedelta(hours=24)
    is_new = bool(
        (row.published_at and row.published_at >= cutoff)
        or (row.created_at and row.created_at >= cutoff)
    )
    return YouTubeVideoIntel(
        video_id=row.video_id,
        channel=row.channel,
        title=row.title,
        published_at=row.published_at,
        updated_at=row.updated_at,
        created_at=row.created_at,
        is_new=is_new,
        url=row.url,
        summary=(row.summary or "").strip() if row.summary else None,
    )


def _repair_published_dates_inline(db: Session, rows: list[YouTubeIntel], max_repairs: int = 5) -> int:
    repaired = 0
    now = _now_utc()
    for row in rows:
        if repaired >= max_repairs:
            break
        if not row.video_id or not row.created_at or not row.published_at:
            continue
        delta = abs((row.created_at - row.published_at).total_seconds())
        very_recent_published = row.published_at >= now - timedelta(days=3)
        if delta > 7 * 24 * 3600 and not very_recent_published:
            continue
        real_published = _fetch_video_published_at(row.video_id)
        if real_published is None:
            continue
        if abs((real_published - row.published_at).total_seconds()) >= 3600:
            row.published_at = real_published
            repaired += 1
    if repaired:
        db.commit()
    return repaired


def _sync_youtube_catalog(db: Session, limit: int = 50) -> tuple[int, Optional[str]]:
    sync_error: Optional[str] = None
    deleted_under_5m = 0
    try:
        _ensure_youtube_intel_table()
        channel_ids = _resolve_youtube_channel_ids()
        if channel_ids:
            all_videos: list[dict[str, Any]] = []
            for cid in channel_ids:
                try:
                    all_videos.extend(_fetch_channel_feed(cid))
                except Exception:
                    continue

            dedup: dict[str, dict[str, Any]] = {}
            for v in all_videos:
                vid = v.get("video_id")
                if not vid:
                    continue
                existing = dedup.get(vid)
                if existing is None or v["published_at"] > existing["published_at"]:
                    dedup[vid] = v

            feed_videos: list[dict[str, Any]] = []
            for v in dedup.values():
                if _is_short_video(v):
                    continue
                duration = v.get("duration_seconds")
                if duration is None:
                    continue
                if duration < _MIN_VIDEO_SECONDS:
                    continue
                feed_videos.append(v)
            feed_videos.sort(key=lambda x: x["published_at"], reverse=True)
            feed_videos = feed_videos[: max(1, min(limit, 200))]

            for v in feed_videos:
                _upsert_video_stub(db, v)

            curated_channels = {v.get("channel") for v in feed_videos if v.get("channel")}
            if curated_channels:
                (
                    db.query(YouTubeIntel)
                    .filter(~YouTubeIntel.channel.in_(list(curated_channels)))
                    .filter(YouTubeIntel.summary.is_(None))
                    .delete(synchronize_session=False)
                )
            deleted_under_5m = _delete_under_5_minute_videos(db)
            db.commit()
        else:
            sync_error = "No configured YouTube channels available."
    except Exception as e:
        db.rollback()
        sync_error = f"Sync degraded: {str(e)}"
    return deleted_under_5m, sync_error


@router.get("/news", response_model=NewsAggregateResponse)
def get_news_aggregate(db: Session = Depends(get_session)):
    """
    Unified news endpoint:
    - Telegram messages from last 24 hours
    - YouTube video summaries from last 7 days
    """
    now = datetime.utcnow()
    telegram_cutoff = now - timedelta(days=7)
    youtube_cutoff = now - timedelta(days=7)

    telegram_messages = (
        db.query(TelegramMessage)
        .filter(TelegramMessage.date >= telegram_cutoff)
        .order_by(TelegramMessage.date.desc())
        .limit(300)
        .all()
    )

    youtube_rows = (
        db.query(YouTubeIntel)
        .filter(YouTubeIntel.is_deleted.is_(False))
        .filter(YouTubeIntel.published_at >= youtube_cutoff)
        .filter(YouTubeIntel.summary.isnot(None))
        .order_by(YouTubeIntel.published_at.desc())
        .all()
    )

    return NewsAggregateResponse(
        generated_at=_now_utc(),
        telegram_messages=[TelegramMessageSchema.model_validate(m) for m in telegram_messages],
        video_summaries=[_to_video_schema(r) for r in youtube_rows],
    )


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
        # Use Full-Text Search (FTS) with to_tsvector/websearch_to_tsquery for relevance
        # Fallback to ILIKE if FTS yields nothing (e.g. for partial matches not in tsvector)
        ts_query = func.websearch_to_tsquery("english", search_text)
        fts_filter = NewsItem.__table__.c.title.op("@@")(ts_query) | \
                     NewsItem.__table__.c.summary.op("@@")(ts_query)
        
        # Check if FTS returns results, otherwise fallback to ilike
        fts_rows = query.filter(fts_filter).limit(limit).all()
        if fts_rows:
            return [UnifiedNewsItemSchema.model_validate(r) for r in fts_rows]
        
        # Fallback to traditional ilike for partial word matches
        pattern = f"%{search_text}%"
        query = query.filter(or_(NewsItem.title.ilike(pattern), NewsItem.summary.ilike(pattern)))
    
    rows = (
        query.order_by(NewsItem.published_at.desc().nullslast(), NewsItem.discovered_at.desc())
        .limit(limit)
        .all()
    )
    return [UnifiedNewsItemSchema.model_validate(r) for r in rows]


@router.get("/news/youtube", response_model=YouTubeIntelResponse)
def get_recent_youtube_intel(
    hours: int = 24,
    limit: int = 50,
    page: int = 1,
    page_size: int = 8,
    sort: str = "unsummarized",
    q: Optional[str] = None,
    refresh: bool = False,
    db: Session = Depends(get_session),
):
    """
    Pull recent videos from curated YouTube channels and summarize with Gemini.
    Shorts are filtered out.
    Requires:
    - GEMINI_API_KEY
    """
    deleted_under_5m = 0
    sync_error: Optional[str] = None
    if refresh:
        deleted_under_5m, sync_error = _sync_youtube_catalog(db=db, limit=limit)

    # Pagination universe: all stored videos (manual + historical), with user-selected sort/search.
    db_query = db.query(YouTubeIntel).filter(YouTubeIntel.is_deleted.is_(False))
    search_text = (q or "").strip()
    if search_text:
        pattern = f"%{search_text}%"
        db_query = db_query.filter(
            or_(
                YouTubeIntel.title.ilike(pattern),
                YouTubeIntel.channel.ilike(pattern),
                YouTubeIntel.summary.ilike(pattern),
            )
        )
    db_rows = db_query.all()
    all_items = [_to_video_schema(r) for r in db_rows]

    def _sort_key(item: YouTubeVideoIntel):
        missing_summary = 1 if not (item.summary and item.summary.strip()) else 0
        return (missing_summary, 1 if item.is_new else 0, item.published_at)
    if sort == "published_desc":
        all_items.sort(key=lambda x: x.published_at, reverse=True)
    else:
        all_items.sort(key=_sort_key, reverse=True)
    page = max(1, page)
    page_size = max(1, min(page_size, 50))
    total = len(all_items)
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    start = (page - 1) * page_size
    end = start + page_size
    paged = all_items[start:end]

    note = None
    if total == 0:
        note = "No videos available."
    else:
        missing_count = sum(1 for x in all_items if not (x.summary and x.summary.strip()))
        recent_count = sum(1 for x in all_items if x.is_new)
        note = (
            f"Sorted with unsummarized videos first ({missing_count} missing summary), "
            f"then new videos ({recent_count} in last 24h). "
            f"Removed {deleted_under_5m} videos under 5 minutes."
        )
    if sort == "published_desc":
        note = f"Sorted by publish date descending. {note}" if note else "Sorted by publish date descending."
    if search_text:
        note = f"{note} Search: \"{search_text}\"." if note else f"Search: \"{search_text}\"."
    if sync_error:
        note = f"{note} {sync_error}".strip() if note else sync_error
    return YouTubeIntelResponse(
        generated_at=_now_utc(),
        videos=paged,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        note=note,
    )


@router.post("/news/youtube/sync")
def sync_youtube_intel(
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Admin-only explicit YouTube sync trigger."""
    if not bool(getattr(current_user, "effective_role", User.ROLE_GENERAL) in User.ADMIN_ROLES):
        raise HTTPException(status_code=403, detail="Admin only")
    deleted_under_5m, sync_error = _sync_youtube_catalog(db=db, limit=50)
    return {
        "ok": True,
        "generated_at": _now_utc(),
        "note": sync_error or "YouTube sync completed.",
        "removed_under_5m": deleted_under_5m,
    }


@router.post("/news/youtube/add", response_model=YouTubeVideoIntel)
def add_youtube_video_for_intel(
    payload: AddYouTubeVideoRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    Manually add a single YouTube video by URL (or raw video id),
    ingest metadata and persist it for manual admin summary workflow.
    """
    _ensure_youtube_intel_table()
    if not bool(getattr(current_user, "effective_role", User.ROLE_GENERAL) in User.ADMIN_ROLES):
        raise HTTPException(status_code=403, detail="Admin only")
    video_id = _extract_video_id_from_url(payload.url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Invalid YouTube URL or video id.")
    existing = db.query(YouTubeIntel).filter(YouTubeIntel.video_id == video_id).first()
    if existing and bool(getattr(existing, "is_deleted", False)):
        raise HTTPException(
            status_code=409,
            detail="This video was deleted and is blocked from re-ingestion.",
        )

    try:
        video = _fetch_video_info(video_id)
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Unable to fetch canonical published date for this YouTube video.",
        )
    duration = video.get("duration_seconds")
    if duration is not None and duration < _MIN_VIDEO_SECONDS:
        raise HTTPException(
            status_code=400,
            detail="Video is under 5 minutes and cannot be added.",
        )
    row = _upsert_video_stub(db, video)
    db.commit()
    db.refresh(row)
    return _to_video_schema(row)


@router.patch("/news/youtube/{video_id}/summary", response_model=YouTubeVideoIntel)
def update_youtube_video_summary(
    video_id: str,
    payload: UpdateYouTubeSummaryRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Admin-only manual summary update."""
    if not bool(getattr(current_user, "effective_role", User.ROLE_GENERAL) in User.ADMIN_ROLES):
        raise HTTPException(status_code=403, detail="Admin only")
    _ensure_youtube_intel_table()
    row = db.query(YouTubeIntel).filter(YouTubeIntel.video_id == video_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found.")
    if bool(getattr(row, "is_deleted", False)):
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found.")
    row.summary = (payload.summary or "").strip() or None
    db.commit()
    db.refresh(row)
    return _to_video_schema(row)


@router.delete("/news/youtube/{video_id}")
def delete_youtube_video(
    video_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Admin-only soft delete; deleted videos are excluded from future syncs."""
    if not bool(getattr(current_user, "effective_role", User.ROLE_GENERAL) in User.ADMIN_ROLES):
        raise HTTPException(status_code=403, detail="Admin only")
    _ensure_youtube_intel_table()
    row = db.query(YouTubeIntel).filter(YouTubeIntel.video_id == video_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"Video '{video_id}' not found.")
    row.is_deleted = True
    row.deleted_at = _now_utc()
    db.commit()
    return {"ok": True, "video_id": video_id}
