"""
Main FastAPI application.
"""
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse, FileResponse, ORJSONResponse, Response
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import text
from slowapi.errors import RateLimitExceeded

from ix.db.conn import ensure_connection, conn
from ix.common.logger import setup_logging

logger = setup_logging(service_name="backend")

scheduler = AsyncIOScheduler(timezone="UTC")


def _run_startup_migrations() -> None:
    """Run all schema migrations in a single transaction."""
    if not ensure_connection():
        logger.warning("Skipping startup migrations — DB connection unavailable.")
        return

    try:
        from ix.db.conn import Base as ModelBase

        # Import all models so metadata knows about them
        import ix.db.models  # noqa: F401

        # Create any missing tables in one call
        ModelBase.metadata.create_all(bind=conn.engine, checkfirst=True)

        # Run ALTER TABLE migrations in a single transaction
        with conn.engine.begin() as db:
            # User table columns
            user_exists = db.execute(
                text("SELECT to_regclass('public.\"user\"')")
            ).scalar()
            if user_exists:
                db.execute(text(
                    'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS role VARCHAR(32) DEFAULT \'general\''
                ))
                db.execute(text(
                    'ALTER TABLE "user" ADD COLUMN IF NOT EXISTS preferences JSONB NOT NULL DEFAULT \'{}\'::jsonb'
                ))
                db.execute(text(
                    "CREATE INDEX IF NOT EXISTS ix_user_role ON \"user\" (role)"
                ))

            # Create a view so old code can still read from research_report
            db.execute(text(
                "CREATE OR REPLACE VIEW research_report AS SELECT * FROM briefings"
            ))

            # Chart packs columns
            db.execute(text(
                "ALTER TABLE chart_packs ADD COLUMN IF NOT EXISTS is_published BOOLEAN NOT NULL DEFAULT false"
            ))
            db.execute(text(
                "ALTER TABLE chart_packs ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT false"
            ))
            db.execute(text(
                "ALTER TABLE chart_packs ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMP"
            ))

        logger.info("Startup migrations completed.")
    except Exception as exc:
        logger.warning(f"Startup migrations failed: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for FastAPI app lifecycle.
    Starts the scheduler on startup and shuts it down on shutdown.
    Also handles database connection initialization if needed.
    """
    logger.info("Initializing FastAPI application...")

    _run_startup_migrations()

    # Schedule macro research pipeline daily at 06:00 UTC
    from ix.common.task import run_macro_research
    scheduler.add_job(
        run_macro_research,
        "cron", hour=6, minute=0,
        id="macro_research",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Send data reports daily at 07:00 KST (22:00 UTC)
    from ix.common.task import send_data_reports
    scheduler.add_job(
        send_data_reports,
        "cron", hour=22, minute=0,
        id="send_data_reports",
        replace_existing=True,
        misfire_grace_time=3600,
    )

    # Compute VOMO screener daily at 23:00 UTC
    from ix.api.routers.analytics.screener import compute_screener
    scheduler.add_job(
        compute_screener,
        "cron", hour=23, minute=0,
        id="vomo_screener",
        replace_existing=True,
        misfire_grace_time=3600,
    )


    scheduler.start()
    logger.info(f"Scheduler started with {len(scheduler.get_jobs())} job(s)")

    logger.info("FastAPI application started")
    yield

    logger.info("Shutting down scheduler...")
    if scheduler.running:
        scheduler.shutdown()


# Create FastAPI app
app = FastAPI(
    title="Investment-X API",
    description="API for Investment-X dashboard and data management",
    version="1.0.0",
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
)

logger.info("FastAPI app created successfully")

# Rate limiter — single shared instance used by all routers
from ix.api.rate_limit import limiter

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"detail": str(exc.detail), "code": "RATE_LIMITED"},
    )


# Standardized error response for AppError hierarchy
from ix.api.exceptions import AppError  # noqa: E402


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
    )


# Domain exception → HTTP status mapping
from ix.core.exceptions import (  # noqa: E402
    IxError,
    NotFoundError,
    ValidationError,
    DataError,
    UploadError,
)

_IX_STATUS_MAP = {
    NotFoundError: 404,
    ValidationError: 400,
    UploadError: 400,
    DataError: 422,
}


@app.exception_handler(IxError)
async def ix_error_handler(request: Request, exc: IxError):
    status = _IX_STATUS_MAP.get(type(exc), 500)
    return JSONResponse(
        status_code=status,
        content={"detail": str(exc), "code": type(exc).__name__},
    )


# GZip compress responses >= 1KB (Plotly JSON typically 50-500KB)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Configure CORS
_cors_origins = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "Accept"],
)


@app.middleware("http")
async def normalize_path_middleware(request: Request, call_next):
    """Collapse double slashes in URL path (e.g. //api/... → /api/...).
    Cloudflare tunnel can introduce these depending on service URL config."""
    import re
    raw = request.scope.get("path", "")
    if "//" in raw:
        request.scope["path"] = re.sub(r"/{2,}", "/", raw)
    return await call_next(request)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    if not request.url.path.startswith("/api/research/library/view/"):
        response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log method, path, status code, and duration for each request."""
    start = time.time()
    response = None
    try:
        response = await call_next(request)
        return response
    except RuntimeError as e:
        if str(e) == "No response returned.":
            response = Response(status_code=499)
            return response
        raise
    finally:
        duration_ms = (time.time() - start) * 1000
        status = response.status_code if response else 500
        path = request.url.path
        method = request.method
        # Skip noisy health check logs
        if path != "/api/health":
            logger.info(
                f"{method} {path} {status} {duration_ms:.0f}ms"
            )


@app.middleware("http")
async def db_session_middleware(request, call_next):
    """Ensure scoped session is removed after each request."""
    try:
        response = await call_next(request)
        return response
    except RuntimeError as e:
        if str(e) == "No response returned.":
            # Client disconnected mid-request, causing Starlette's BaseHTTPMiddleware to crash.
            # We return a dummy 499 Client Closed Request to gracefully exit the middleware chain.
            return Response(status_code=499)
        raise
    finally:
        if conn.Session:
            conn.Session.remove()


# Root endpoint removed as Dash handles "/"

# Auth dependency — imported here to avoid circular imports at module top-level
from ix.api.dependencies import get_current_admin_user as _get_admin_user  # noqa: E402


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Investment-X API",
        "scheduler_running": scheduler.running,
    }


_DEBUG_MODE = os.environ.get("DEBUG_MODE", "false").lower() in ("true", "1", "yes")

if _DEBUG_MODE:

    @app.get("/api/test-error")
    async def test_error(_=Depends(_get_admin_user)):
        """Endpoint to test error handling — admin only."""
        raise Exception("Critical test failure")


@app.get("/api/jobs")
async def get_jobs(_=Depends(_get_admin_user)):
    """List currently scheduled jobs — admin only."""
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
        content={
            "error": "Internal server error",
            "detail": "An unexpected error occurred.",
        },
    )


