from sqlalchemy import Column, Date, DateTime, Text, LargeBinary, func, text
from sqlalchemy.orm import deferred
from sqlalchemy.dialects.postgresql import JSONB, UUID
from ix.db.conn import Base


class ResearchReport(Base):
    """Stores NotebookLM-generated macro research reports."""

    __tablename__ = "research_report"

    id = Column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    date = Column(Date, unique=True, nullable=False, index=True)
    briefing = Column(Text)
    risk_scorecard = Column(Text)
    takeaways = Column(Text)
    infographic = deferred(Column(LargeBinary))
    slide_deck = deferred(Column(LargeBinary))
    sources = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
