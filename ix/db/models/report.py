from sqlalchemy import Boolean, Column, String, DateTime, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from ix.db.conn import Base
from sqlalchemy.orm import relationship


class Report(Base):
    """A slide-based report with charts and narrative commentary."""

    __tablename__ = "reports"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id = Column(
        UUID(as_uuid=False),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(255), nullable=False, default="Untitled Report")
    description = Column(Text, nullable=True)
    slides = Column(JSONB, nullable=False, server_default=text("'[]'::jsonb"))
    settings = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    is_deleted = Column(Boolean, nullable=False, server_default=text("false"))
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    creator = relationship("User", foreign_keys=[user_id], lazy="select")

    @property
    def active_slides(self) -> list:
        """Return only non-deleted slides."""
        return [s for s in (self.slides or []) if not s.get("deleted")]

    @property
    def slide_count(self) -> int:
        return len(self.active_slides)


Index("ix_reports_updated_at", Report.updated_at.desc())
