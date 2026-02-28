from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text, text, Index, Boolean
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
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
    discovered_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# GIN index for JSONB symbols containment queries (@>)
Index("ix_news_items_symbols_gin", NewsItem.symbols, postgresql_using="gin")

# Full-Text Search Index for title and summary
# Note: In a production environment with high volume, consider a stored TSVector column.
# For now, we use a functional index for improved search performance on existing text.
Index(
    "ix_news_items_fts",
    text("to_tsvector('english', coalesce(title, '') || ' ' || coalesce(summary, ''))"),
    postgresql_using="gin",
)

