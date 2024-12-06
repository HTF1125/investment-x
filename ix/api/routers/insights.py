from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Body, status
from ix import db
from fastapi.responses import StreamingResponse
import io
from bson import ObjectId
from pydantic import BaseModel

router = APIRouter(prefix="/data/insights", tags=["data"])


@router.get(
    "/",
    response_model=List[db.Insight],
    status_code=status.HTTP_200_OK,
)
def get_research_file_codes(
    skip: Optional[int] = Query(0, ge=0, description="Number of records to skip"),
    limit: Optional[int] = Query(
        10, gt=0, description="Maximum number of records to return"
    ),
):
    """
    Retrieves insights sorted by date in descending order, with support for pagination.
    """
    try:
        # Query the database with sorting, skipping, and limiting
        insights = db.Insight.find().sort("-date").skip(skip).limit(limit)
        return list(insights)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching insights: {str(e)}",
        )


@router.get(
    "/{id}",
    response_model=str,
    status_code=status.HTTP_200_OK,
)
def get_insight_content(id: str):
    """
    Retrieves a research file by its code and streams it as a response.
    """
    try:
        insight = db.Insight.find_one(db.Insight.id == ObjectId(id)).run()
        if not insight:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )
        content = insight.get_content()
        # Serve the content as a streaming response
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/pdf",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )






class InsightUpdateRequest(BaseModel):
    issuer: Optional[str] = None
    name: Optional[str] = None
    summary: Optional[str] = None
    date: Optional[str] = None  # ISO format (YYYY-MM-DD)


@router.put(
    "/{id}",
    response_model=db.Insight,
    status_code=status.HTTP_200_OK,
)
def update_insight(id: str, update_request: InsightUpdateRequest = Body(...)):
    """
    Updates an Insight by its ID with the provided data.
    """
    try:
        # Validate the ID
        if not ObjectId.is_valid(id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format"
            )

        # Update the fields if provided
        updated_fields = {}
        if update_request.name is not None:
            updated_fields["name"] = update_request.name
        if update_request.summary is not None:
            updated_fields["summary"] = update_request.summary
        if update_request.date is not None:
            updated_fields["date"] = update_request.date
        if update_request.issuer is not None:
            updated_fields["issuer"] = update_request.issuer
        if not updated_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update",
            )

        insight = db.Insight.find_one(db.Insight.id == ObjectId(id)).run()
        updated = insight.set(updated_fields)

        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found"
            )

        return updated

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )
