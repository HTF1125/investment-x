"""ResearchFile ORM model."""

from sqlalchemy import Boolean, Column, DateTime, Integer, LargeBinary, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID

from ix.db.conn import Base


class ResearchFile(Base):
    """Uploaded research PDFs stored in the database."""

    __tablename__ = "research_files"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    filename = Column(String(512), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    content = Column(LargeBinary, nullable=False)
    summary = Column(Text, nullable=True)
    uploaded_by = Column(String(256), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False, index=True)
    deleted_at = Column(DateTime, nullable=True)
