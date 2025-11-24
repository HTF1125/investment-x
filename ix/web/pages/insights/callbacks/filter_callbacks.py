"""Filter Callbacks - Handle filter toggles and updates."""

from dash import callback, Input, Output, State, no_update
from dash.exceptions import PreventUpdate

from ix.misc.terminal import get_logger
from ix.web.pages.insights.services.data_service import InsightsDataService
from ix.web.pages.insights.callbacks.data_callbacks import (
    render_table,
    create_empty_state,
    get_filter_config,
)
from ix.web.pages.insights.utils.data_utils import serialize_insights

logger = get_logger(__name__)


@callback(
    Output("insights-table-container", "children", allow_duplicate=True),
    Output("insights-data", "data", allow_duplicate=True),
    Output("insights-pagination", "total", allow_duplicate=True),
    Output("insights-pagination", "value", allow_duplicate=True),
    Output("current-page", "data", allow_duplicate=True),
    Output("filter-config", "data", allow_duplicate=True),
    Output("filter-no-summary", "variant"),
    Input("filter-no-summary", "n_clicks"),
    State("filter-config", "data"),
    prevent_initial_call=True,
)
def toggle_no_summary_filter(n_clicks, current_filter_config):
    """Toggle no-summary filter."""
    if not n_clicks:
        raise PreventUpdate

    try:
        # Get current state
        search_query, current_state = get_filter_config(current_filter_config)
        new_state = not current_state

        # Update filter config
        new_filter_config = {
            "search": search_query,
            "no_summary": new_state,
        }

        # Load data with new filter
        insights_list = InsightsDataService.load_all_insights(
            search_query=search_query if search_query else None,
            no_summary_filter=new_state,
        )

        if not insights_list:
            message = (
                "No insights without summaries found." if new_state
                else "No insights found."
            )
            empty = create_empty_state(message)
            variant = "filled" if new_state else "light"
            return empty, [], 1, 1, 1, new_filter_config, variant

        # Serialize
        serialized = serialize_insights(insights_list)

        # Render first page
        table, total_pages = render_table(serialized, page=1)

        # Update button variant
        variant = "filled" if new_state else "light"

        return table, serialized, total_pages, 1, 1, new_filter_config, variant

    except Exception as e:
        logger.error(f"Error toggling filter: {e}")
        return no_update, no_update, no_update, no_update, no_update, no_update, no_update
