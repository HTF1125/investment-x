from sqlalchemy import Column, String, Integer, DateTime, BigInteger, Text, text
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from ix.db.conn import Base


class TelegramMessage(Base):
    """Telegram Message model."""

    __tablename__ = "telegram_message"

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )
    # The channel/chat ID or username
    channel_name = Column(String, nullable=False, index=True)
    # The message ID within the channel
    message_id = Column(BigInteger, nullable=False)
    # Who sent it (if available/relevant)
    sender_id = Column(BigInteger, nullable=True)
    sender_name = Column(String, nullable=True)

    date = Column(DateTime, nullable=False, index=True)
    message = Column(Text, nullable=True)

    # Store other metadata if needed, like views
    views = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
