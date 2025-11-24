"""Unified Data Service - Centralized data operations for Insights page."""

import math
from typing import Dict, List, Optional, Tuple
from ix.db.client import get_insights
from ix.misc.terminal import get_logger
from ix.web.pages.insights.utils.data_utils import (
    normalize_insight_data,
    serialize_insights,
    filter_insights,
    sort_insights,
)

logger = get_logger(__name__)


class InsightsDataService:
    """Centralized service for managing insights data operations."""

    # Configuration
    PAGE_SIZE = 20
    MAX_ITEMS = 10000

    @staticmethod
    def load_all_insights(
        search_query: Optional[str] = None,
        no_summary_filter: bool = False,
    ) -> List[Dict]:
        """
        Load all insights from database with optional filtering.

        Args:
            search_query: Optional search term
            no_summary_filter: Filter to show only insights without summaries

        Returns:
            List of normalized insight dictionaries
        """
        try:
            # Get insights from database
            if search_query and search_query.strip():
                insights_raw = get_insights(search=search_query, limit=InsightsDataService.MAX_ITEMS)
            else:
                insights_raw = get_insights(limit=InsightsDataService.MAX_ITEMS)

            # Normalize to dict format
            insights_list = [normalize_insight_data(insight) for insight in insights_raw]

            # Apply no-summary filter if active
            if no_summary_filter:
                insights_list = [
                    insight for insight in insights_list
                    if not insight.get("summary") or not str(insight.get("summary", "")).strip()
                ]

            return insights_list

        except Exception as e:
            logger.error(f"Error loading insights: {e}")
            return []

    @staticmethod
    def get_page_data(
        all_insights: List[Dict],
        page: int,
        page_size: Optional[int] = None,
    ) -> Tuple[List[Dict], int, int]:
        """
        Get paginated data from insights list.

        Args:
            all_insights: Complete list of insights
            page: Current page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (page_data, total_count, total_pages)
        """
        page_size = page_size or InsightsDataService.PAGE_SIZE
        total_count = len(all_insights)
        total_pages = max(1, math.ceil(total_count / page_size))

        # Ensure page is valid
        page = max(1, min(page, total_pages))

        # Calculate slice
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        page_data = all_insights[start_idx:end_idx]

        return page_data, total_count, total_pages

    @staticmethod
    def apply_filters(
        insights: List[Dict],
        search: Optional[str] = None,
        no_summary_only: bool = False,
        sort_by: Optional[str] = None,
    ) -> List[Dict]:
        """
        Apply all filters to insights list.

        Args:
            insights: List of insights to filter
            search: Search query
            no_summary_only: Filter for insights without summaries
            sort_by: Sort criteria

        Returns:
            Filtered and sorted insights list
        """
        filtered = filter_insights(
            insights,
            search=search,
            no_summary_only=no_summary_only,
        )

        if sort_by:
            filtered = sort_insights(filtered, sort_by)

        return filtered

    @staticmethod
    def refresh_after_change(no_summary_filter: bool = False) -> Tuple[List[Dict], List[str]]:
        """
        Refresh all data after a change (upload, delete, etc.).

        Args:
            no_summary_filter: Apply no-summary filter

        Returns:
            Tuple of (insights_list, serialized_insights)
        """
        insights_list = InsightsDataService.load_all_insights(
            no_summary_filter=no_summary_filter
        )
        serialized = serialize_insights(insights_list)
        return insights_list, serialized
