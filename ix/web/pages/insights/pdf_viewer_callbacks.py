"""
PDF Viewer Callbacks for Insights
Handles switching between insights list and PDF viewer
"""

import json
import dash
from dash import callback, Input, Output, State, no_update, ALL
from dash.exceptions import PreventUpdate
import dash_mantine_components as dmc

from ix import db
from ix.misc.terminal import get_logger
from .pdf_viewer import create_pdf_viewer

logger = get_logger(__name__)


@callback(
    Output("pdf-viewer-container", "children"),
    Output("current-view", "data"),
    Output("current-insight", "data"),
    Input({"type": "view-pdf-button", "index": ALL}, "n_clicks"),
    State("insights-data", "data"),
    prevent_initial_call=True,
)
def handle_pdf_view_request(n_clicks_list, insights_data):
    """Handle PDF view button clicks"""
    if not any(n_clicks_list) or not insights_data:
        raise PreventUpdate

    # Find which button was clicked
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    triggered_prop = ctx.triggered[0]["prop_id"]
    insight_id = json.loads(triggered_prop.split(".")[0])["index"]

    # Find the insight data
    insight_data = None
    for insight_json in insights_data:
        insight = json.loads(insight_json)
        if str(insight.get("id")) == str(insight_id):
            insight_data = insight
            break

    if not insight_data:
        logger.error(f"Insight with ID {insight_id} not found")
        raise PreventUpdate

    # Create PDF viewer
    pdf_viewer = create_pdf_viewer(insight_data)

    # Return the PDF viewer layout and update stores
    return pdf_viewer, "pdf-viewer", insight_data


@callback(
    Output("current-view", "data", allow_duplicate=True),
    Input("back-to-insights", "n_clicks"),
    Input("close-pdf-viewer", "n_clicks"),
    prevent_initial_call=True,
)
def handle_back_to_insights(back_clicks, close_clicks):
    """Handle back to insights list"""
    if not (back_clicks or close_clicks):
        raise PreventUpdate

    # Return to insights list view
    return "insights-list"


@callback(
    Output("pdf-viewer-container", "style", allow_duplicate=True),
    Output("insights-container", "style", allow_duplicate=True),
    Input("current-view", "data"),
    prevent_initial_call=True,
)
def toggle_view_visibility(current_view):
    """Show/hide PDF viewer and insights list based on current view"""
    if current_view == "pdf-viewer":
        return {"display": "block"}, {"display": "none"}
    else:
        return {"display": "none"}, {"display": "block"}
