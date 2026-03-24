from fastapi import APIRouter, Depends, Request, Response
from ix.api.dependencies import get_current_user, get_optional_user
from ix.api.rate_limit import limiter as _limiter

router = APIRouter()


def _apply_private_cache_headers(response: Response, max_age: int = 300) -> None:
    response.headers["Cache-Control"] = (
        f"private, max-age={max_age}, stale-while-revalidate={max_age * 2}"
    )
    response.headers["Vary"] = "Cookie, Authorization"


@router.get("/scorecards")
@_limiter.limit("10/minute")
def get_scorecards(
    request: Request,
    response: Response,
    current_user=Depends(get_optional_user),
):
    """Pre-computed scorecard tables: performance returns + RRG metrics."""
    _apply_private_cache_headers(response)
    from ix.core.indicators.scorecards import compute_all_scorecards

    return {"categories": compute_all_scorecards()}


@router.post("/scorecards/refresh")
@_limiter.limit("3/minute")
def refresh_scorecards(
    request: Request,
    response: Response,
    current_user=Depends(get_current_user),
):
    """Clear all caches and recompute with live data from Yahoo/Fred/Naver."""
    from ix.core.indicators.scorecards import clear_scorecard_cache, compute_all_scorecards

    clear_scorecard_cache()
    response.headers["Cache-Control"] = "no-cache"
    return {"categories": compute_all_scorecards(force_live=True)}
