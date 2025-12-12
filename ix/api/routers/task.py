from fastapi import APIRouter, BackgroundTasks
from ix.misc.task import daily

router = APIRouter()

@router.post("/task/daily")
async def run_daily_task(background_tasks: BackgroundTasks):
    """
    Manually trigger the daily task to run in the background.
    """
    background_tasks.add_task(daily)
    return {"message": "Daily task triggered in background"}
