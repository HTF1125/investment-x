from typing import Union, List, Set, Tuple, Dict, Optional
import pandas as pd
import re
import io
from datetime import datetime
import base64
from ix.misc import get_logger, periods
from .models import Universe, Insight, TacticalView, Timeseries
from .boto import Boto


# Configure logging
logger = get_logger(__name__)

def get_timeseries(code: str) -> Timeseries:
    """
    Retrieves a time series for the specified asset code.
    Caching is enabled so that repeated calls with the same parameters
    do not re-query the database.
    """
    ts = Timeseries.find_one({"code": code}).run()
    if ts is None:
        raise
    return ts


def get_insight_by_id(id: str) -> Insight:
    """
    Retrieves an insight by its ID from the database.
    Caching is enabled to avoid repeated database lookups for the same insight.
    """
    insight = Insight.find_one({"id": str(id)}).run()
    if insight is None:
        raise ValueError(f"Insight not found for id: {id}")
    return insight


def _get_insight_content_bytes(id: str) -> bytes:
    """
    Internal helper function to retrieve the raw PDF bytes for an insight.
    This function is cached so that the PDF content is not repeatedly
    fetched from storage.
    """
    insight = Insight.find_one({"id": str(id)}).run()
    if not insight:
        raise ValueError("Insight not found")
    filename = f"{insight.id}.pdf"
    boto = Boto()
    content = boto.get_pdf(filename)
    if content is None:
        raise ValueError("PDF content not found")
    return content


def get_insight_content(id: str) -> io.BytesIO:
    """
    Retrieves the PDF content for an insight as a BytesIO object.
    The raw bytes are cached, and a new BytesIO instance is returned on each call.
    """
    content_bytes = _get_insight_content_bytes(id)
    return io.BytesIO(content_bytes)


def get_insights(
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 20,
) -> List[Insight]:
    """
    Retrieves insights from the database sorted by published_date descending,
    with optional search and pagination.
    """
    try:
        query = {}
        if search:
            # Attempt to extract a date in YYYY-MM-DD format
            date_pattern = r"\d{4}-\d{2}-\d{2}"
            date_match = re.search(date_pattern, search)
            if date_match:
                search_date_str = date_match.group(0)
                try:
                    search_date = datetime.strptime(search_date_str, "%Y-%m-%d")
                    query["published_date"] = {"$eq": search_date}
                except ValueError:
                    pass
                # Remove the date portion for text search
                search_text = search.replace(search_date_str, "").strip()
            else:
                search_text = search

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

        insights = Insight.find(query).sort("-published_date").skip(skip).limit(limit)
        return list(insights)
    except Exception as e:
        raise Exception(f"Error occurred while fetching insights: {str(e)}")


def get_insight_content_by_id(id: str) -> io.BytesIO:
    """
    Retrieves the PDF content for an insight by its ID.
    (This function is simply an alias for get_insight_content.)
    """
    return get_insight_content(id)


def add_insight(add_request):
    """
    Adds a new Insight with the provided data.
    """
    try:
        content_bytes = None
        if getattr(add_request, "content", None):
            try:
                content_bytes = base64.b64decode(add_request.content)
            except Exception as e:
                raise ValueError("Invalid Base64 content") from e

        new_insight = Insight(
            issuer=add_request.issuer,
            name=add_request.name,
            published_date=add_request.published_date,
            summary=add_request.summary,
        ).create()

        if content_bytes:
            Boto().save_pdf(
                pdf_content=content_bytes,
                filename=f"{new_insight.id}.pdf",
            )

        return new_insight
    except Exception as e:
        logger.error("Failed to add insight: %s", e)
        raise Exception("Failed to add insight") from e


def update_insight(id: str, update_request):
    """
    Updates an Insight by its ID with the provided data.
    """

    updated_fields = {
        key: value
        for key, value in update_request.__dict__.items()
        if value is not None and key != "content"
    }

    if not updated_fields and not getattr(update_request, "content", None):
        raise ValueError("No fields provided for update")

    insight = Insight.find_one({"id": str(id)}).run()
    if not insight:
        raise ValueError("Insight not found")

    insight.set(updated_fields)

    if getattr(update_request, "content", None):
        try:
            pdf_content = base64.b64decode(update_request.content)
            Boto().save_pdf(
                pdf_content=pdf_content,
                filename=f"{insight.id}.pdf",
            )
        except Exception as e:
            raise ValueError("Invalid Base64 content") from e

    return insight


def delete_insight(id: str):
    """
    Deletes an Insight by its ID.
    """
    Insight.find_one({"id": str(id)}).run()
    return {"message": "Insight deleted successfully"}


def update_insight_summary(id: str):
    """
    Updates the summary of an Insight by processing its PDF content.
    """
    from ix.misc import PDFSummarizer, Settings

    insight = Insight.find_one({"id": str(id)}).run()
    if not insight:
        raise ValueError("Insight not found")

    report = PDFSummarizer(Settings.openai_secret_key).process_insights(
        insight.get_content()
    )
    insight.set({"summary": report})
    return report


def create_insight_with_pdf(base64_content: str, filename: str):
    """
    Creates a new insight from an uploaded PDF (base64 encoded).
    """
    try:
        pdf_data = base64.b64decode(base64_content)
        insight = Insight(
            name=filename,
            issuer="Uploaded PDF",
            published_date=datetime.now(),
            summary="Processing...",
        )
        return insight
    except Exception as e:
        raise Exception(f"Error creating insight from PDF: {str(e)}")


def get_recent_tactical_view() -> Optional[TacticalView]:
    return TacticalView.find_one({}, sort=[("published_date", -1)]).run()
