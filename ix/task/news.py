import feedparser
import logging
from datetime import datetime
import hashlib
import json
from urllib.parse import quote_plus
from urllib.request import Request, urlopen
from sqlalchemy.orm import Session as SASession
from ix.db.conn import Session
from ix.db.models.news_item import NewsItem
from ix.misc import get_logger

logger = get_logger(__name__)

RSS_FEEDS = {
    "Yahoo Finance": "https://finance.yahoo.com/rss/",
    "CNBC Finance": "https://www.cnbc.com/id/10000664/device/rss/rss.html",
    "MarketWatch": "http://feeds.marketwatch.com/marketwatch/topstories/",
    "Investing.com": "https://www.investing.com/rss/news.rss",
    "WSJ Markets": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
}

SEC_RSS_FEEDS = {
    "SEC Press Releases": "https://www.sec.gov/news/pressreleases.rss",
    "SEC Speeches": "https://www.sec.gov/rss/speeches.xml",
}

REDDIT_FEEDS = {
    "Reddit r/investing": "https://www.reddit.com/r/investing/new.json?limit=80",
    "Reddit r/stocks": "https://www.reddit.com/r/stocks/new.json?limit=80",
    "Reddit r/SecurityAnalysis": "https://www.reddit.com/r/SecurityAnalysis/new.json?limit=80",
}

GDELT_QUERIES = [
    "stocks OR equity OR earnings OR fed OR inflation OR treasury",
]


def _safe_datetime_from_struct_or_now(published_parsed) -> datetime:
    if published_parsed:
        return datetime(*published_parsed[:6])
    return datetime.utcnow()


def _extract_rss_authors(entry) -> list[str]:
    return [
        a.get("name")
        for a in entry.get("authors", [])
        if isinstance(a, dict) and a.get("name")
    ]


def _extract_rss_tags(entry) -> list[str]:
    return [
        t.get("term")
        for t in entry.get("tags", [])
        if isinstance(t, dict) and t.get("term")
    ]


def _upsert_unified_news_item(
    db: SASession,
    *,
    source: str,
    source_name: str,
    source_item_id: str | None,
    url: str | None,
    title: str,
    summary: str | None = None,
    body_text: str | None = None,
    published_at: datetime | None = None,
    symbols: list[str] | None = None,
    meta: dict | None = None,
    raw: dict | None = None,
    lang: str | None = None,
) -> bool:
    """
    Returns True if inserted, False if updated existing.
    """
    url_hash = None
    if url:
        url_hash = hashlib.sha256(url.strip().encode("utf-8")).hexdigest()

    existing = None
    if url_hash:
        existing = db.query(NewsItem).filter(NewsItem.url_hash == url_hash).first()
    if existing is None and source_item_id:
        existing = (
            db.query(NewsItem)
            .filter(NewsItem.source == source)
            .filter(NewsItem.source_name == source_name)
            .filter(NewsItem.source_item_id == str(source_item_id))
            .first()
        )

    if existing is None:
        db.add(
            NewsItem(
                source=source,
                source_name=source_name,
                source_item_id=str(source_item_id) if source_item_id else None,
                url=url,
                url_hash=url_hash,
                title=title or "",
                body_text=body_text,
                summary=summary,
                lang=lang,
                symbols=symbols or [],
                meta=meta or {},
                raw=raw or {},
                published_at=published_at,
                discovered_at=datetime.utcnow(),
            )
        )
        return True

    existing.title = title or existing.title
    existing.summary = summary or existing.summary
    existing.body_text = body_text or existing.body_text
    existing.published_at = published_at or existing.published_at
    existing.url = url or existing.url
    if symbols:
        existing.symbols = symbols
    if meta:
        existing.meta = {**(existing.meta or {}), **meta}
    if raw:
        existing.raw = {**(existing.raw or {}), **raw}
    return False


def fetch_rss_feed(source_name: str, url: str, db: SASession):
    logger.info(f"Fetching RSS feed from {source_name}: {url}")
    try:
        feed = feedparser.parse(url)
        if feed.bozo:
            logger.warning(f"Feed error from {source_name}: {feed.bozo_exception}")

        new_count = 0
        for entry in feed.entries:
            title = entry.get("title")
            link = entry.get("link")
            summary = entry.get("summary", "")
            source_item_id = entry.get("id") or entry.get("guid")

            # Parse published date
            published_parsed = entry.get("published_parsed")
            published_at = _safe_datetime_from_struct_or_now(published_parsed)

            did_insert = _upsert_unified_news_item(
                db,
                source="rss",
                source_name=source_name,
                source_item_id=str(source_item_id) if source_item_id else None,
                url=link,
                title=title or "",
                summary=summary or None,
                body_text=summary or None,
                published_at=published_at,
                meta={
                    "feed_url": url,
                    "authors": _extract_rss_authors(entry),
                    "tags": _extract_rss_tags(entry),
                },
                raw={
                    "title": title,
                    "link": link,
                    "summary": summary,
                    "published": entry.get("published"),
                    "id": source_item_id,
                },
                lang=(entry.get("language") or None),
            )
            if did_insert:
                new_count += 1

        db.commit()
        logger.info(f"Saved {new_count} new articles from {source_name}")

    except Exception as e:
        logger.error(f"Error fetching {source_name}: {e}")


