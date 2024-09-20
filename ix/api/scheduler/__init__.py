from apscheduler.schedulers.background import (
    BackgroundScheduler,
)  # runs tasks in the background
from apscheduler.triggers.cron import (
    CronTrigger,
)  # allows us to specify a recurring time for execution


from ix import task

# Set up the scheduler
scheduler = BackgroundScheduler()
trigger = CronTrigger(minute=37)  # midnight every day
scheduler.add_job(task.run, trigger)
scheduler.start()
