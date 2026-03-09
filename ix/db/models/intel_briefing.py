"""SQLAlchemy model for daily synthesized intel briefings."""

from sqlalchemy import Column, Date, DateTime, Text, text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from ix.db.conn import Base


class IntelBriefing(Base):
    """Daily synthesized intel briefing from all sources (News, Telegram, YouTube)."""

    __tablename__ = "intel_briefing"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    date = Column(Date, nullable=False, unique=True, index=True)
    headlines = Column(JSONB, nullable=False, default=list)
    insights = Column(JSONB, nullable=False, default=list)
    themes = Column(JSONB, nullable=False, default=list)
    raw_input_summary = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
