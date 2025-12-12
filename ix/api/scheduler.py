from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from ix.misc import get_logger
from ix.misc.task import daily

logger = get_logger(__name__)

scheduler = AsyncIOScheduler()

def start_scheduler():
    try:
        logger.info("Starting background scheduler...")
        # Add the daily task to run every hour
        # APScheduler will automatically run this synchronous function in a thread pool
        scheduler.add_job(
            daily,
            trigger=IntervalTrigger(hours=1),
            id="daily_task",
            name="Run daily misc task every hour",
            replace_existing=True,
        )
        scheduler.start()
        logger.info("Scheduler started successfully.")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)

def stop_scheduler():
    try:
        logger.info("Stopping background scheduler...")
        scheduler.shutdown()
        logger.info("Scheduler stopped.")
    except Exception as e:
        logger.error(f"Failed to stop scheduler: {e}", exc_info=True)
