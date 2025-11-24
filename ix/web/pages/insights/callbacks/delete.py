"""Delete insight callback."""

import json
from dash import callback, Input, Output, State, ALL
from dash.exceptions import PreventUpdate

from ix.db.client import get_insights
from ix.db.conn import Session
from ix.db.models import Insights
from ix.misc.terminal import get_logger
from ix.web.pages.insights.utils.data_utils import normalize_insight_data, serialize_insights

logger = get_logger(__name__)


@callback(
    Output("insights-table-container", "children", allow_duplicate=True),
    Output("insights-data", "data", allow_duplicate=True),
    Output("total-count", "data", allow_duplicate=True),
    Output("insights-pagination", "total", allow_duplicate=True),
    Output("insights-pagination", "value", allow_duplicate=True),
    Input({"type": "delete-insight-button", "index": ALL}, "n_clicks"),
    State("insights-data", "data"),
    State("no-summary-filter", "data"),
    State("insights-pagination", "value"),
    State("page-size", "data"),
    prevent_initial_call=True,
)
def delete_insight(n_clicks_list, insights_data, no_summary_filter, current_page, page_size):
    """Handle insight deletion."""
    if not any(n_clicks_list):
        raise PreventUpdate

    try:
        import dash
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        insight_id = json.loads(button_id)["index"]

        # Delete from database
        with Session() as session:
            insight_to_delete = session.query(Insights).filter(Insights.id == insight_id).first()
            if insight_to_delete:
                session.delete(insight_to_delete)
                session.commit()

        # Reload all insights from database
        from ix.db.client import get_insights
        insights_raw = get_insights(limit=10000)
        insights_list = [normalize_insight_data(insight) for insight in insights_raw]

        # Apply no-summary filter if active
        if no_summary_filter:
            insights_list = [
                insight for insight in insights_list
                if not insight.get("summary") or not str(insight.get("summary", "")).strip()
            ]

        if not insights_list:
            from ix.web.pages.insights.callbacks.data_loading import create_empty_state
            return create_empty_state(), [], 0, 1, 1

        # Calculate pagination
        page_size = page_size or 20
        total_count = len(insights_list)
        total_pages = max(1, (total_count + page_size - 1) // page_size)

        # Adjust current page if needed (if we deleted the last item on the last page)
        current_page = max(1, min(current_page or 1, total_pages))

        # Get current page data
        start_idx = (current_page - 1) * page_size
        end_idx = start_idx + page_size
        insights_to_show = insights_list[start_idx:end_idx]

        # Create table
        from ix.web.pages.insights.components.table import create_insights_table
        table = create_insights_table(insights_to_show)

        # Serialize for store
        serialized_insights = serialize_insights(insights_list)

        return table, serialized_insights, total_count, total_pages, current_page

    except Exception as e:
        logger.error(f"Error deleting insight: {e}")
        raise PreventUpdate
