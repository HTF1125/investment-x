from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from ix.db.conn import Base


class CollectorState(Base):
    """Tracks incremental fetch state per collector to avoid re-downloading."""

    __tablename__ = "collector_state"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    collector_name = Column(String(100), unique=True, nullable=False, index=True)
    last_fetch_at = Column(DateTime, nullable=True)
    last_success_at = Column(DateTime, nullable=True)
    last_error = Column(String, nullable=True)
    last_data_date = Column(String(50), nullable=True)
    state = Column(JSONB, default=dict)
    fetch_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
