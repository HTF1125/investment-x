from sqlalchemy import Column, String, DateTime, Text, ForeignKey, Boolean, Integer, Index, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ix.db.conn import Base

class InvestmentNote(Base):
    """
    Unified Notion-like block-based investment note.
    Everything (text, images, charts, links) is stored in the 'body' JSONB column.
    """
    __tablename__ = "investment_notes"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String(255), nullable=False, default="Untitled Note")
    
    # The 'body' stores an ordered list of blocks:
    # [
    #   {"type": "text", "value": "Analysis..."},
    #   {"type": "image", "id": "uuid", "data": "base64...", "filename": "..."},
    #   {"type": "chart", "chart_id": "..."},
    #   {"type": "link", "url": "..."}
    # ]
    body = Column(JSONB, nullable=False, server_default='[]')
    
    pinned = Column(Boolean, nullable=False, default=False, index=True)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

# GIN index for deep searching within the block-based body
Index("ix_investment_notes_body_gin", InvestmentNote.body, postgresql_using="gin")

# Full-Text Search Index for title and text blocks inside body
# This uses a functional index to extract text from the JSONB body for searching
Index(
    "ix_investment_notes_fts",
    text("to_tsvector('english', coalesce(title, '') || ' ' || (SELECT string_agg(elem->>'value', ' ') FROM jsonb_array_elements(body) AS elem WHERE elem->>'type' = 'text'))"),
    postgresql_using="gin",
)
