"""Action Callbacks - Handle delete, upload refresh, and other actions."""

import json
from dash import callback, Input, Output, State, no_update, ALL
from dash.exceptions import PreventUpdate

from ix.db.conn import Session
from ix.db.models import Insights
from ix.misc.terminal import get_logger
from ix.web.pages.insights.services.data_service import InsightsDataService
from ix.web.pages.insights.callbacks.data_callbacks import (
    render_table,
    create_empty_state,
    get_filter_config,
)

logger = get_logger(__name__)


@callback(
    Output("insights-table-container", "children", allow_duplicate=True),
    Output("insights-data", "data", allow_duplicate=True),
    Output("insights-pagination", "total", allow_duplicate=True),
    Output("insights-pagination", "value", allow_duplicate=True),
    Output("current-page", "data", allow_duplicate=True),
    Input({"type": "delete-insight-button", "index": ALL}, "n_clicks"),
    State("insights-data", "data"),
    State("current-page", "data"),
    State("filter-config", "data"),
    prevent_initial_call=True,
)
def handle_delete(n_clicks_list, insights_data, current_page, filter_config):
    """Handle insight deletion."""
    if not any(n_clicks_list):
        raise PreventUpdate

    try:
        import dash
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate

        # Get insight ID from button
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        insight_id = json.loads(button_id)["index"]

        # Delete from database
        with Session() as session:
            insight_to_delete = session.query(Insights).filter(Insights.id == insight_id).first()
            if insight_to_delete:
                session.delete(insight_to_delete)
                session.commit()

        # Refresh data
        _, no_summary = get_filter_config(filter_config)
        insights_list, serialized = InsightsDataService.refresh_after_change(
            no_summary_filter=no_summary
        )

        if not insights_list:
            return create_empty_state(), [], 1, 1, 1

        # Adjust page if needed
        _, _, total_pages = InsightsDataService.get_page_data(insights_list, current_page)
        page = min(current_page or 1, total_pages)

        # Render table
        table, _ = render_table(serialized, page=page)

        return table, serialized, total_pages, page, page

    except Exception as e:
        logger.error(f"Error deleting insight: {e}")
        raise PreventUpdate


@callback(
    Output("insights-table-container", "children", allow_duplicate=True),
    Output("insights-data", "data", allow_duplicate=True),
    Output("insights-pagination", "total", allow_duplicate=True),
    Output("insights-pagination", "value", allow_duplicate=True),
    Output("current-page", "data", allow_duplicate=True),
    Input("output-pdf-upload", "children"),
    State("filter-config", "data"),
    prevent_initial_call=True,
)
def refresh_after_upload(upload_output, filter_config):
    """Refresh table after successful upload."""
    if not upload_output:
        raise PreventUpdate

    try:
        # Refresh data
        _, no_summary = get_filter_config(filter_config)
        insights_list, serialized = InsightsDataService.refresh_after_change(
            no_summary_filter=no_summary
        )

        if not insights_list:
            return create_empty_state(), [], 1, 1, 1

        # Render first page
        table, total_pages = render_table(serialized, page=1)

        return table, serialized, total_pages, 1, 1

    except Exception as e:
        logger.error(f"Error refreshing after upload: {e}")
        raise PreventUpdate
