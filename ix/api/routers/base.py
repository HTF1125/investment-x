from typing import List
from typing import Type
from typing import Optional
from bunnet import Document
from ix.db.conn import Code
from bson import ObjectId
from pydantic import BaseModel
from typing import Dict
from datetime import date
from fastapi import Query
from fastapi import APIRouter, BackgroundTasks, status
from fastapi import HTTPException, Body
from ix.db import MetaData, InsightSource, MetaDataBase, InsightSourceBase
from ix import task


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


router = APIRouter(prefix="", tags=["metadata"])


@router.get(
    "/metadatas",
    response_model=List[MetaData],
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


@router.get(
    "/metadata",
    status_code=status.HTTP_201_CREATED,
    description="Get ticker code",
)
def get_metadata(
    id: Optional[str] = Query(None, description="MetaData id (optional)"),
    code: Optional[str] = Query(None, description="MetaData code (optional)"),
):
    if code:
        metadata = MetaData.find_one(MetaData.code == code).run()
    elif id:
        metadata = MetaData.find_one(MetaData.id == id).run()
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No metadatas found.",
        )
    return metadata


@router.delete(
    "/metadata",
    status_code=status.HTTP_200_OK,
    description="Add a new ticker code to the database.",
)
def delete_metata(metadata: MetaData):
    """
    Endpoint to create a new insight source.

    Parameters:
    - url: URL data provided in the request body.

    Returns:
    - The created InsightSource document.
    """
    if not ObjectId.is_valid(metadata.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format",
        )
    InsightSource.find_one(MetaData.id == metadata.id).delete().run()
    return {"message": "InsightSource deleted successfully"}


@router.put(
    "/metadata",
    status_code=status.HTTP_200_OK,
    response_model=MetaData,
    description="Add a new ticker code to the database.",
)
def update_metadata(metadata: MetaData):

    if not ObjectId.is_valid(metadata.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format",
        )

    try:
        _metadata = MetaData.find_one(MetaData.id == metadata.id).run()
        if not _metadata:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found"
            )
        return _metadata.set(metadata.model_dump())
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the insight source: {str(e)}",
        )


@router.post(
    "/metadata",
    status_code=status.HTTP_200_OK,
    response_model=MetaData,
    description="Add a new ticker code to the database.",
)
def create_metadata(metadata: MetaDataBase):

    try:
        return MetaData(**metadata.model_dump()).create()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the insight source: {str(e)}",
        )


# Define the request model for the data
class TimeSeriesData(BaseModel):
    data: Dict[date, float]  # Dictionary with date as key and float as value


# Add the route to the router
@router.get("/timeseries")
async def get_timeseries(
    code: str = Query(..., description="MetaData code"),
    field: str = Query("PX_LAST", description="Field code"),
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


@router.put(
    path="/timeseries",
    status_code=status.HTTP_200_OK,
    response_model=dict,
)
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
    metadata = MetaData.find_one(MetaData.code == code).run()
    if metadata is None:
        raise HTTPException(status_code=404, detail=f"MetaData<{code}> not found.")
    try:
        metadata.ts(field=field).data = body.data
        return {"message": "Time series updated successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    path="/signals",
    response_model=List[MetaData],
    status_code=status.HTTP_200_OK,
)
async def get_signals():
    try:
        metadatas = MetaData.find_many(MetaData.market == "Signal").run()
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


@router.get(
    path="/insightsources",
    response_model=List[InsightSource],
    status_code=status.HTTP_200_OK,
)
async def get_insight_sources():
    try:
        insight_souces = InsightSource.find_all().run()
        if not insight_souces:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No metadatas found.",
            )
        return insight_souces
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching tickers: {str(e)}",
        )


@router.post(
    path="/insightsources",
    response_model=InsightSource,
    status_code=status.HTTP_201_CREATED,
)
async def create_insight_source(insight_source: InsightSourceBase = Body(...)):
    """
    Endpoint to create a new insight source.

    Parameters:
    - url: URL data provided in the request body.

    Returns:
    - The created InsightSource document.
    """
    try:
        model = {}
        for k, v in insight_source.model_dump().items():
            if v is not None:
                model[k] = v
        return InsightSource(**model).create()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the insight source: {str(e)}",
        )


@router.put(
    path="/insightsources",
    response_model=InsightSource,
    status_code=status.HTTP_200_OK,
)
async def update_insight_source(
    update_insight_source: InsightSource = Body(...),
):
    """
    Endpoint to create a new insight source.

    Parameters:
    - url: URL data provided in the request body.

    Returns:
    - The created InsightSource document.
    """
    if not ObjectId.is_valid(update_insight_source.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format",
        )
    update = {key: value for key, value in update_insight_source.model_dump().items()}
    if not update:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )
    try:
        insight_source = InsightSource.find_one(
            InsightSource.id == update_insight_source.id
        ).run()
        if not insight_source:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found"
            )
        return insight_source.set(update)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while creating the insight source: {str(e)}",
        )


@router.delete(
    path="/insightsources/{id}",
    status_code=status.HTTP_200_OK,
)
async def delete_insight_source(id: str):
    """
    Endpoint to create a new insight source.

    Parameters:
    - url: URL data provided in the request body.

    Returns:
    - The created InsightSource document.
    """
    if not ObjectId.is_valid(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format",
        )
    InsightSource.find_one(InsightSource.id == ObjectId(id)).delete().run()
    return {"message": "InsightSource deleted successfully"}


# Your task handler that will run in the background
async def run_daily_task():
    task.run()


# The route that will trigger the background task
@router.get(path="/tasks/daily", status_code=status.HTTP_200_OK)
async def ping_task_daily(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_daily_task)
    return {"message": "Task is running in the background"}
