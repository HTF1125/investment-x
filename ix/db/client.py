from typing import Union, List, Set, Tuple, Dict, Optional
import pandas as pd
import re
import io
from datetime import datetime
import base64
from ix.misc import get_logger, periods
from .models import Universe, Insights, TacticalView, Timeseries, Publishers
from .query import *

# Configure logging
logger = get_logger(__name__)


def get_timeseries(code: str) -> Timeseries:
    """
    Retrieves a time series for the specified asset code.
    Caching is enabled so that repeated calls with the same parameters
    do not re-query the database.
    """
    from ix.db.conn import Session

    with Session() as session:
        ts = session.query(Timeseries).filter(Timeseries.code == code).first()
        if ts is None:
            raise ValueError(f"Timeseries not found for code: {code}")
        return ts


def get_insight_by_id(id: str) -> Insights:
    """
    Retrieves an insight by its ID from the database.
    Caching is enabled to avoid repeated database lookups for the same insight.
    """
    from ix.db.conn import Session

    with Session() as session:
        insight = session.query(Insights).filter(Insights.id == id).first()
        if insight is None:
            raise ValueError(f"Insight not found for id: {id}")
        return insight


def _get_insight_content_bytes(id: str) -> bytes:
    """
    Internal helper function to retrieve the raw PDF bytes for an insight.
    This function is cached so that the PDF content is not repeatedly
    fetched from storage.
    """
    from ix.db.conn import Session

    with Session() as session:
        insight = session.query(Insights).filter(Insights.id == id).first()
        if not insight:
            raise ValueError("Insight not found")
        if not insight.pdf_content:
            raise ValueError("PDF content not found")
        return bytes(insight.pdf_content)


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
) -> List[Insights]:
    """
    Retrieves insights from the database sorted by published_date descending,
    with optional search and pagination.
    """
    try:
        from ix.db.conn import Session
        from sqlalchemy import or_, and_
        from sqlalchemy.orm import load_only

        with Session() as session:
            query = session.query(Insights).options(
                load_only(
                    Insights.id,
                    Insights.name,
                    Insights.issuer,
                    Insights.published_date,
                    Insights.status,
                    Insights.summary,
                )
            )

            if search:
                # Attempt to extract a date in YYYY-MM-DD format
                date_pattern = r"\d{4}-\d{2}-\d{2}"
                date_match = re.search(date_pattern, search)
                if date_match:
                    search_date_str = date_match.group(0)
                    try:
                        search_date = datetime.strptime(
                            search_date_str, "%Y-%m-%d"
                        ).date()
                        query = query.filter(Insights.published_date == search_date)
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
                            or_(
                                Insights.issuer.ilike(f"%{keyword}%"),
                                Insights.name.ilike(f"%{keyword}%"),
                            )
                        )
                    query = query.filter(and_(*conditions))

            insights = (
                query.order_by(Insights.published_date.desc())
                .offset(skip)
                .limit(limit)
                .all()
            )
            # Extract all attributes while session is active to avoid detached instance errors
            insights_data = []
            for insight in insights:
                # Convert date to ISO format string for JSON serialization
                published_date_str = None
                if insight.published_date:
                    if isinstance(insight.published_date, str):
                        published_date_str = insight.published_date
                    elif hasattr(insight.published_date, "isoformat"):
                        published_date_str = insight.published_date.isoformat()
                    else:
                        published_date_str = str(insight.published_date)

                insights_data.append(
                    {
                        "id": insight.id,
                        "name": insight.name,
                        "issuer": insight.issuer,
                        "published_date": published_date_str,
                        "status": insight.status,
                        "summary": insight.summary,
                    }
                )
            return insights_data
    except Exception as e:
        raise Exception(f"Error occurred while fetching insights: {str(e)}")


def _serialize_publisher(publisher: Publishers) -> Dict[str, Optional[str]]:
    """Convert a Publishers ORM instance into a plain dict."""

    last_visited = None
    if getattr(publisher, "last_visited", None) is not None:
        try:
            last_visited = publisher.last_visited.isoformat()
        except AttributeError:
            last_visited = str(publisher.last_visited)

    return {
        "id": str(publisher.id),
        "name": publisher.name,
        "url": publisher.url,
        "frequency": publisher.frequency,
        "remark": publisher.remark,
        "last_visited": last_visited,
    }


def get_publishers(limit: Optional[int] = None) -> List[Dict[str, Optional[str]]]:
    """Fetch publishers ordered by most recently visited."""

    from ix.db.conn import Session
    from sqlalchemy import asc, nullsfirst

    with Session() as session:
        query = session.query(Publishers)
        query = query.order_by(nullsfirst(asc(Publishers.last_visited)))
        if limit is not None:
            query = query.limit(limit)
        publishers = query.all()

        return [_serialize_publisher(publisher) for publisher in publishers]


def create_publisher(
    name: str,
    url: str,
    frequency: Optional[str] = None,
    remark: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    """Create a new publisher entry."""

    if not name or not url:
        raise ValueError("Both name and url are required to create a publisher")

    from ix.db.conn import Session

    normalized_frequency = frequency or "Unclassified"

    with Session() as session:
        existing = session.query(Publishers).filter(Publishers.url == url).first()
        if existing:
            raise ValueError("A publisher with this URL already exists")

        publisher = Publishers(
            name=name.strip(),
            url=url.strip(),
            frequency=normalized_frequency.strip() if normalized_frequency else "Unclassified",
            remark=remark.strip() if remark else None,
        )

        session.add(publisher)
        session.flush()
        session.refresh(publisher)

        return _serialize_publisher(publisher)


def touch_publisher(publisher_id: str) -> Dict[str, Optional[str]]:
    """Update a publisher's last_visited timestamp and return the updated record."""

    if not publisher_id:
        raise ValueError("publisher_id is required")

    from ix.db.conn import Session

    with Session() as session:
        publisher = session.query(Publishers).filter(Publishers.id == publisher_id).first()
        if not publisher:
            raise ValueError("Publisher not found")

        publisher.last_visited = datetime.utcnow()
        session.flush()
        session.refresh(publisher)

        return _serialize_publisher(publisher)


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
        from ix.db.conn import Session

        content_bytes = None
        if getattr(add_request, "content", None):
            try:
                content_bytes = base64.b64decode(add_request.content)
            except Exception as e:
                raise ValueError("Invalid Base64 content") from e

        new_insight = Insights(
            issuer=add_request.issuer,
            name=add_request.name,
            published_date=add_request.published_date,
            summary=add_request.summary,
            pdf_content=content_bytes,
        )

        with Session() as session:
            session.add(new_insight)
            session.refresh(new_insight)

            return new_insight
    except Exception as e:
        logger.error("Failed to add insight: %s", e)
        raise Exception("Failed to add insight") from e


def update_insight(id: str, update_request):
    """
    Updates an Insight by its ID with the provided data.
    """
    from ix.db.conn import Session

    with Session() as session:
        insight = session.query(Insights).filter(Insights.id == id).first()
        if not insight:
            raise ValueError("Insight not found")

        updated_fields = {
            key: value
            for key, value in update_request.__dict__.items()
            if value is not None and key != "content"
        }

        if not updated_fields and not getattr(update_request, "content", None):
            raise ValueError("No fields provided for update")

        for key, value in updated_fields.items():
            setattr(insight, key, value)

        if getattr(update_request, "content", None):
            try:
                pdf_content = base64.b64decode(update_request.content)
                insight.pdf_content = pdf_content
            except Exception as e:
                raise ValueError("Invalid Base64 content") from e

        session.refresh(insight)
        return insight


def delete_insight(id: str):
    """
    Deletes an Insight by its ID.
    """
    from ix.db.conn import Session

    with Session() as session:
        insight = session.query(Insights).filter(Insights.id == id).first()
        if not insight:
            raise ValueError("Insight not found")
        session.delete(insight)
        return {"message": "Insight deleted successfully"}


def update_insight_summary(id: str):
    """
    Updates the summary of an Insight by processing its PDF content.
    """
    from ix.misc import PDFSummarizer, Settings
    from ix.db.conn import Session

    with Session() as session:
        insight = session.query(Insights).filter(Insights.id == id).first()
        if not insight:
            raise ValueError("Insight not found")

        report = PDFSummarizer(Settings.openai_secret_key).process_insights(
            insight.get_content()
        )
        insight.summary = report
        session.refresh(insight)
        return report


def create_insight_with_pdf(base64_content: str, filename: str):
    """
    Creates a new insight from an uploaded PDF (base64 encoded).
    """
    try:
        pdf_data = base64.b64decode(base64_content)
        insight = Insights(
            name=filename,
            issuer="Uploaded PDF",
            published_date=datetime.now().date(),
            summary="Processing...",
            pdf_content=pdf_data,
        )
        return insight
    except Exception as e:
        raise Exception(f"Error creating insight from PDF: {str(e)}")


def get_recent_tactical_view() -> Optional[TacticalView]:
    """Get the most recent tactical view."""
    from ix.db.conn import Session

    with Session() as session:
        return (
            session.query(TacticalView)
            .order_by(TacticalView.published_date.desc())
            .first()
        )
