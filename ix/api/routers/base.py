from typing import List
from typing import Type
from bunnet import Document
from ix.db.conn import Code


def get_model_codes(model: Type[Document]) -> List[str]:

    if getattr(model, "code") is None:
        raise Exception(f"Document {model.__name__} does not have code attribute.")

    codes = [
        str(doc.code)
        for doc in model.find_all(
            projection_model=Code,
        ).run()
    ]
    return codes


from fastapi import APIRouter, HTTPException, status, Path, Body
from ix.db import MetaData


router = APIRouter(prefix="", tags=["metadata"])


@router.get(
    "/metadatas",
    response_model=list[MetaData],
    status_code=status.HTTP_200_OK,
)
def get_metadatas():
    try:
        metadatas = MetaData.find_all().run()
        if not metadatas:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No metadatas found.",
            )
        return metadatas
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching tickers: {str(e)}",
        )


@router.post(
    "/metadata",
    status_code=status.HTTP_201_CREATED,
    description="Add a new ticker code to the database.",
)
def create_metadata():
    try:
        metadatas = MetaData.find_all().run()
        if not metadatas:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No metadatas found.",
            )
        return metadatas
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching tickers: {str(e)}",
        )


from pydantic import BaseModel
from typing import Dict
from datetime import date
from fastapi import Query, Body
import pandas as pd


# Define the request model for the data
class TimeSeriesData(BaseModel):
    data: Dict[date, float]  # Dictionary with date as key and float as value


# Add the route to the router
@router.get("/timeseries")
async def get_timeseries(
    code: str = Query(..., description="Code of the time series"),
    field: str = Query(..., description="Field to update"),
):
    """
    Endpoint to update time series data.

    Parameters:
        - code (str): Code of the time series (query parameter).
        - field (str): Field to update (query parameter).
        - body (TimeSeriesData): Time series data in the request body.
    """
    try:
        metadata = MetaData.find_one(MetaData.code == code).run()
        if metadata is None:
            raise
        return metadata.ts(field=field).data.to_dict()
    except Exception as e:
        # Handle any unexpected errors
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/timeseries")
async def update_timeseries(
    code: str = Query(..., description="Code of the time series"),
    field: str = Query(..., description="Field to update"),
    body: TimeSeriesData = Body(..., description="Time series data"),
):
    """
    Endpoint to update time series data.

    Parameters:
        - code (str): Code of the time series (query parameter).
        - field (str): Field to update (query parameter).
        - body (TimeSeriesData): Time series data in the request body.
    """
    try:

        metadata = MetaData.find_one(MetaData.code == code).run()
        if metadata is None:
            raise
        ts = metadata.ts(field=field)
        data = pd.Series(data=body.data)
        data.index = pd.to_datetime(data.index)
        ts.data = data

    except Exception as e:
        # Handle any unexpected errors
        raise HTTPException(status_code=500, detail=str(e))
