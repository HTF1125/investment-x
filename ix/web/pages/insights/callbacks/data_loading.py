"""Data loading and pagination callbacks."""

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


def create_empty_state(message: str = "No Insights Found") -> html.Div:
    """Create empty state component."""
    return html.Div(
        [
            html.I(
                className="fas fa-search fa-3x",
                style={"color": "#64748b", "marginBottom": "20px"},
            ),
            html.H4(message, style={"color": "#ffffff", "marginBottom": "10px"}),
            html.P(
                "Upload some documents to get started with AI-powered insights.",
                style={"color": "#94a3b8"},
            ),
        ],
        style={
            "textAlign": "center",
            "padding": "60px 20px",
            "backgroundColor": "#1e293b",
            "borderRadius": "12px",
            "border": "1px solid #475569",
        },
    )


@callback(
    Output("insights-table-container", "children"),
    Output("insights-data", "data"),
    Output("total-count", "data"),
    Output("insights-pagination", "total"),
    Input("insights-table-container", "id"),
    State("no-summary-filter", "data"),
    State("search-query", "data"),
    State("filter-state", "data"),
    State("page-size", "data"),
)
def load_insights(
    container_id,
    no_summary_filter: bool,
    search_query: str,
    filter_state: dict,
    page_size: int,
) -> Tuple:
    """Load initial insights from database."""
    try:
        # Check if we have active filters - if so, don't reload here
        # The search callback should handle filtered views
        has_active_filters = (
            (search_query and search_query.strip()) or
            (filter_state and isinstance(filter_state, dict) and any([
                filter_state.get("search"),
                filter_state.get("sort"),
                filter_state.get("issuer") and filter_state.get("issuer") != "all",
                filter_state.get("start_date"),
                filter_state.get("end_date"),
            ]))
        )

        # If there are active filters and we already have data, don't reload
        # This prevents overwriting filtered data
        if has_active_filters:
            raise PreventUpdate

        # Get all insights (no filters active)
        insights_raw = get_insights(limit=10000)

        # Normalize to dict format
        insights_list = [normalize_insight_data(insight) for insight in insights_raw]

        # Apply no-summary filter only if active
        if no_summary_filter:
            insights_list = [
                insight for insight in insights_list
                if not insight.get("summary") or not str(insight.get("summary", "")).strip()
            ]

        if not insights_list:
            return create_empty_state(), [], 0, 1

        # Load first page
        page_size = page_size or 20
        insights_to_show = insights_list[:page_size]

        # Create table with first page
        table = create_insights_table(insights_to_show)

        # Serialize all insights for store
        serialized_insights = serialize_insights(insights_list)
        total_count = len(insights_list)
        total_pages = max(1, (total_count + page_size - 1) // page_size)

        return table, serialized_insights, total_count, total_pages

    except PreventUpdate:
        raise
    except Exception as e:
        logger.error(f"Error loading insights: {e}")
        return (
            html.Div(
                [
                    html.I(
                        className="fas fa-exclamation-triangle fa-3x",
                        style={"color": "#ef4444", "marginBottom": "20px"},
                    ),
                    html.H4("Error Loading Insights", style={"color": "#ffffff"}),
                    html.P(f"Failed to load insights: {str(e)}", style={"color": "#94a3b8"}),
                ],
                style={
                    "textAlign": "center",
                    "padding": "60px 20px",
                    "backgroundColor": "#1e293b",
                    "borderRadius": "12px",
                },
            ),
            [],
            0,
            1,
        )


# Pagination callback removed - using infinite scroll instead
