"""Macro analytics router — target list, stress test, VAMS technicals, CACRI.

Slim successor to the legacy macro outlook router. Only endpoints actually
consumed by the frontend are kept; legacy outlook/regime-strategy endpoints
were removed along with ``ix/core/macro/``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as SessionType

from ix.api.dependencies import get_current_admin_user, get_db, get_optional_user
from ix.api.rate_limit import limiter as _limiter
from ix.common import get_logger
from ix.core.stress_test import TARGET_INDICES

router = APIRouter()
logger = get_logger(__name__)


@router.get("/macro/targets")
@_limiter.limit("60/minute")
def list_targets(request: Request, _user=Depends(get_optional_user)):
    """List all available target indices."""
    return {
        "targets": [
            {
                "name": name,
                "ticker": idx.ticker,
                "region": idx.region,
                "currency": idx.currency,
                "has_sectors": idx.has_sectors,
            }
            for name, idx in TARGET_INDICES.items()
        ]
    }


@router.get("/macro/stress-test")
@_limiter.limit("10/minute")
def get_stress_test(request: Request, target: str = "KOSPI", _user=Depends(get_optional_user)):
    """Compute stress test analysis for a target index.

    Auto-detects historical crash events, computes forward returns at
    standard horizons, and builds recovery curves.
    """
    if target not in TARGET_INDICES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown target '{target}'. Available: {list(TARGET_INDICES.keys())}",
        )
    try:
        from ix.core.stress_test import compute_stress_test

        return compute_stress_test(target)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logger.exception(f"Stress test failed for {target}")
        raise HTTPException(status_code=500, detail="Stress test computation failed")


# ===========================================================================
# TECHNICALS (delegates to ix.core.technical.vams_technicals)
# ===========================================================================


@router.get("/macro/technicals")
@_limiter.limit("30/minute")
def get_technicals(request: Request, index: str | None = None, _user=Depends(get_optional_user)):
    """VAMS momentum regime data."""
    if index:
        from ix.core.technical.vams_technicals import get_or_compute_index

        result = get_or_compute_index(index)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Index '{index}' not found")
        return result

    from ix.core.technical.vams_technicals import get_summary

    return get_summary()


@router.get("/macro/technicals/summary")
@_limiter.limit("30/minute")
def macro_technicals_summary(request: Request, _user=Depends(get_optional_user)):
    """Lightweight summary of all indices — no chart data."""
    from ix.core.technical.vams_technicals import get_summary

    return get_summary()


@router.get("/macro/technicals/detail")
@_limiter.limit("30/minute")
def macro_technicals_detail(request: Request, index: str, _user=Depends(get_optional_user)):
    """Chart data (daily_prices, weekly_vams, vomo history) for a single index."""
    from ix.core.technical.vams_technicals import get_detail

    result = get_detail(index)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Index '{index}' not found")
    return result


@router.post("/macro/technicals/refresh")
@_limiter.limit("5/minute")
def refresh_technicals(request: Request, index: str, _user=Depends(get_current_admin_user)):
    """Refresh a single index's technical data."""
    from ix.core.technical.vams_technicals import refresh_single

    return refresh_single(index)


@router.get("/macro/cacri-history")
@_limiter.limit("30/minute")
def get_cacri_history(request: Request, _user=Depends(get_optional_user), db: SessionType = Depends(get_db)):
    """Historical CACRI timeseries."""
    from ix.db.models.api_cache import ApiCache

    entry = db.query(ApiCache).get("cacri-history")
    if entry and entry.value:
        return entry.value

    from ix.core.technical.vams_technicals import compute_cacri_history

    return compute_cacri_history()