def fetch_reddit_feed(source_name: str, url: str, db: SASession):
    logger.info(f"Fetching Reddit JSON from {source_name}: {url}")
    try:
        req = Request(
            url,
            headers={
                "User-Agent": "investment-x-news-ingestor/1.0 (+https://github.com/HTF1125/investment-x)"
            },
        )
        with urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        children = (((payload or {}).get("data") or {}).get("children") or [])
        inserted = 0
        for row in children:
            data = (row or {}).get("data") or {}
            permalink = data.get("permalink")
            full_url = f"https://www.reddit.com{permalink}" if permalink else data.get("url")
            created_utc = data.get("created_utc")
            published_at = (
                datetime.utcfromtimestamp(created_utc) if isinstance(created_utc, (int, float)) else datetime.utcnow()
            )
            did_insert = _upsert_unified_news_item(
                db,
                source="reddit",
                source_name=source_name,
                source_item_id=str(data.get("id") or ""),
                url=full_url,
                title=(data.get("title") or "").strip(),
                summary=(data.get("selftext") or "")[:4000] or None,
                body_text=(data.get("selftext") or "")[:12000] or None,
                published_at=published_at,
                symbols=[],
                meta={
                    "subreddit": data.get("subreddit"),
                    "author": data.get("author"),
                    "score": data.get("score"),
                    "num_comments": data.get("num_comments"),
                    "is_self": data.get("is_self"),
                },
                raw={
                    "id": data.get("id"),
                    "name": data.get("name"),
                    "permalink": permalink,
                },
                lang="en",
            )
            if did_insert:
                inserted += 1
        db.commit()
        logger.info(f"Saved {inserted} new Reddit items from {source_name}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error fetching Reddit source {source_name}: {e}")


def fetch_gdelt(query: str, db: SASession, max_records: int = 100):
    encoded_q = quote_plus(query)
    url = (
        "https://api.gdeltproject.org/api/v2/doc/doc?"
        f"query={encoded_q}&mode=ArtList&maxrecords={max_records}&format=json&sort=DateDesc"
    )
    logger.info(f"Fetching GDELT for query: {query}")
    try:
        req = Request(url, headers={"User-Agent": "investment-x-news-ingestor/1.0"})
        with urlopen(req, timeout=25) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        articles = payload.get("articles") or []
        inserted = 0
        for art in articles:
            published_at = None
            try:
                seendate = art.get("seendate")
                if seendate:
                    published_at = datetime.strptime(seendate, "%Y%m%dT%H%M%SZ")
            except Exception:
                published_at = datetime.utcnow()
            did_insert = _upsert_unified_news_item(
                db,
                source="gdelt",
                source_name="GDELT",
                source_item_id=(art.get("url") or "")[:500],
                url=art.get("url"),
                title=(art.get("title") or "").strip(),
                summary=(art.get("seendate") or None),
                body_text=None,
                published_at=published_at,
                symbols=[],
                meta={
                    "domain": art.get("domain"),
                    "language": art.get("language"),
                    "socialimage": art.get("socialimage"),
                    "query": query,
                },
                raw=art,
                lang=art.get("language"),
            )
            if did_insert:
                inserted += 1
        db.commit()
        logger.info(f"Saved {inserted} new GDELT items for query: {query}")
    except Exception as e:
        db.rollback()
        logger.error(f"Error fetching GDELT query '{query}': {e}")


def run_news_scraping():
    """Run news scraping task."""
    with Session() as db:
        for name, url in RSS_FEEDS.items():
            fetch_rss_feed(name, url, db)
        for name, url in SEC_RSS_FEEDS.items():
            fetch_rss_feed(name, url, db)
        for name, url in REDDIT_FEEDS.items():
            fetch_reddit_feed(name, url, db)
        for q in GDELT_QUERIES:
            fetch_gdelt(q, db)


if __name__ == "__main__":
    run_news_scraping()
