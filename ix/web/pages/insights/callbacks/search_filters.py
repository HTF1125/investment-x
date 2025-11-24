"""Search and filter callbacks."""

from typing import Tuple
from dash import html, callback, Input, Output, State, no_update
from dash.exceptions import PreventUpdate

from ix.db.client import get_insights
from ix.misc.terminal import get_logger
from ix.web.pages.insights.components.table import create_insights_table
from ix.web.pages.insights.utils.data_utils import (
    normalize_insight_data,
    serialize_insights,
    filter_insights,
    sort_insights,
)

logger = get_logger(__name__)


@callback(
    Output("insights-table-container", "children", allow_duplicate=True),
    Output("insights-data", "data", allow_duplicate=True),
    Output("total-count", "data", allow_duplicate=True),
    Output("insights-pagination", "total", allow_duplicate=True),
    Output("insights-pagination", "value", allow_duplicate=True),
    Output("search-query", "data", allow_duplicate=True),
    Output("filter-state", "data", allow_duplicate=True),
    Input("search-button", "n_clicks"),
    Input("insights-search", "n_submit"),
    State("insights-search", "value"),
    State("no-summary-filter", "data"),
    State("page-size", "data"),
    prevent_initial_call=True,
)
def search_and_filter_insights(
    search_clicks,
    search_submit,
    search_value,
    no_summary_filter,
    page_size,
):
    """Search and filter insights."""
    try:
        # Get all insights
        if search_value:
            insights_raw = get_insights(search=search_value, limit=10000)
        else:
            insights_raw = get_insights(limit=10000)

        # Normalize to dict format
        insights_list = [normalize_insight_data(insight) for insight in insights_raw]

        # Apply filters (only search and no-summary filter now)
        filtered = filter_insights(
            insights_list,
            search=search_value,
            issuer=None,
            start_date=None,
            end_date=None,
            no_summary_only=no_summary_filter or False,
        )

        if not filtered:
            from ix.web.pages.insights.callbacks.data_loading import create_empty_state
            empty = create_empty_state("No Results Found")
            filter_state = {
                "search": search_value or "",
            }
            return empty, [], 0, 1, 1, search_value or "", filter_state

        # Load first page
        page_size = page_size or 20
        insights_to_show = filtered[:page_size]

        # Create table
        table = create_insights_table(insights_to_show)

        # Serialize for store
        serialized = serialize_insights(filtered)

        # Store filter state
        filter_state = {
            "search": search_value or "",
        }

        total_count = len(filtered)
        total_pages = max(1, (total_count + page_size - 1) // page_size)

        return table, serialized, total_count, total_pages, 1, search_value or "", filter_state

    except Exception as e:
        logger.error(f"Error searching insights: {e}")
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update


@callback(
    Output("insights-search", "value"),
    Output("search-query", "data", allow_duplicate=True),
    Output("filter-state", "data", allow_duplicate=True),
    Input("clear-search", "n_clicks"),
    prevent_initial_call=True,
)
def clear_search_inputs(n_clicks):
    """Clear search input and filter state."""
    if not n_clicks:
        raise PreventUpdate
    return "", "", {}
