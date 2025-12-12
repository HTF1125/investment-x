"""Unified Data Callbacks - Optimized and consolidated data operations."""

import math
from typing import Tuple
from dash import html, callback, Input, Output, State, no_update
from dash.exceptions import PreventUpdate

from ix.misc.terminal import get_logger
from ix.web.pages.insights.services.data_service import InsightsDataService
from ix.web.pages.insights.components.table import create_insights_table
from ix.web.pages.insights.utils.data_utils import (
    deserialize_insights,
    serialize_insights,
)

logger = get_logger(__name__)


# ============================================================================
# UI State Components
# ============================================================================
def create_empty_state(message: str = "No Insights Found") -> html.Div:
    """Create empty state component with Google Drive integration."""
    folder_id = "1jkpxtpaZophtkx5Lhvb-TAF9BuKY_pPa"
    drive_url = f"https://drive.google.com/drive/folders/{folder_id}"

    return html.Div(
        [
            html.I(
                className="fab fa-google-drive fa-3x",
                style={"color": "#34A853", "marginBottom": "20px"},
            ),
            html.H4("Research Library (Google Drive)", style={"color": "#ffffff", "marginBottom": "10px"}),
            html.P(
                "Access your insights and research documents directly from Google Drive.",
                style={"color": "#94a3b8", "marginBottom": "20px"},
            ),
            # Button to open in new tab
            html.A(
                html.Button(
                    children=[
                        html.I(className="fas fa-external-link-alt", style={"marginRight": "8px"}),
                        "Open in Google Drive"
                    ],
                    style={
                        "padding": "10px 20px",
                        "backgroundColor": "#4285F4",
                        "color": "white",
                        "border": "none",
                        "borderRadius": "4px",
                        "cursor": "pointer",
                        "fontWeight": "600",
                        "fontSize": "14px",
                    }
                ),
                href=drive_url,
                target="_blank",
                style={"textDecoration": "none", "display": "inline-block", "marginBottom": "25px"},
            ),
            # Embedded view (using list layout for better visibility)
            html.Div(
                html.Iframe(
                    src=f"https://drive.google.com/embeddedfolderview?id={folder_id}#list",
                    style={
                        "width": "100%",
                        "height": "100%",
                        "border": "none",
                        "backgroundColor": "#ffffff",
                    },
                ),
                style={
                    "width": "100%",
                    "height": "600px",
                    "borderRadius": "8px",
                    "overflow": "hidden",
                    "border": "1px solid #475569",
                },
            ),
        ],
        style={
            "textAlign": "center",
            "padding": "40px",
            "backgroundColor": "#1e293b",
            "borderRadius": "12px",
            "border": "1px solid #475569",
            "display": "flex",
            "flexDirection": "column",
            "alignItems": "center",
        },
    )


def create_error_state(error_msg: str) -> html.Div:
    """Create error state component."""
    return html.Div(
        [
            html.I(
                className="fas fa-exclamation-triangle fa-3x",
                style={"color": "#ef4444", "marginBottom": "20px"},
            ),
            html.H4("Error Loading Insights", style={"color": "#ffffff"}),
            html.P(error_msg, style={"color": "#94a3b8"}),
        ],
        style={
            "textAlign": "center",
            "padding": "60px 20px",
            "backgroundColor": "#1e293b",
            "borderRadius": "12px",
            "border": "1px solid #475569",
        },
    )


# ============================================================================
# Helper Functions
# ============================================================================
def render_table(insights_data: list, page: int = 1) -> Tuple[html.Div, int]:
    """
    Render table from serialized data with pagination.

    Args:
        insights_data: Serialized insights list
        page: Current page number

    Returns:
        Tuple of (table_component, total_pages)
    """
    if not insights_data:
        return create_empty_state(), 1

    try:
        # Deserialize data
        all_insights = deserialize_insights(insights_data)

        if not all_insights:
            return create_empty_state(), 1

        # Get page data
        page_data, total_count, total_pages = InsightsDataService.get_page_data(
            all_insights, page, page_size=50
        )

        # Create table
        table = create_insights_table(page_data)

        return table, total_pages

    except Exception as e:
        logger.error(f"Error rendering table: {e}")
        return create_error_state(f"Error: {str(e)}"), 1


def get_filter_config(filter_config: dict) -> Tuple[str, bool]:
    """Extract filter configuration safely."""
    if not filter_config:
        return "", False
    return (
        filter_config.get("search", "") or "",
        filter_config.get("no_summary", False) or False,
    )


