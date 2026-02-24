from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Boolean, LargeBinary
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ix.db.conn import Base


class InvestmentNote(Base):
    __tablename__ = "investment_notes"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String(255), nullable=False, default="Untitled Note")
    content = Column(Text, nullable=False, default="")
    links = Column(JSONB, nullable=False, default=list)
    pinned = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    images = relationship(
        "InvestmentNoteImage",
        back_populates="note",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )


class InvestmentNoteImage(Base):
    __tablename__ = "investment_note_images"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    note_id = Column(
        UUID(as_uuid=False),
        ForeignKey("investment_notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    filename = Column(String(255), nullable=True)
    content_type = Column(String(128), nullable=False, default="image/png")
    data = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    note = relationship("InvestmentNote", back_populates="images", lazy="joined")
