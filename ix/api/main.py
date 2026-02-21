"""
Main FastAPI application.
"""

from contextlib import asynccontextmanager
import pytz
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from ix.db.conn import ensure_connection, conn
from ix.misc import get_logger
from ix.utils.logger import setup_antigravity_logging
from ix.misc.task import run_daily_tasks

# Initialize Mandatory Antigravity Logger
logger = setup_antigravity_logging(service_name="backend")
# logger = get_logger(__name__)

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

    # Telegram Scraping is now triggered manually via the app button
    # from ix.misc.telegram import scrape_all_channels
    #
    # scheduler.add_job(
    #     scrape_all_channels,
    #     CronTrigger(minute="*/30", timezone=KST),  # Run every 30 minutes
    #     id="telegram_scrape_routine",
    #     replace_existing=True,
    #     misfire_grace_time=300,
    # )
    # logger.info("Scheduled 'scrape_all_channels' for every 30 minutes")

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


@app.middleware("http")
async def db_session_middleware(request, call_next):
    """Ensure scoped session is removed after each request."""
    try:
        response = await call_next(request)
        return response
    finally:
        if conn.Session:
            conn.Session.remove()


# Root endpoint removed as Dash handles "/"


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "Investment-X API"}


@app.get("/api/test-error")
async def test_error():
    """Endpoint to test error handling."""
    raise Exception("Critical test failure")


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


from starlette.exceptions import HTTPException as StarletteHTTPException


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    """Handle FastAPI/Starlette HTTPExceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "Client Error" if exc.status_code < 500 else "Server Error",
            "detail": exc.detail,
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global catch-all for unhandled exceptions."""
    try:
        logger.exception(f"Unhandled exception: {exc}")
    except Exception as log_err:
        import sys

        print(
            f"CRITICAL: Logger failed inside exception handler: {log_err}",
            file=sys.stderr,
        )
        import traceback

        traceback.print_exc()

    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


# Include routers with error handling
try:
    from ix.api.routers import (
        auth,
        timeseries,
        series,
        evaluation,
        task,
        risk,
        news,
        custom,
        insights,
        technical,
    )

    logger.info("Importing routers...")
    app.include_router(auth.router, prefix="/api", tags=["Authentication"])
    app.include_router(timeseries.router, prefix="/api", tags=["Timeseries"])
    app.include_router(series.router, prefix="/api", tags=["Series"])
    app.include_router(evaluation.router, prefix="/api", tags=["Evaluation"])
    app.include_router(task.router, prefix="/api", tags=["Tasks"])
    app.include_router(risk.router, prefix="/api", tags=["Risk"])
    app.include_router(news.router, prefix="/api", tags=["News"])
    app.include_router(custom.router, prefix="/api", tags=["Custom"])
    app.include_router(insights.router, prefix="/api", tags=["Insights"])
    app.include_router(technical.router, prefix="/api", tags=["Technical"])
    from ix.api.routers import dashboard

    app.include_router(dashboard.router, prefix="/api/v1", tags=["Dashboard"])
    logger.info("Routers registered successfully")

    # Legacy Dash chartbook mount removed with charts table decommission.

except Exception as e:
    import traceback

    traceback.print_exc()
    logger.error(f"Failed to import or register routers: {e}", exc_info=True)
    # Re-raise so the app fails to start if routers are broken
    raise e


# Serve SPA - Static Files
import os


# Try to find static directory
cwd_static = os.path.join(os.getcwd(), "static")
root_static = "/app/static"
api_relative_static = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "../../static"
)

static_dir = None
for p in [cwd_static, root_static, api_relative_static]:
    if os.path.exists(p):
        static_dir = p
        break

if static_dir:
    logger.info(f"Serve static frontend from {static_dir}")

    # Mount /_next first
    if os.path.exists(os.path.join(static_dir, "_next")):
        app.mount(
            "/_next",
            StaticFiles(directory=os.path.join(static_dir, "_next")),
            name="next_assets",
        )

    # Catch-all for other static files or SPA index.html
    # NOTE: This must be below all API routes
    @app.get("/")
    async def serve_root():
        return FileResponse(os.path.join(static_dir, "index.html"))

    @app.get("/api/debug-fs")
    async def debug_fs():
        import subprocess

        try:
            # Safe ls listing
            files = os.listdir(os.getcwd())
            static_exists = os.path.exists(static_dir)
            static_content = os.listdir(static_dir) if static_exists else []
            return {
                "cwd": os.getcwd(),
                "static_dir": static_dir,
                "exists": static_exists,
                "root_files": files,
                "static_files": static_content,
            }
        except Exception as e:
            return {"error": str(e)}

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # 1. Check if the file exists as is
        file_path = os.path.join(static_dir, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)

        # 2. Check if appending .html works (for Next.js static export)
        html_path = f"{file_path}.html"
        if os.path.isfile(html_path):
            return FileResponse(html_path)

        # 3. Check if it's a directory with index.html (trailingSlash: true)
        dir_index_path = os.path.join(file_path, "index.html")
        if os.path.isfile(dir_index_path):
            return FileResponse(dir_index_path)

        # Fallback to root index.html
        return FileResponse(os.path.join(static_dir, "index.html"))

else:
    logger.info("Static directory not found, running API only mode")


# Debug Endpoint - Keep GLOBAL so it always works
@app.get("/api/debug-fs")
async def debug_fs():
    import os

    try:
        # Safe ls listing
        files = os.listdir(os.getcwd())
        static_exists = static_dir and os.path.exists(static_dir)
        static_content = os.listdir(static_dir) if static_exists else []
        return {
            "cwd": os.getcwd(),
            "static_dir": static_dir,
            "exists": static_exists,
            "root_files": files,
            "static_files": static_content,
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
