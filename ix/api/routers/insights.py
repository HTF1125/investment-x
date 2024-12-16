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
    "/tacticalview",
    response_model=db.TacticalView,
    status_code=status.HTTP_200_OK,
)
def get_tacticalview():

    # Find the most recent document by sorting published_date descending
    most_recent = db.TacticalView.find_one(
        {},  # Match all documents
        sort=[("published_date", -1)],  # Sort descending by `published_date`
    ).run()

    if not most_recent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No TacticalView found"
        )

    # Return the most recent TacticalView
    return most_recent


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
                search_keywords = search_text.lower().split(sep="_")

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
        # Validate the ID format
        if not ObjectId.is_valid(id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format"
            )

        # Retrieve the insight object from the database
        insight = db.Insight.find_one(db.Insight.id == ObjectId(id)).run()
        if not insight:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        # Build the filename for the PDF
        filename = f"{insight.id}.pdf"

        # Get the PDF content using the Boto class
        boto = db.Boto()
        content = boto.get_pdf(filename)
        if content is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File '{filename}' not found in storage",
            )

        # Return the PDF as a streaming response
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
            db.Boto().save_pdf(
                pdf_content=content_bytes,
                filename=f"{new_insight.id}.pdf",
            )

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
            db.Boto().save_pdf(
                pdf_content=base64.b64decode(update_request.content),
                filename=f"{insight.id}.pdf",
            )

        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Base64 content",
            )

    return insight


@router.delete("/{id}", status_code=status.HTTP_200_OK)
def delete_insight(id: str):
    """
    Deletes an Insight by its ID.

    """
    db.Insight.find_one(db.Insight.id == ObjectId(id)).delete().run()
    return {"message": "Insight deleted successfully"}
