from fastapi import APIRouter, HTTPException, status, Path
from ix import db
from datetime import date
import pandas as pd
from typing import Dict

router = APIRouter(prefix="/data/tickers", tags=["data"])


@router.get(
    "/all",
    response_model=list[db.TickerInfo],
    status_code=status.HTTP_200_OK,
)
def get_tickers():
    """
    Fetch all tickers from the database.
    """
    try:
        tickers = db.Ticker.find_all(
            projection_model=db.TickerInfo,
        ).run()
        if not tickers:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No tickers found.",
            )
        return tickers
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching tickers: {str(e)}",
        )


@router.put(
    "/{code}",
    response_model=db.Ticker,
    status_code=status.HTTP_200_OK,
)
def update_ticker(
    code: str = Path(..., description="Ticker code to be updated"),
    ticker_update: db.TickerInfo | None = None,
):
    """
    Update a ticker with the specified code. Partial updates are supported.
    """

    if not ticker_update:
        raise

    try:
        # Retrieve the ticker by code
        ticker = db.Ticker.find_one({"code": code}).run()
        if not ticker:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticker with code '{code}' not found.",
            )

        # Prepare the update data
        update_data = ticker_update.model_dump()
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update.",
            )

        # Perform the update
        updated_ticker = (
            db.Ticker.find_one(db.Ticker.code == code)
            .update(
                {"$set": update_data},
                projection_model=db.TickerInfo,
            )
            .run()
        )

        if not updated_ticker:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update ticker with code '{code}'.",
            )
        return updated_ticker
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating ticker: {str(e)}",
        )


from pydantic import BaseModel, Field, ValidationError
from fastapi import Body
from typing import Dict
from datetime import date

class UpdatePxLastRequest(BaseModel):
    update_pxlast: Dict[str, float] = Field(..., description="PxLast data with date keys")

    # Validator to convert keys to `date`
    @classmethod
    def validate_update_pxlast(cls, value):
        try:
            return {date.fromisoformat(k): v for k, v in value.items()}
        except ValueError as e:
            raise ValidationError(f"Invalid date format in keys: {str(e)}")

@router.put(path="/update_pxlast/{code}", status_code=status.HTTP_200_OK)
def update_pxlast(
    code: str = Path(..., description="Ticker code to be updated"),
    request: UpdatePxLastRequest = Body(...),
):
    """
    Update the PxLast data for a specified ticker code. Partial updates are supported.
    """
    if not request.update_pxlast:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No update data provided.",
        )

    try:
        # Retrieve the ticker by code
        pxlast = db.PxLast.find_one({"code": code}).run()
        if not pxlast:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Ticker with code '{code}' not found.",
            )

        # Combine existing and new data
        existing_series = pd.Series(pxlast.data)
        new_series = pd.Series(request.update_pxlast)
        updated_series = new_series.combine_first(existing_series)

        # Update the database
        pxlast.set({"data": updated_series.to_dict()})

        return {"message": "PxLast data updated successfully.", "code": code}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating PxLast data: {str(e)}",
        )
