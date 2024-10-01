from apscheduler.schedulers.background import (
    BackgroundScheduler,
)
from apscheduler.triggers.cron import (
    CronTrigger,
)


from ix import task

# Set up the scheduler
scheduler = BackgroundScheduler()
trigger = CronTrigger(minute=37)
scheduler.add_job(task.run, trigger)
