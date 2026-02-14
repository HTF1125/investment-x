import feedparser
import logging
from datetime import datetime
from sqlalchemy.orm import Session as SASession
from ix.db.conn import Session
from ix.db.models.financial_news import FinancialNews
from ix.misc import get_logger

logger = get_logger(__name__)

RSS_FEEDS = {
    "Yahoo Finance": "https://finance.yahoo.com/rss/",
    "CNBC Finance": "https://www.cnbc.com/id/10000664/device/rss/rss.html",
    "MarketWatch": "http://feeds.marketwatch.com/marketwatch/topstories/",
    "Investing.com": "https://www.investing.com/rss/news.rss",
    "WSJ Markets": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
}


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

            # Parse published date
            published_parsed = entry.get("published_parsed")
            if published_parsed:
                published_at = datetime(*published_parsed[:6])
            else:
                published_at = datetime.utcnow()

            # Check if exists
            exists = db.query(FinancialNews).filter(FinancialNews.url == link).first()
            if not exists:
                news_item = FinancialNews(
                    source=source_name,
                    title=title,
                    url=link,
                    published_at=published_at,
                    summary=summary,
                    content=summary,
                    news_type="general",
                )
                db.add(news_item)
                new_count += 1

        db.commit()
        logger.info(f"Saved {new_count} new articles from {source_name}")

    except Exception as e:
        logger.error(f"Error fetching {source_name}: {e}")


def run_news_scraping():
    """Run news scraping task."""
    with Session() as db:
        for name, url in RSS_FEEDS.items():
            fetch_rss_feed(name, url, db)


if __name__ == "__main__":
    run_news_scraping()
