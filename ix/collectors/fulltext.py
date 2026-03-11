"""Shared Firecrawl full-text extraction utility.

Provides a lazy-initialized Firecrawl client and a helper to scrape
article URLs into markdown. Gracefully degrades if FIRECRAWL_API_KEY
is not set — collectors continue working without full text.
"""

import logging
import os

logger = logging.getLogger("collector.fulltext")

_client = None


def get_firecrawl():
    """Return a lazy-initialized Firecrawl client, or None if no API key."""
    global _client
    if _client is None:
        key = os.environ.get("FIRECRAWL_API_KEY")
        if not key:
            return None
        from firecrawl import Firecrawl

        _client = Firecrawl(api_key=key)
    return _client


def fetch_full_text(url: str, timeout: int = 30) -> str | None:
    """Scrape a URL via Firecrawl and return markdown content.

    Returns None if Firecrawl is unavailable or the scrape fails.
    """
    if not url:
        return None

    client = get_firecrawl()
    if not client:
        return None

    try:
        doc = client.scrape(url, timeout=timeout, only_main_content=True)
        if doc and doc.markdown:
            return doc.markdown
        return None
    except Exception as e:
        logger.warning(f"Firecrawl scrape failed for {url}: {e}")
        return None
