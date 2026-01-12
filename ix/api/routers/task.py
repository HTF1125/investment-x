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
