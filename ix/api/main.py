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
from fastapi.responses import JSONResponse, FileResponse, Response
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import text
from slowapi.errors import RateLimitExceeded

from ix.db.conn import ensure_connection, conn
from ix.utils.logger import setup_logging

logger = setup_logging(service_name="backend")

scheduler = AsyncIOScheduler()


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

            # Research report: slide_deck column
            db.execute(text(
                "ALTER TABLE research_report ADD COLUMN IF NOT EXISTS slide_deck BYTEA"
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
)

logger.info("FastAPI app created successfully")

# Rate limiter — single shared instance used by all routers
from ix.api.rate_limit import limiter

app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": "Rate limit exceeded", "detail": str(exc.detail)},
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
async def security_headers_middleware(request: Request, call_next):
    """Add security headers to all responses."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
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
    from ix.api.routers import (
        auth,
        admin,
        timeseries,
        series,
        evaluation,
        task,
        risk,
        news,
        custom,
        insights,
        user,
    )

    logger.info("Importing routers...")
    app.include_router(auth.router, prefix="/api", tags=["Authentication"])
    app.include_router(admin.router, prefix="/api", tags=["Admin"])
    app.include_router(user.router, prefix="/api", tags=["User"])
    app.include_router(timeseries.router, prefix="/api", tags=["Timeseries"])
    app.include_router(series.router, prefix="/api", tags=["Series"])
    app.include_router(evaluation.router, prefix="/api", tags=["Evaluation"])
    app.include_router(task.router, prefix="/api", tags=["Tasks"])
    app.include_router(risk.router, prefix="/api", tags=["Risk"])
    app.include_router(news.router, prefix="/api", tags=["News"])
    app.include_router(custom.router, prefix="/api", tags=["Custom"])
    app.include_router(insights.router, prefix="/api", tags=["Insights"])
    from ix.api.routers import quant
    app.include_router(quant.router, prefix="/api", tags=["Quant"])
    from ix.api.routers import wartime
    app.include_router(wartime.router, prefix="/api", tags=["Wartime"])
    from ix.api.routers import macro
    app.include_router(macro.router, prefix="/api", tags=["Macro"])
    from ix.api.routers import dashboard

    app.include_router(dashboard.router, prefix="/api/v1", tags=["Dashboard"])
    from ix.api.routers import whiteboard
    app.include_router(whiteboard.router, prefix="/api", tags=["Whiteboard"])
    from ix.api.routers import collectors
    app.include_router(collectors.router, prefix="/api", tags=["Collectors"])
    logger.info("Routers registered successfully")

    # Legacy Dash chartbook mount removed with charts table decommission.

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
