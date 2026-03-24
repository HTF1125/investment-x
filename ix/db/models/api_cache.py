from sqlalchemy import Column, DateTime, String, text, func
from sqlalchemy.dialects.postgresql import JSONB
from ix.db.conn import Base


class ApiCache(Base):
    """Generic key-value cache table for expensive API responses.

    Usage:
        key: unique cache key (e.g. "technicals", "cacri-history")
        value: JSON-serialisable response payload
        updated_at: auto-set on insert/update — lets consumers decide freshness
    """

    __tablename__ = "api_cache"

    key = Column(String(255), primary_key=True)
    value = Column(JSONB, nullable=False, default=dict)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
