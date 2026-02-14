from sqlalchemy import Column, String, DateTime, Text, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
from ix.db.conn import Base


class FinancialNews(Base):
    """Financial News model for storing articles from various sources."""

    __tablename__ = "financial_news"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    source = Column(
        String, nullable=False, index=True
    )  # e.g. "Yahoo Finance", "Benzinga"
    title = Column(String, nullable=False)
    url = Column(String, unique=True, nullable=False)
    published_at = Column(DateTime, nullable=False, index=True)
    content = Column(Text, nullable=True)  # Full body or summary
    summary = Column(Text, nullable=True)  # Brief description
    tickers = Column(JSONB, default=list)  # List of related tickers
    news_type = Column(
        String, default="general"
    )  # e.g. "analyst_rating", "earnings", "general"

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
