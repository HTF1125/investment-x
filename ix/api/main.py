from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from ix.api import routers
from ix.misc import get_logger


logger = get_logger(__name__)


app = FastAPI()


# Include API routers
app.include_router(routers.data.router, prefix="/api")
app.include_router(routers.strategies.router, prefix="/api")
app.include_router(routers.signals.router, prefix="/api")
app.include_router(routers.insights.router, prefix="/api")
app.include_router(routers.login.router, prefix="/api")
app.include_router(routers.base.router, prefix="/api")
app.include_router(routers.auth.router, prefix="/api")
app.include_router(routers.metadata.router, prefix="/api")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.get("/api/health")
async def health_check():
    logger.info("Health check requested")
    try:
        return JSONResponse(content={"status": "healthy"}, status_code=200)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    logger.error(f"HTTPException: {exc.detail}")
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"error": "Validation error", "details": exc.errors()},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