# Include routers with error handling
try:
    from ix.api.routers.auth import auth_router, admin_router, user_router
    from ix.api.routers.data import (
        timeseries_router,
        series_router,
        evaluation_router,
        collectors_router,
        credit_watchlist_router,
    )
    from ix.api.routers.charts import (
        chart_packs_router,
        whiteboard_router,
    )
    from ix.api.routers.analytics import (
        quant_router,
        technical_router,
        technicals_router,
        macro_router,
        wartime_router,
        screener_router,
        strategies_router,
        regimes_router,
    )
    from ix.api.routers.research import (
        news_router,
        scorecards_router,
        tts_router,
        library_router,
    )
    from ix.api.routers.risk import risk_router

    logger.info("Importing routers...")

    # Auth & User
    app.include_router(auth_router, prefix="/api", tags=["Authentication"])
    app.include_router(admin_router, prefix="/api", tags=["Admin"])
    app.include_router(user_router, prefix="/api", tags=["User"])

    # Data Management
    app.include_router(timeseries_router, prefix="/api", tags=["Timeseries"])
    app.include_router(series_router, prefix="/api", tags=["Series"])
    app.include_router(evaluation_router, prefix="/api", tags=["Evaluation"])
    app.include_router(collectors_router, prefix="/api", tags=["Collectors"])
    app.include_router(credit_watchlist_router, prefix="/api", tags=["Credit Watchlist"])

    # Charts & Visualization
    app.include_router(chart_packs_router, prefix="/api", tags=["Chart Packs"])
    app.include_router(whiteboard_router, prefix="/api", tags=["Whiteboard"])

    # Analytics & Quantitative
    app.include_router(quant_router, prefix="/api", tags=["Quant"])
    app.include_router(technical_router, prefix="/api", tags=["Technical"])
    app.include_router(technicals_router, prefix="/api", tags=["Technicals"])
    app.include_router(macro_router, prefix="/api", tags=["Macro"])
    app.include_router(wartime_router, prefix="/api", tags=["Wartime"])
    app.include_router(screener_router, prefix="/api", tags=["Screener"])
    app.include_router(strategies_router, prefix="/api", tags=["Strategies"])
    app.include_router(regimes_router, prefix="/api", tags=["Regimes"])

    # Research & News
    app.include_router(news_router, prefix="/api", tags=["Briefings"])
    app.include_router(scorecards_router, prefix="/api/v1", tags=["Scorecards"])
    app.include_router(tts_router, prefix="/api", tags=["TTS"])
    app.include_router(library_router, prefix="/api", tags=["Research Library"])

    app.include_router(risk_router, prefix="/api", tags=["Risk"])

    logger.info("Routers registered successfully")

except Exception as e:
    import traceback

    traceback.print_exc()
    logger.error(f"Failed to import or register routers: {e}", exc_info=True)
    # Re-raise so the app fails to start if routers are broken
    raise e


# Serve SPA - Static Files
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

    if _DEBUG_MODE:

        @app.get("/api/debug-fs")
        async def debug_fs(_=Depends(_get_admin_user)):
            try:
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
        static_root = Path(static_dir).resolve()

        # Prevent path traversal
        resolved = (static_root / full_path).resolve()
        if not str(resolved).startswith(str(static_root)):
            raise HTTPException(status_code=404)

        # 1. Check if the file exists as is
        if resolved.is_file():
            return FileResponse(str(resolved))

        # 2. Check if appending .html works (for Next.js static export)
        html_path = resolved.with_suffix(".html")
        if html_path.is_file() and str(html_path).startswith(str(static_root)):
            return FileResponse(str(html_path))

        # 3. Check if it's a directory with index.html (trailingSlash: true)
        dir_index_path = resolved / "index.html"
        if dir_index_path.is_file() and str(dir_index_path.resolve()).startswith(str(static_root)):
            return FileResponse(str(dir_index_path))

        # Fallback to root index.html
        return FileResponse(str(static_root / "index.html"))

else:
    logger.info("Static directory not found, running API only mode")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
