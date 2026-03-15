from sqlalchemy import Boolean, Column, String, DateTime, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from ix.db.conn import Base
from sqlalchemy.orm import relationship


class ChartPack(Base):
    """A curated collection of chart configurations (like FRED chart packs)."""

    __tablename__ = "chart_packs"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id = Column(
        UUID(as_uuid=False),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False, default="Untitled Pack")
    description = Column(Text, nullable=True)
    charts = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    is_published = Column(Boolean, nullable=False, server_default=text("false"))
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    creator = relationship("User", foreign_keys=[user_id], lazy="select")


Index("ix_chart_packs_updated_at", ChartPack.updated_at.desc())
