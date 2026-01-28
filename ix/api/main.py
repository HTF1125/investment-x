"""
Main FastAPI application.
"""

from contextlib import asynccontextmanager
import pytz
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ix.db.conn import ensure_connection
from ix.misc import get_logger
from ix.misc.task import run_daily_tasks

logger = get_logger(__name__)

# Timezone config
KST = pytz.timezone("Asia/Seoul")

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for FastAPI app lifecycle.
    Starts the scheduler on startup and shuts it down on shutdown.
    Also handles database connection initialization if needed.
    """
    logger.info("Initializing FastAPI application...")
    logger.info("Starting scheduler...")

    # Schedule run_daily_tasks() at 07:00 KST
    scheduler.add_job(
        run_daily_tasks,
        CronTrigger(hour=7, minute=0, timezone=KST),
        id="daily_routine",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    logger.info("Scheduled 'run_daily_tasks' for 07:00 KST")

    # Schedule Telegram Scraping (e.g., Every hour)
    from ix.misc.telegram import scrape_channel

    # We must wrap async function if the scheduler expects a coroutine or callable.
    # AsyncIOScheduler handles async functions natively.
    # Define channels to scrape
    # Define channels to scrape
    channels_to_scrape = [
        "t.me/HANAchina",
        "t.me/EMchina",
        "t.me/hermitcrab41",
        "t.me/Yeouido_Lab",
        "t.me/EarlyStock1",
        "t.me/globaletfi",
        "t.me/hanaglobalbottomup",
        "t.me/hanabondview",
        "t.me/KISemicon",
        "t.me/Inhwan_Ha",
        "t.me/jkc123",
        "t.me/sskimfi",
        "t.me/strategy_kis",
        "t.me/globalequity1",
        "t.me/sypark_strategy",
        "t.me/bottomupquantapproach",
        "t.me/TNBfolio",
        "t.me/ReutersWorldChannel",
        "t.me/bloomberg",
        "t.me/FinancialNews",
        "t.me/BloombergQ",
        "t.me/wall_street_journal_news",
        "t.me/globalbobo",
        "t.me/aetherjapanresearch",
        "t.me/shinhanresearch",
        "t.me/kiwoom_semibat",
        "t.me/lim_econ",
        "t.me/Jstockclass",
        "t.me/merITz_tech",
        "t.me/growthresearch",
        "t.me/awake_schedule",
        "t.me/eugene2team",
        "t.me/Brain_And_Body_Research",
    ]

    async def scrape_routine():
        for ch in channels_to_scrape:
            # Add a small delay between channels to be polite
            await scrape_channel(ch, limit=50)
            import asyncio

            await asyncio.sleep(2)

    scheduler.add_job(
        scrape_routine,
        CronTrigger(minute="*/5", timezone=KST),  # Run every 5 minutes
        id="telegram_scrape_routine",
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info("Scheduled 'scrape_routine' for every 5 minutes")

    from ix.misc.task import send_daily_market_brief
    
    scheduler.add_job(
        send_daily_market_brief,
        CronTrigger(minute=0, timezone=KST), # Run every hour at minute 0
        id="market_brief_hourly",
        replace_existing=True,
        misfire_grace_time=300
    )
    logger.info("Scheduled 'send_daily_market_brief' for every hour")

    scheduler.start()

    logger.info("FastAPI application started")
    yield

    logger.info("Shutting down scheduler...")
    scheduler.shutdown()


# Create FastAPI app
app = FastAPI(
    title="Investment-X API",
    description="API for Investment-X dashboard and data management",
    version="1.0.0",
    lifespan=lifespan,
)

logger.info("FastAPI app created successfully")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint showing recent news in a table."""
    from ix.db.conn import Session
    from ix.db.models import TelegramMessage

    from datetime import datetime, timedelta

    # DB stores KST. We want last 24 hours relative to current KST time.
    # Current KST = UTC + 9
    now_kst = datetime.utcnow() + timedelta(hours=9)
    since_date = now_kst - timedelta(hours=24)

    with Session() as session:
        messages = (
            session.query(TelegramMessage)
            .filter(TelegramMessage.date >= since_date)
            .order_by(TelegramMessage.date.desc())
            .limit(2000)
            .all()
        )

    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Investment-X News</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            table { border-collapse: collapse; width: 100%; }
            th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
            th { background-color: #f2f2f2; position: sticky; top: 0; }
            tr:nth-child(even) { background-color: #f9f9f9; }
            tr:hover { background-color: #f1f1f1; }
            .date { white-space: nowrap; color: #666; font-size: 0.9em; }
            .channel { font-weight: bold; color: #2c3e50; }
            .message { white-space: pre-wrap; word-wrap: break-word; }
        </style>
    </head>
    <body>
        <h2>Latest Telegram News</h2>
        <table>
            <thead>
                <tr>
                    <th width="150">Date (KST)</th>
                    <th width="150">Channel</th>
                    <th>Message</th>
                </tr>
            </thead>
            <tbody>
    """

    for m in messages:
        # DB is now KST, so just format directly
        dt_str = m.date.strftime("%Y-%m-%d %H:%M") if m.date else ""
        # Clean message text slightly if needed
        msg_text = m.message or ""

        row = f"""
                <tr>
                    <td class="date">{dt_str}</td>
                    <td class="channel">{m.channel_name}</td>
                    <td class="message">{msg_text}</td>
                </tr>
        """
        html_content += row

    html_content += """
            </tbody>
        </table>
    </body>
    </html>
    """
    return html_content


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Investment-X API"}


@app.get("/api/jobs")
async def get_jobs():
    """List currently scheduled jobs"""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append(
            {
                "id": job.id,
                "next_run_time": str(job.next_run_time),
                "func": job.func.__name__,
            }
        )
    return {"jobs": jobs}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


# Include routers with error handling
try:
    from ix.api.routers import auth, timeseries, series, evaluation, task, risk

    logger.info("Importing routers...")
    app.include_router(auth.router, prefix="/api", tags=["Authentication"])
    app.include_router(timeseries.router, prefix="/api", tags=["Timeseries"])
    app.include_router(series.router, prefix="/api", tags=["Series"])
    app.include_router(evaluation.router, prefix="/api", tags=["Evaluation"])
    app.include_router(task.router, prefix="/api", tags=["Tasks"])
    app.include_router(risk.router, prefix="/api", tags=["Risk"])
    logger.info("Routers registered successfully")

except Exception as e:
    import traceback

    traceback.print_exc()
    logger.error(f"Failed to import or register routers: {e}", exc_info=True)
    # Re-raise so the app fails to start if routers are broken
    raise e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
