from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Boolean, Index, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from ix.db.conn import Base
from sqlalchemy.orm import relationship


class Whiteboard(Base):
    """Model for storing user-created Excalidraw diagrams."""

    __tablename__ = "whiteboards"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    user_id = Column(
        UUID(as_uuid=False),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False, default="Untitled")
    scene_data = Column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    thumbnail = Column(Text, nullable=True)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    creator = relationship("User", foreign_keys=[user_id], lazy="joined")


Index("ix_whiteboards_updated_at", Whiteboard.updated_at.desc())
