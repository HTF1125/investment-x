from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Body, status
from ix import db
from fastapi.responses import StreamingResponse
import io, base64
from bson import ObjectId
from pydantic import BaseModel
from datetime import datetime, date
import re

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
def get_insights(
    skip: Optional[int] = Query(0, ge=0, description="Number of records to skip"),
    limit: Optional[int] = Query(
        1000, gt=0, description="Maximum number of records to return"
    ),
    search: Optional[str] = Query(
        None, description="Search term to filter insights by issuer, name, or date"
    ),
):
    """
    Retrieves insights sorted by date in descending order, with support for pagination and search.
    """
    try:
        # Base query
        query = {}

        if search:
            # Step 1: Try to extract a date from the search term using regex
            date_pattern = r"\d{4}-\d{2}-\d{2}"  # Match date in YYYY-MM-DD format
            date_match = re.search(date_pattern, search)

            # If a date is found, separate the date and text parts
            if date_match:
                search_date_str = date_match.group(0)
                try:
                    search_date = datetime.strptime(
                        search_date_str, "%Y-%m-%d"
                    )  # Convert to date object
                    query["published_date"] = {
                        "$eq": search_date
                    }  # Filter by exact date
                except ValueError:
                    pass  # If date format is incorrect, we ignore it

                # Remove the date part from the search term for text-based search
                search_text = search.replace(search_date_str, "").strip()
            else:
                # No date found, use the entire search term as text-based search
                search_text = search

            # Step 2: Handle the text-based search for issuer, name, and published_date
            if search_text:
                search_keywords = search_text.lower().split()

                conditions = []
                for keyword in search_keywords:
                    conditions.append(
                        {
                            "$or": [
                                {"issuer": {"$regex": keyword, "$options": "i"}},
                                {"name": {"$regex": keyword, "$options": "i"}},
                                {
                                    "published_date": {
                                        "$regex": keyword,
                                        "$options": "i",
                                    }
                                },
                            ]
                        }
                    )

                query["$and"] = conditions

        # Fetch insights with the query
        insights = (
            db.Insight.find(query).sort("-published_date").skip(skip).limit(limit)
        )

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
