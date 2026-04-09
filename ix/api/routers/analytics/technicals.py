"""Technicals API — VAMS regimes, VOMO scores, CACRI.

Serves dashboard technical data computed by ix.core.technical.vams_technicals.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as SessionType

from ix.api.dependencies import get_current_admin_user, get_db, get_optional_user
from ix.api.rate_limit import limiter as _limiter
from ix.common import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/technicals")
@_limiter.limit("30/minute")
def get_technicals(request: Request, index: str | None = None, _user=Depends(get_optional_user)):
    """VAMS momentum regime data.

    When `index` is provided, returns full data for that single index.
    Otherwise returns lightweight summary for all indices.
    """
    if index:
        from ix.core.technical.vams_technicals import get_or_compute_index

        result = get_or_compute_index(index)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Index '{index}' not found")
        return result

    from ix.core.technical.vams_technicals import get_summary

    return get_summary()


@router.get("/technicals/summary")
@_limiter.limit("30/minute")
def get_technicals_summary(request: Request, _user=Depends(get_optional_user)):
    """Lightweight summary of all indices — no chart data."""
    from ix.core.technical.vams_technicals import get_summary

    return get_summary()


@router.get("/technicals/detail")
@_limiter.limit("30/minute")
def get_technicals_detail(request: Request, index: str, _user=Depends(get_optional_user)):
    """Chart data (daily_prices, weekly_vams, vomo history) for a single index."""
    from ix.core.technical.vams_technicals import get_detail

    result = get_detail(index)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Index '{index}' not found")
    return result


@router.post("/technicals/refresh")
@_limiter.limit("5/minute")
def refresh_technicals(request: Request, index: str, _user=Depends(get_current_admin_user)):
    """Refresh a single index's technical data.

    Admin-only. Downloads fresh data for the specified index only
    and patches it into the existing cache.
    """
    from ix.core.technical.vams_technicals import refresh_single

    return refresh_single(index)


@router.get("/cacri-history")
@_limiter.limit("30/minute")
def get_cacri_history(request: Request, _user=Depends(get_optional_user), db: SessionType = Depends(get_db)):
    """Historical CACRI timeseries: weekly fraction of cross-asset proxies with bearish VAMS.

    Serves from DB cache; falls back to live compute on cache miss.
    """
    from ix.db.models.api_cache import ApiCache

    entry = db.query(ApiCache).get("cacri-history")
    if entry and entry.value:
        return entry.value

    from ix.core.technical.vams_technicals import compute_cacri_history

    return compute_cacri_history()
