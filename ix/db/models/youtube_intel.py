from sqlalchemy import Column, String, DateTime, Text, Integer, Boolean, text
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from ix.db.conn import Base


class YouTubeIntel(Base):
    """Persisted YouTube video intelligence summaries."""

    __tablename__ = "youtube_intel"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    video_id = Column(String, nullable=False, unique=True, index=True)
    channel = Column(String, nullable=False, index=True)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    published_at = Column(DateTime, nullable=False, index=True)
    duration_seconds = Column(Integer, nullable=True, index=True)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    deleted_at = Column(DateTime, nullable=True, index=True)
    summary = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
