"""
Simple task scheduler for running the daily() function every hour.
"""

import atexit
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

from ix.misc.task import daily
from ix.misc.terminal import get_logger

logger = get_logger(__name__)


class TaskScheduler:
    """Simple scheduler class for managing the daily() task."""

    def __init__(self):
        """Initialize the TaskScheduler."""
        # Initialize the scheduler
        self.scheduler = BackgroundScheduler(
            jobstores={"default": MemoryJobStore()},
            executors={"default": ThreadPoolExecutor(max_workers=2)},
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 30,
            },
            timezone="UTC",
        )

        # Register cleanup on exit
        atexit.register(self.shutdown)

        logger.info("TaskScheduler initialized")

    def start(self):
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("TaskScheduler started")
        else:
            logger.warning("TaskScheduler is already running")

    def shutdown(self):
        """Shutdown the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=True)
            logger.info("TaskScheduler shutdown")

    def add_hourly_task(self, func, minute: int = 0, job_id: Optional[str] = None):
        """Add an hourly scheduled task."""
        if job_id is None:
            job_id = f"hourly_{func.__name__}_{minute}"

        trigger = CronTrigger(minute=minute)

        self.scheduler.add_job(
            func=func,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            name=f"Hourly {func.__name__}",
        )

        logger.info(
            f"Added hourly task '{job_id}' to run at minute {minute:02d} of every hour"
        )

    def setup_hourly_task(self, minute: int = 0):
        """Set up hourly task for the daily function."""
        self.add_hourly_task(
            func=daily,
            minute=minute,
            job_id="hourly_daily_task",
        )
        logger.info(
            f"Hourly task configured - daily() function runs every hour at minute {minute}"
        )

    def list_jobs(self):
        """List all scheduled jobs."""
        jobs = self.scheduler.get_jobs()
        if not jobs:
            logger.info("No scheduled jobs found")
            return

        logger.info("Scheduled jobs:")
        for job in jobs:
            logger.info(f"  - {job.id}: {job.name} (Next run: {job.next_run_time})")


# Global scheduler instance
_scheduler_instance: Optional[TaskScheduler] = None


def get_scheduler() -> TaskScheduler:
    """Get the global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = TaskScheduler()
    return _scheduler_instance


def start_scheduler(minute: int = 0):
    """Start the global scheduler to run daily() function every hour."""
    scheduler = get_scheduler()
    scheduler.setup_hourly_task(minute=minute)
    scheduler.start()
    scheduler.list_jobs()  # Show configured jobs
    return scheduler


def stop_scheduler():
    """Stop the global scheduler."""
    global _scheduler_instance
    if _scheduler_instance:
        _scheduler_instance.shutdown()
        _scheduler_instance = None
