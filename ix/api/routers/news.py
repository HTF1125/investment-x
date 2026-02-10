from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List
from ix.db.conn import get_session
from ix.db.models import TelegramMessage
from pydantic import BaseModel

router = APIRouter()


class TelegramMessageSchema(BaseModel):
    id: str
    channel_name: str
    message_id: int
    date: datetime
    message: str | None
    views: int | None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/news/telegram", response_model=List[TelegramMessageSchema])
def get_recent_telegram_messages(hours: int = 24, db: Session = Depends(get_session)):
    """
    Returns Telegram messages from the last X hours (default 24).
    """
    cutoff = datetime.utcnow() - timedelta(hours=hours)

    messages = (
        db.query(TelegramMessage)
        .filter(TelegramMessage.date >= cutoff)
        .order_by(TelegramMessage.date.desc())
        .all()
    )

    return messages
