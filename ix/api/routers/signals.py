from typing import List
from fastapi import APIRouter
from fastapi import HTTPException
from fastapi import status
from bson.errors import InvalidId
from ix import db
from .base import get_model_codes


router = APIRouter(prefix="/data/signals", tags=["data"])


@router.get(
    "/codes",
    response_model=List[str],
    status_code=status.HTTP_200_OK,
)
def get_signal_codes():
    """
    Retrieves all signal codes.
    """
    try:
        return get_model_codes(model=db.Signal)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching signal codes: {str(e)}",
        )


@router.get(
    "/{code}",
    response_model=db.Signal,
    status_code=status.HTTP_200_OK,
)
def get_signal_by_id(code: str):
    """
    Retrieves a signal by its ID.
    """
    try:
        # Attempt to retrieve the signal
        signal = db.Signal.find_one(db.Signal.code == code).run()

        if signal is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Signal not found"
            )

        return signal

    except InvalidId:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signal ID format"
        )
    except Exception as e:
        # Log the exception here
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while processing the request: {str(e)}",
        )
