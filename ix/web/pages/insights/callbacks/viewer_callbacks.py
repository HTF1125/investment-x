"""PDF Viewer Callbacks - Handle row clicks and PDF viewing."""

import json
from dash import html, callback, Input, Output, State, ALL
from dash.exceptions import PreventUpdate

from ix.misc.terminal import get_logger
from ix.web.pages.insights.utils.data_utils import deserialize_insights
from ix.web.pages.insights.pdf_viewer import create_pdf_viewer

logger = get_logger(__name__)


@callback(
    Output("insights-table-view", "style", allow_duplicate=True),
    Output("pdf-viewer-container", "children", allow_duplicate=True),
    Output("pdf-viewer-container", "style", allow_duplicate=True),
    Output("viewing-insight", "data", allow_duplicate=True),
    Input({"type": "row-click-button", "index": ALL}, "n_clicks"),
    State("insights-data", "data"),
    prevent_initial_call=True,
)
def handle_row_click(n_clicks_list, insights_data):
    """Handle row click to show PDF viewer."""
    if not any(n_clicks_list):
        raise PreventUpdate

    try:
        import dash
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate

        # Get insight ID from clicked button
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        insight_id = json.loads(button_id)["index"]

        # Find the insight in the data
        if not insights_data:
            raise PreventUpdate

        all_insights = deserialize_insights(insights_data)
        insight = next((i for i in all_insights if str(i.get("id")) == str(insight_id)), None)

        if not insight:
            raise PreventUpdate

        # Create PDF viewer
        viewer = create_pdf_viewer(insight)

        # Hide table view and show PDF viewer
        return (
            {"display": "none"},
            viewer,
            {"display": "block", "flex": 1, "overflow": "auto"},
            insight,
        )

    except Exception as e:
        logger.error(f"Error handling row click: {e}")
        raise PreventUpdate


@callback(
    Output("insights-table-view", "style", allow_duplicate=True),
    Output("pdf-viewer-container", "style", allow_duplicate=True),
    Output("viewing-insight", "data", allow_duplicate=True),
    Input("back-to-insights", "n_clicks"),
    Input("close-pdf-viewer", "n_clicks"),
    prevent_initial_call=True,
)
def close_pdf_viewer(back_clicks, close_clicks):
    """Close PDF viewer and return to table view."""
    if not (back_clicks or close_clicks):
        raise PreventUpdate

    return (
        {"flex": 1, "display": "flex", "flexDirection": "column", "minHeight": 0, "overflow": "hidden"},
        {"display": "none"},
        None,
    )
