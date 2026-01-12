"""
Main FastAPI application.
"""

from contextlib import asynccontextmanager
import pytz
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ix.db.conn import ensure_connection
from ix.misc import get_logger
from ix.misc.task import daily, send_data_reports

logger = get_logger(__name__)

# Timezone config
KST = pytz.timezone('Asia/Seoul')

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
    
    # Schedule daily() at 06:00 KST
    scheduler.add_job(
        daily, 
        CronTrigger(hour=6, minute=0, timezone=KST),
        id="daily_update",
        replace_existing=True
    )
    logger.info("Scheduled 'daily' task for 06:00 KST")

    # Schedule send_data_reports() at 07:00 KST
    scheduler.add_job(
        send_data_reports, 
        CronTrigger(hour=7, minute=0, timezone=KST),
        id="send_reports",
        replace_existing=True
    )
    logger.info("Scheduled 'send_data_reports' task for 07:00 KST")

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
    lifespan=lifespan
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


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Investment-X API", "status": "running"}


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Investment-X API"}


@app.get("/api/jobs")
async def get_jobs():
    """List currently scheduled jobs"""
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "next_run_time": str(job.next_run_time),
            "func": job.func.__name__
        })
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
