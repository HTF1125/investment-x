from fastapi import APIRouter, Depends, Request, Response
from ix.api.dependencies import get_optional_user
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
    from ix.db.custom.scorecards import compute_all_scorecards

    return {"categories": compute_all_scorecards()}
