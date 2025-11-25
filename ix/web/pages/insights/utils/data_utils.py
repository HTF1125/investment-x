"""Data processing utility functions."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union


def normalize_insight_data(insight: Union[Dict, Any]) -> Dict[str, Any]:
    """Normalize insight data from dict or object format to dict."""
    if isinstance(insight, dict):
        return {
            "id": str(insight.get("id", "")),
            "name": insight.get("name") or "Untitled",
            "issuer": insight.get("issuer") or "Unknown",
            "published_date": str(insight.get("published_date", "")) if insight.get("published_date") else "",
            "status": insight.get("status") or "new",
            "summary": insight.get("summary") or "",
            "hash": insight.get("hash") or "",
            "editing": False,
        }
    else:
        # Object format
        return {
            "id": str(insight.id),
            "name": insight.name or "Untitled",
            "issuer": insight.issuer or "Unknown",
            "published_date": str(insight.published_date) if insight.published_date else "",
            "status": insight.status or "new",
            "summary": insight.summary or "",
            "hash": getattr(insight, "hash_tag", None) or getattr(insight, "hash", None) or "",
            "editing": False,
        }


def serialize_insights(insights: List[Dict[str, Any]]) -> List[str]:
    """Serialize insights list to JSON strings for dcc.Store."""
    return [json.dumps(insight) for insight in insights]


def deserialize_insights(insights_json: List[str]) -> List[Dict[str, Any]]:
    """Deserialize JSON strings from dcc.Store to insights list."""
    if not insights_json:
        return []
    return [json.loads(insight_json) for insight_json in insights_json]


def filter_insights(
    insights: List[Dict[str, Any]],
    search: Optional[str] = None,
    issuer: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    no_summary_only: bool = False,
) -> List[Dict[str, Any]]:
    """Filter insights based on various criteria."""
    filtered = insights

    # No summary filter
    if no_summary_only:
        filtered = [
            insight for insight in filtered
            if not insight.get("summary") or not str(insight.get("summary", "")).strip()
        ]

    # Search filter
    if search:
        search_lower = search.lower()
        filtered = [
            insight for insight in filtered
            if (
                search_lower in (insight.get("name", "") or "").lower()
                or search_lower in (insight.get("issuer", "") or "").lower()
                or search_lower in (insight.get("summary", "") or "").lower()
                or search_lower in (insight.get("hash", "") or "").lower()
                or search in (insight.get("published_date", "") or "")
            )
        ]

    # Issuer filter
    if issuer and issuer != "all":
        issuer_lower = issuer.lower()
        filtered = [
            insight for insight in filtered
            if issuer_lower in (insight.get("issuer", "") or "").lower()
        ]

    # Date range filter
    if start_date:
        try:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
            filtered = [
                insight for insight in filtered
                if insight.get("published_date")
                and datetime.strptime(insight["published_date"][:10], "%Y-%m-%d").date() >= start_date_obj
            ]
        except (ValueError, TypeError):
            pass

    if end_date:
        try:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
            filtered = [
                insight for insight in filtered
                if insight.get("published_date")
                and datetime.strptime(insight["published_date"][:10], "%Y-%m-%d").date() <= end_date_obj
            ]
        except (ValueError, TypeError):
            pass

    return filtered


def sort_insights(insights: List[Dict[str, Any]], sort_by: Optional[str] = None) -> List[Dict[str, Any]]:
    """Sort insights by specified criteria."""
    if not sort_by:
        return insights

    def get_published_date(x: Dict[str, Any]) -> str:
        return x.get("published_date", "")

    def get_name(x: Dict[str, Any]) -> str:
        return (x.get("name", "") or "").lower()

    if sort_by == "date_desc":
        return sorted(insights, key=get_published_date, reverse=True)
    elif sort_by == "date_asc":
        return sorted(insights, key=get_published_date)
    elif sort_by == "name_asc":
        return sorted(insights, key=get_name)
    elif sort_by == "name_desc":
        return sorted(insights, key=get_name, reverse=True)

    return insights
