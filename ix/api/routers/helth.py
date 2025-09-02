# routers/health.py
"""
Router for health check endpoints.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from fastapi import APIRouter
from pydantic import BaseModel

from ix.db import Timeseries
from ix.misc.terminal import get_logger

router = APIRouter()
logger = get_logger(__name__)


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    database: Optional[str] = None
    timeseries_count: Optional[int] = None
    error: Optional[str] = None


@router.get("/ping", response_model=Dict[str, str])
async def ping():
    """Simple ping endpoint for health checks."""
    return {"message": "pong"}


@router.get("/status", response_model=Dict[str, str])
async def get_status():
    """Get application status."""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


@router.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Comprehensive health check."""
    try:
        # Test database connectivity
        timeseries_count = len(Timeseries.find().run())

        return HealthCheckResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            database="connected",
            timeseries_count=timeseries_count
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=datetime.now().isoformat(),
            error=str(e)
        )