# ============================================================================
# Callbacks
# ============================================================================
@callback(
    Output("insights-table-container", "children"),
    Output("insights-data", "data"),
    Output("insights-pagination", "total"),
    Output("insights-pagination", "value"),
    Output("current-page", "data"),
    Input("insights-table-container", "id"),
    State("filter-config", "data"),
    prevent_initial_call=False,
)
def load_initial_data(container_id, filter_config):
    """Load initial insights data on page load."""
    try:
        # Get filter config
        search_query, no_summary = get_filter_config(filter_config)

        # Load data
        insights_list = InsightsDataService.load_all_insights(
            search_query=search_query if search_query else None,
            no_summary_filter=no_summary,
        )

        if not insights_list:
            return create_empty_state(), [], 1, 1, 1

        # Serialize for store
        serialized = serialize_insights(insights_list)

        # Render first page
        table, total_pages = render_table(serialized, page=1)

        return table, serialized, total_pages, 1, 1

    except Exception as e:
        logger.error(f"Error loading initial data: {e}")
        return create_error_state(str(e)), [], 1, 1, 1


@callback(
    Output("insights-table-container", "children", allow_duplicate=True),
    Output("insights-pagination", "total", allow_duplicate=True),
    Input("insights-pagination", "value"),
    State("insights-data", "data"),
    prevent_initial_call=True,
)
def handle_pagination(current_page, insights_data):
    """Handle pagination changes."""
    if not insights_data or not current_page:
        raise PreventUpdate

    try:
        table, total_pages = render_table(insights_data, page=current_page)
        return table, total_pages

    except Exception as e:
        logger.error(f"Error handling pagination: {e}")
        raise PreventUpdate


@callback(
    Output("insights-table-container", "children", allow_duplicate=True),
    Output("insights-data", "data", allow_duplicate=True),
    Output("insights-pagination", "total", allow_duplicate=True),
    Output("insights-pagination", "value", allow_duplicate=True),
    Output("current-page", "data", allow_duplicate=True),
    Output("filter-config", "data", allow_duplicate=True),
    Input("terminal-search", "n_submit"),
    State("terminal-search", "value"),
    State("filter-config", "data"),
    prevent_initial_call=True,
)
def handle_search(search_submit, search_value, current_filter_config):
    """Handle search with unified filtering."""
    try:
        # Get current filter state
        _, no_summary = get_filter_config(current_filter_config)

        # Update filter config
        new_filter_config = {
            "search": search_value or "",
            "no_summary": no_summary,
        }

        # Load data (server-side search first for performance)
        insights_list = InsightsDataService.load_all_insights(
            search_query=search_value if search_value else None,
            no_summary_filter=no_summary,
        )

        # Always apply client-side filters to ensure fields like 'hash' are searchable
        filtered = InsightsDataService.apply_filters(
            insights_list,
            search=search_value or None,
            no_summary_only=no_summary,
        )

        # Fallback: if nothing found and a search term exists, fetch all and filter locally
        if (not filtered) and (search_value and search_value.strip()):
            insights_all = InsightsDataService.load_all_insights(
                search_query=None, no_summary_filter=no_summary
            )
            filtered = InsightsDataService.apply_filters(
                insights_all, search=search_value, no_summary_only=no_summary
            )

        if not filtered:
            empty = create_empty_state("No Results Found")
            return empty, [], 1, 1, 1, new_filter_config

        # Serialize
        serialized = serialize_insights(filtered)

        # Render first page
        table, total_pages = render_table(serialized, page=1)

        return table, serialized, total_pages, 1, 1, new_filter_config

    except Exception as e:
        logger.error(f"Error handling search: {e}")
        return no_update, no_update, no_update, no_update, no_update, no_update


@callback(
    Output("terminal-search", "value"),
    Output("filter-config", "data", allow_duplicate=True),
    Input("clear-search", "n_clicks"),
    State("filter-config", "data"),
    prevent_initial_call=True,
)
def clear_search(n_clicks, current_filter_config):
    """Clear search and reset filters."""
    if not n_clicks:
        raise PreventUpdate

    _, no_summary = get_filter_config(current_filter_config)
    new_config = {"search": "", "no_summary": no_summary}

    return "", new_config


@callback(
    Output("insights-count-badge", "children"),
    Input("insights-data", "data"),
)
def update_count_badge(insights_data):
    """Update document count badge."""
    if not insights_data:
        return "0 documents"

    try:
        all_insights = deserialize_insights(insights_data)
        count = len(all_insights)
        return f"{count} document{'s' if count != 1 else ''}"
    except Exception:
        return "0 documents"
