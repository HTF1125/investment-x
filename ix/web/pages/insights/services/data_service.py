"""Unified Data Service - Centralized data operations for Insights page."""

import math
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from ix.db.client import get_insights
from ix.misc.terminal import get_logger
from ix.web.pages.insights.services.drive_client import drive_client
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
        Load all insights directly from Google Drive.

        Args:
            search_query: Optional search term
            no_summary_filter: Filter to show only insights without summaries

        Returns:
            List of normalized insight dictionaries
        """
        try:
            files = drive_client.list_files()

            insights_list = []
            for f in files:
                # Create a virtual object that mimics the SQLAlchemy model
                class VirtualInsight:
                    def __init__(self, data):
                        self.id = data['id']
                        self.name = data['name']
                        self.url = data['webViewLink']
                        # Handle createdTime format 2023-10-25T12:00:00.000Z
                        try:
                            self.created = datetime.fromisoformat(data['createdTime'].replace('Z', '+00:00'))
                        except:
                            self.created = datetime.now()
                        self.published_date = self.created.date()
                        self.summary = None # Not available in direct mode
                        self.issuer = "Unknown"

                        # Parse filename for better metadata
                        try:
                            base_name = os.path.splitext(self.name)[0]
                            parts = base_name.split('_')
                            if len(parts) >= 3:
                                date_str = parts[0]
                                self.issuer = parts[1]
                                self.name = "_".join(parts[2:])
                                self.published_date = datetime.strptime(date_str, "%Y%m%d").date()
                        except:
                            pass

                    def __getitem__(self, item):
                        return getattr(self, item)

                    def get(self, item, default=None):
                        return getattr(self, item, default)

                # Normalize expects an object it can getattr from, or a dict.
                # normalize_insight_data likely does hasattr checks or .get()
                # Let's inspect normalize_insight_data if this fails, but for now returned normalized dicts directly

                v_insight = VirtualInsight(f)

                # Manual normalization to ensure dict format
                normalized = {
                    "id": v_insight.id,
                    "name": v_insight.name,
                    "issuer": v_insight.issuer,
                    "published_date": str(v_insight.published_date) if v_insight.published_date else "",
                    "summary": None,
                    "url": v_insight.url, # Special field for direct link
                    "created": str(v_insight.created) if v_insight.created else "",
                }
                insights_list.append(normalized)

            # Apply local search filtering (naive)
            if search_query and search_query.strip():
                q = search_query.lower()
                insights_list = [
                    i for i in insights_list
                    if q in i['name'].lower() or q in i['issuer'].lower()
                ]

            # Sort by published_date descending (User Request)
            insights_list.sort(key=lambda x: x.get('published_date', ''), reverse=True)

            return insights_list

        except Exception as e:
            logger.error(f"Error loading insights from Drive: {e}")
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
