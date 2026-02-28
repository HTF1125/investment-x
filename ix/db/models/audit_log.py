from sqlalchemy import Column, String, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from ix.db.conn import Base

class AuditLog(Base):
    """
    Tracks changes to critical data for security and debugging.
    """
    __tablename__ = "audit_logs"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True
    )
    table_name = Column(String(64), nullable=False, index=True)
    record_id = Column(String(64), nullable=False, index=True)
    action = Column(String(16), nullable=False, index=True)  # CREATE, UPDATE, DELETE, RESTORE
    
    # Store what changed: {"field": ["old_value", "new_value"]}
    changes = Column(JSONB, nullable=True)
    
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
