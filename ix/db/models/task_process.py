from sqlalchemy import Column, String, DateTime, text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from ix.db.conn import Base


class TaskProcess(Base):
    """Persistent task process tracker."""

    __tablename__ = "task_process"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    message = Column(String, nullable=True)
    progress = Column(String, nullable=True)
    user_id = Column(
        UUID(as_uuid=False), ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )


Index("ix_task_process_name_status", TaskProcess.name, TaskProcess.status)
