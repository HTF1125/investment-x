from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from ix.db.conn import Base


class NewsItem(Base):
    """
    Unified multi-source news storage.
    Use `meta`/`raw` for source-specific payloads (RSS/Reddit/GDELT/EDGAR).
    """

    __tablename__ = "news_items"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    source = Column(String, nullable=False, index=True)  # rss, reddit, gdelt, sec_edgar
    source_name = Column(String, nullable=True, index=True)  # e.g. Yahoo Finance
    source_item_id = Column(String, nullable=True, index=True)

    url = Column(Text, nullable=True)
    url_hash = Column(String(64), nullable=True, unique=True, index=True)

    title = Column(Text, nullable=False)
    body_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    lang = Column(String(16), nullable=True, index=True)

    symbols = Column(JSONB, nullable=False, default=list)  # e.g. ["AAPL", "SPY"]
    meta = Column(JSONB, nullable=False, default=dict)  # normalized source-specific fields
    raw = Column(JSONB, nullable=False, default=dict)  # original payload for audit/reparse

    published_at = Column(DateTime, nullable=True, index=True)
    discovered_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

