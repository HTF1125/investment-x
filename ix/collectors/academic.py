"""Academic paper collector for SSRN, NBER, and Fed working papers.

Fetches new finance/economics working papers via RSS feeds.
Stores as NewsItem entries with source="academic".
"""

import time
from datetime import datetime

import feedparser
from bs4 import BeautifulSoup

from ix.collectors.base import BaseCollector
from ix.collectors.fulltext import fetch_full_text
from ix.db.conn import Session


class AcademicPapersCollector(BaseCollector):
    name = "academic"
    display_name = "Academic Papers"
    schedule = "0 7 * * *"  # Daily 7 AM
    category = "academic"

    FEEDS = [
        {
            "name": "NBER Working Papers",
            "url": "https://www.nber.org/rss/new.xml",
            "source_name": "NBER",
        },
        {
            "name": "Fed Research (FEDS)",
            "url": "https://www.federalreserve.gov/feeds/feds.xml",
            "source_name": "Fed Research",
        },
        {
            "name": "NY Fed Liberty Street",
            "url": "https://feeds.feedburner.com/LibertyStreetEconomics",
            "source_name": "NY Fed",
        },
        {
            "name": "ECB Working Papers",
            "url": "https://www.ecb.europa.eu/rss/wppn.html",
            "source_name": "ECB",
        },
        {
            "name": "BIS Working Papers",
            "url": "https://www.bis.org/doclist/wppubls.rss",
            "source_name": "BIS",
        },
        {
            "name": "IMF Working Papers",
            "url": "https://www.imf.org/en/Publications/RSS?type=WP",
            "source_name": "IMF",
        },
        # ── New Academic Feeds ──
        {
            "name": "FRED Blog",
            "url": "https://fredblog.stlouisfed.org/feed/",
            "source_name": "St. Louis Fed",
        },
        {
            "name": "Brookings Economic Studies",
            "url": "https://www.brookings.edu/feed/?topic=economy",
            "source_name": "Brookings",
        },
        {
            "name": "Peterson Institute (PIIE)",
            "url": "https://www.piie.com/rss.xml",
            "source_name": "PIIE",
        },
        {
            "name": "Chicago Fed Insights",
            "url": "https://www.chicagofed.org/publications/blogs/rss",
            "source_name": "Chicago Fed",
        },
    ]

    # Finance-related keywords for SSRN filtering
    FINANCE_KEYWORDS = [
        "asset pricing", "risk premium", "factor", "portfolio",
        "volatility", "market", "equity", "bond", "fixed income",
        "monetary policy", "inflation", "recession", "credit",
        "financial stability", "systemic risk", "liquidity",
        "macro", "business cycle", "yield curve",
    ]

    def collect(self, progress_cb=None) -> dict:
        inserted = 0
        errors = 0
        total = len(self.FEEDS)

        with Session() as db:
            for i, feed_info in enumerate(self.FEEDS):
                if progress_cb:
                    progress_cb(i + 1, total, f"Fetching {feed_info['name']}")

                try:
                    count = self._fetch_feed(db, feed_info)
                    inserted += count
                except Exception as e:
                    self.logger.error(f"Error fetching {feed_info['name']}: {e}")
                    errors += 1

        self.update_state(last_data_date=str(datetime.now().date()))
        return {
            "inserted": inserted,
            "updated": 0,
            "errors": errors,
            "message": f"Academic: {inserted} new papers from {total} feeds",
        }

    def _fetch_feed(self, db, feed_info: dict) -> int:
        """Parse an RSS feed and insert new papers."""
        count = 0
        try:
            feed = feedparser.parse(feed_info["url"])

            for entry in feed.entries[:30]:
                title = entry.get("title", "").strip()
                url = entry.get("link", "").strip()
                summary = entry.get("summary", entry.get("description", "")).strip()

                if not title:
                    continue

                # Strip HTML from summary
                if summary:
                    summary = BeautifulSoup(summary, "html.parser").get_text()[:1000]

                # Parse publication date
                published = None
                if entry.get("published_parsed"):
                    try:
                        published = datetime(*entry.published_parsed[:6])
                    except (TypeError, ValueError):
                        pass
                elif entry.get("updated_parsed"):
                    try:
                        published = datetime(*entry.updated_parsed[:6])
                    except (TypeError, ValueError):
                        pass

                # Extract authors
                authors = []
                if entry.get("authors"):
                    authors = [a.get("name", "") for a in entry.authors if a.get("name")]
                elif entry.get("author"):
                    authors = [entry.author]

                # Extract categories/tags
                categories = []
                if entry.get("tags"):
                    categories = [t.get("term", "") for t in entry.tags if t.get("term")]

                body_text = fetch_full_text(url) if url else None
                if body_text:
                    time.sleep(1)  # Rate limit Firecrawl calls

                was_new = self._upsert_news_item(
                    db,
                    source="academic",
                    source_name=feed_info["source_name"],
                    title=title,
                    url=url,
                    body_text=body_text,
                    summary=summary,
                    meta={
                        "authors": authors,
                        "categories": categories,
                        "feed": feed_info["name"],
                    },
                    published_at=published,
                )
                if was_new:
                    count += 1

        except Exception as e:
            self.logger.warning(f"Feed parse failed for {feed_info['name']}: {e}")

        return count
