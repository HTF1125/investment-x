from sqlalchemy import Column, String, DateTime, Text, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from ix.db.conn import Base


class RuntimeLog(Base):
    """Application runtime logs persisted for admin inspection."""

    __tablename__ = "runtime_logs"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    level = Column(String(16), nullable=False, index=True)
    logger_name = Column(String(255), nullable=False, index=True)
    module = Column(String(255), nullable=True, index=True)
    function = Column(String(255), nullable=True)
    message = Column(Text, nullable=False)
    path = Column(Text, nullable=True)
    line_no = Column(Integer, nullable=True)
    service = Column(String(64), nullable=True, index=True)
    exception = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
