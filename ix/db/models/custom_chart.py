from sqlalchemy import Column, String, DateTime, Text, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func
from ix.db.conn import Base
from sqlalchemy.orm import relationship


class CustomChart(Base):
    """
    Model for storing user-defined custom charts.
    """

    __tablename__ = "charts"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=func.gen_random_uuid()
    )
    created_by_user_id = Column(
        UUID(as_uuid=False), ForeignKey("user.id"), nullable=True, index=True
    )

    code = Column(Text, nullable=False)  # The Python code
    name = Column(String, nullable=True)  # Name of the analysis
    category = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    tags = Column(JSONB, default=list)

    figure = Column(JSONB, nullable=True)  # Cached execution result
    chart_style = Column(String(32), nullable=True)  # Visual style preset (default/minimal/terminal/presentation)
    public = Column(Boolean, default=True, nullable=False)  # Visible to all users

    # "order" is a reserved keyword in SQL, so we quote it or use a different name in DB.
    # Since we added column "order", we map it here.
    from sqlalchemy import Integer

    rank = Column("order", Integer, default=0, index=True)

    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    creator = relationship("User", foreign_keys=[created_by_user_id], lazy="joined")
