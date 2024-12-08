from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Body, status
from ix import db
from fastapi.responses import StreamingResponse
import io, base64
from bson import ObjectId
from pydantic import BaseModel
from datetime import date

router = APIRouter(prefix="/data/insights", tags=["data"])


class InsightRequest(BaseModel):
    issuer: str
    name: str
    published_date: date
    summary: Optional[str] = None
    content: Optional[str] = None


@router.get(
    "/",
    response_model=List[db.Insight],
    status_code=status.HTTP_200_OK,
)
def get_research_file_codes(
    skip: Optional[int] = Query(0, ge=0, description="Number of records to skip"),
    limit: Optional[int] = Query(
        1000, gt=0, description="Maximum number of records to return"
    ),
):
    """
    Retrieves insights sorted by date in descending order, with support for pagination.
    """
    try:
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
    Retrieves the content of a research file by its ID and streams it as a response.
    """
    try:
        if not ObjectId.is_valid(id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format"
            )

        insight = db.Insight.find_one(db.Insight.id == ObjectId(id)).run()
        if not insight:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        content = insight.get_content()
        return StreamingResponse(
            io.BytesIO(content),
            media_type="application/pdf",
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred: {str(e)}",
        )


@router.post(
    "/new",
    response_model=db.Insight,
    status_code=status.HTTP_200_OK,
)
def add_insight(add_request: InsightRequest = Body(...)):
    """
    Adds a new Insight with the provided data.
    """
    try:
        # Decode Base64 content to bytes
        content_bytes = None
        if add_request.content:
            try:
                content_bytes = base64.b64decode(add_request.content)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid Base64 content",
                )

        # Create and save the insight
        new_insight = db.Insight(
            issuer=add_request.issuer,
            name=add_request.name,
            published_date=add_request.published_date,
            summary=add_request.summary,
        ).create()

        if content_bytes:
            new_insight.save_content(content=content_bytes)

        return new_insight
    except Exception as e:
        print("Failed to add insight:", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add insight",
        )


@router.put(
    "/update/{id}",
    response_model=db.Insight,
    status_code=status.HTTP_200_OK,
)
def update_insight(id: str, update_request: InsightRequest = Body(...)):
    """
    Updates an Insight by its ID with the provided data.
    """
    if not ObjectId.is_valid(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ID format",
        )

    updated_fields = {
        key: value
        for key, value in update_request.model_dump().items()
        if value is not None and key != "content"
    }

    if not updated_fields and not update_request.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update",
        )

    insight = db.Insight.find_one(db.Insight.id == ObjectId(id)).run()
    if not insight:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Insight not found"
        )

    # Update the fields
    insight.set(updated_fields)

    # Handle content update
    if update_request.content:
        try:
            # Decode Base64 content to bytes
            content_bytes = base64.b64decode(update_request.content)

            # Remove old content and save new content
            db.InsightContent.find_many(
                db.InsightContent.insight_id == str(insight.id)
            ).delete().run()
            insight.save_content(content_bytes)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Base64 content",
            )

    return insight

@router.delete(
    "/delete/{id}",
    status_code=status.HTTP_200_OK,
)
def delete_insight(id: str):
    """
    Deletes an Insight by its ID.
    """
    try:
        if not ObjectId.is_valid(id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format"
            )

        insight = db.Insight.find_one(db.Insight.id == ObjectId(id)).run()
        if insight:
            db.InsightContent.find_many(
                db.InsightContent.insight_id == str(insight.id)
            ).delete().run()
            db.Insight.find_one(db.Insight.id == ObjectId(id)).delete().run()

        return {"message": "Insight successfully deleted."}

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting the insight: {str(e)}",
        )
