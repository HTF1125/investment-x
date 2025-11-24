"""Pagination callbacks for Insights page."""

import math
from dash import html, callback, Input, Output, State, no_update
from dash.exceptions import PreventUpdate

from ix.web.pages.insights.utils.data_utils import deserialize_insights
from ix.web.pages.insights.components.table import create_insights_table


@callback(
    Output("insights-table-container", "children", allow_duplicate=True),
    Output("insights-pagination", "total", allow_duplicate=True),
    Input("insights-pagination", "value"),
    State("insights-data", "data"),
    State("total-count", "data"),
    State("page-size", "data"),
    prevent_initial_call=True,
)
def update_table_on_pagination(
    current_page: int,
    insights_data: list,
    total_count: int,
    page_size: int,
):
    """Update table when pagination changes."""
    if not insights_data or not current_page:
        raise PreventUpdate

    try:
        # Deserialize insights
        all_insights = deserialize_insights(insights_data)

        # Get page size
        page_size = page_size or 20

        # Calculate pagination
        total_count = len(all_insights) if not total_count else total_count
        total_pages = max(1, math.ceil(total_count / page_size))

        # Ensure current_page is valid
        current_page = max(1, min(current_page, total_pages))

        # Calculate slice indices
        start_idx = (current_page - 1) * page_size
        end_idx = start_idx + page_size

        # Get insights for current page
        insights_to_show = all_insights[start_idx:end_idx]

        # Create table
        table = create_insights_table(insights_to_show)

        return table, total_pages

    except Exception as e:
        from ix.misc.terminal import get_logger
        logger = get_logger(__name__)
        logger.error(f"Error updating table on pagination: {e}")
        raise PreventUpdate
