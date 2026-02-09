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

    # Schedule Telegram Scraping (e.g., Every 5 minutes)
    from ix.misc.telegram import scrape_all_channels

    scheduler.add_job(
        scrape_all_channels,
        CronTrigger(minute="*/30", timezone=KST),  # Run every 30 minutes
        id="telegram_scrape_routine",
        replace_existing=True,
        misfire_grace_time=300,
    )
    logger.info("Scheduled 'scrape_all_channels' for every 30 minutes")

    # from ix.misc.task import send_daily_market_brief

    # scheduler.add_job(
    #     send_daily_market_brief,
    #     CronTrigger(hour="1,7,13,19", minute=0, timezone=KST),
    #     id="market_brief_6h",
    #     replace_existing=True,
    #     misfire_grace_time=300,
    # )
    # logger.info("Scheduled 'send_daily_market_brief' for every 6 hours (1, 7, 13, 19 KST)")

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

# Root endpoint removed as Dash handles "/"



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
    from ix.api.routers import auth, timeseries, series, evaluation, task, risk, charts

    logger.info("Importing routers...")
    app.include_router(auth.router, prefix="/api", tags=["Authentication"])
    app.include_router(timeseries.router, prefix="/api", tags=["Timeseries"])
    app.include_router(series.router, prefix="/api", tags=["Series"])
    app.include_router(evaluation.router, prefix="/api", tags=["Evaluation"])
    app.include_router(task.router, prefix="/api", tags=["Tasks"])
    app.include_router(risk.router, prefix="/api", tags=["Risk"])
    app.include_router(charts.router, prefix="/api", tags=["Charts"])
    logger.info("Routers registered successfully")
    
    # Mount Dash app at root "/" AFTER all API routers
    # This ensures /api/... routes take precedence over Dash's catch-all
    try:
        from starlette.middleware.wsgi import WSGIMiddleware
        from ix.api.dash_app import dash_app

        app.mount("/", WSGIMiddleware(dash_app.server))
        logger.info("Dash app mounted at /")
    except Exception as e:
        logger.warning(f"Failed to mount Dash app: {e}")

except Exception as e:
    import traceback

    traceback.print_exc()
    logger.error(f"Failed to import or register routers: {e}", exc_info=True)
    # Re-raise so the app fails to start if routers are broken
    raise e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
