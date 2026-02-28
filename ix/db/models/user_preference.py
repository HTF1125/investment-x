from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from ix.db.conn import Base
from sqlalchemy.orm import relationship

class UserPreference(Base):
    """
    Stores user-specific UI and application preferences.
    """
    __tablename__ = "user_preferences"

    user_id = Column(
        UUID(as_uuid=False), 
        ForeignKey("user.id", ondelete="CASCADE"), 
        primary_key=True
    )
    theme = Column(String(20), default="system")  # light, dark, system
    language = Column(String(10), default="en")
    timezone = Column(String(50), default="UTC")
    
    # Flexible storage for miscellaneous UI settings (dashboard layout, etc.)
    settings = Column(JSONB, default=dict, nullable=False)

    user = relationship("User", backref="preferences", uselist=False)
