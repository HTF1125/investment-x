from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from ix.db.conn import Base


class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(128), primary_key=True)
    value = Column(JSONB, nullable=False)
    updated_at = Column(
        DateTime, nullable=False, default=func.now(), onupdate=func.now()
    )
