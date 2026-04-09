from sqlalchemy import Column, Date, DateTime, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from ix.db.conn import Base


class Briefings(Base):
    """Daily macro intelligence briefing."""

    __tablename__ = "briefings"

    id = Column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    date = Column(Date, unique=True, nullable=False, index=True)
    briefing = Column(Text)
    sources = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
