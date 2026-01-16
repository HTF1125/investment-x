from fastapi import APIRouter, BackgroundTasks
from ix.misc.task import daily, send_data_reports

router = APIRouter()


@router.post("/task/daily")
async def run_daily_task(background_tasks: BackgroundTasks):
    """
    Manually trigger the daily task to run in the background.
    """
    background_tasks.add_task(daily)
    return {"message": "Daily task triggered in background"}


@router.post("/task/report")
async def run_report_task(background_tasks: BackgroundTasks):
    """
    Manually trigger the report sending task in the background.
    """
    background_tasks.add_task(send_data_reports)
    return {"message": "Report sending task triggered in background"}


@router.get("/task/telegram")
async def get_telegram_messages(channel: str = None, limit: int = 1000):
    """
    Get recent Telegram messages.
    If channel is not specified, returns messages from all channels in last 24 hours.
    """
    from ix.db.conn import Session
    from ix.db.models import TelegramMessage
    from datetime import datetime, timedelta

    since_date = datetime.utcnow() - timedelta(hours=24)

    with Session() as session:
        query = session.query(TelegramMessage)

        if channel:
            query = query.filter(TelegramMessage.channel_name == channel)
        else:
            # If no channel specified, default to last 24 hours
            query = query.filter(TelegramMessage.date >= since_date)

        messages = query.order_by(TelegramMessage.date.desc()).limit(limit).all()
        data = [
            {
                "id": str(m.id),
                "channel": m.channel_name,
                "message_id": m.message_id,
                "date": m.date,
                "message": m.message,
                "views": m.views,
            }
            for m in messages
        ]
        return data
