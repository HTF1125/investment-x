from fastapi import APIRouter, BackgroundTasks
from ix.misc.task import daily, send_data_reports, send_daily_market_brief

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
    from ix.misc.telegram import scrape_all_channels

    background_tasks.add_task(scrape_all_channels)
    return {"message": "Telegram scraping task triggered in background"}


@router.post("/task/refresh-charts")
async def run_refresh_charts_task(background_tasks: BackgroundTasks):
    """
    Manually trigger a refresh of all charts in the background.
    """
    from ix.misc.task import refresh_all_charts

    background_tasks.add_task(refresh_all_charts)
    return {"message": "Chart refresh task triggered in background"}
