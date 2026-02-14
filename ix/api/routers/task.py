from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, HTTPException
from ix.misc.task import (
    daily,
    send_data_reports,
    send_daily_market_brief,
    run_daily_tasks,
)

router = APIRouter()

# Global status tracker (simple in-memory)
task_status = {
    "daily": {"running": False, "last_run": None, "message": "Idle"},
    "telegram": {"running": False, "last_run": None, "message": "Idle"},
}


async def run_telegram_with_status():
    """Wrapper to update status during execution"""
    try:
        from ix.misc.telegram import scrape_all_channels

        task_status["telegram"]["running"] = True
        task_status["telegram"]["message"] = "Syncing Telegram channels..."

        await scrape_all_channels()

        task_status["telegram"]["message"] = "Completed successfully"
        task_status["telegram"]["last_run"] = datetime.now().isoformat()
    except Exception as e:
        task_status["telegram"]["message"] = f"Failed: {str(e)}"
    finally:
        task_status["telegram"]["running"] = False


async def run_daily_with_status():
    """Wrapper to update status during execution"""
    try:
        task_status["daily"]["running"] = True
        task_status["daily"]["message"] = "Running daily update..."

        # Execute the full daily routine
        run_daily_tasks()

        task_status["daily"]["message"] = "Completed successfully"
        task_status["daily"]["last_run"] = datetime.now().isoformat()
    except Exception as e:
        task_status["daily"]["message"] = f"Failed: {str(e)}"
    finally:
        task_status["daily"]["running"] = False


@router.get("/task/status")
async def get_task_status():
    """Get current status of tasks"""
    return task_status


@router.post("/task/daily")
async def run_daily_task(background_tasks: BackgroundTasks):
    """
    Manually trigger the full daily routine (update + refresh charts) in background.
    """
    if task_status["daily"]["running"]:
        raise HTTPException(status_code=400, detail="Daily task is already running")

    background_tasks.add_task(run_daily_with_status)
    return {"message": "Daily task triggered", "status": "started"}


@router.post("/task/report")
async def run_report_task(background_tasks: BackgroundTasks):
    """
    Manually trigger the report sending task in the background.
    """
    background_tasks.add_task(send_data_reports)
    return {"message": "Report sending task triggered in background"}


@router.post("/task/brief")
async def run_market_brief_task(background_tasks: BackgroundTasks):
    """
    Manually trigger the Daily Market Brief task in the background.
    """
    background_tasks.add_task(send_daily_market_brief)
    return {"message": "Daily Market Brief task triggered in background"}


@router.post("/task/telegram")
async def run_telegram_scrape_task(background_tasks: BackgroundTasks):
    """
    Trigger Telegram scraping for all configured channels in the background.
    """
    if task_status["telegram"]["running"]:
        raise HTTPException(status_code=400, detail="Telegram sync is already running")

    background_tasks.add_task(run_telegram_with_status)
    return {
        "message": "Telegram scraping task triggered in background",
        "status": "started",
    }


@router.post("/task/refresh-charts")
async def run_refresh_charts_task(background_tasks: BackgroundTasks):
    """
    Manually trigger a refresh of all charts in the background.
    """
    from ix.misc.task import refresh_all_charts

    background_tasks.add_task(refresh_all_charts)
    return {"message": "Chart refresh task triggered in background"}
