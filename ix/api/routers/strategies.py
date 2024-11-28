from fastapi import APIRouter, HTTPException, status
from ix import db
from .base import get_model_codes


router = APIRouter(prefix="/data/strategies", tags=["data"])


@router.get(
    "/keyinfo",
    response_model=list[db.StrategyKeyInfo],
    status_code=status.HTTP_200_OK,
)
def get_strategies_keyinfo():
    try:
        return db.Strategy.find_all(
            projection_model=db.StrategyKeyInfo,
        ).run()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching strategy IDs: {str(e)}",
        )


@router.get(
    "/all",
    response_model=list[db.Strategy],
    status_code=status.HTTP_200_OK,
)
def get_strategies():
    """
    Retrieves all strategy IDs.
    """
    try:
        return db.Strategy.find_all(
            projection_model=db.Strategy,
        ).run()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching strategy IDs: {str(e)}",
        )


@router.get(
    "/codes",
    response_model=list[str],
    status_code=status.HTTP_200_OK,
)
def get_strategy_codes():
    """
    Retrieves all strategy IDs.
    """
    try:
        return get_model_codes(model=db.Strategy)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching strategy IDs: {str(e)}",
        )


@router.get(
    "/{code}",
    response_model=db.Strategy,
    status_code=status.HTTP_200_OK,
)
def get_strategy_by_code(code: str):
    """
    Retrieves a strategy by its ID.
    """
    try:
        # Attempt to retrieve the strategy
        strategy = db.Strategy.find_one(db.Strategy.code == code).run()

        if strategy is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy {code} not found",
            )

        return strategy

    except Exception as e:
        # Log the exception here
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching the strategy: {str(e)}",
        )
