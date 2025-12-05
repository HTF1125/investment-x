"""Publishers callbacks."""

from typing import Any
from dash import html, callback, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from ix.misc.terminal import get_logger
from ix.web.pages.insights.components.publishers_section import create_publishers_list_items

logger = get_logger(__name__)


@callback(
    Output("insight-sources-list", "children"),
    Input("publishers-refresh-token", "data"),
    Input("publishers-refresh-interval", "n_intervals"),
    prevent_initial_call=False,
)
def update_publishers_list(refresh_token, n_intervals):
    """Update publishers list."""
    try:
        publishers = get_publishers()
        return create_publishers_list_items(publishers)
    except Exception as e:
        logger.error(f"Error loading publishers: {e}")
        return dmc.Text("Error loading publishers.", size="sm", c="red", ta="center")


@callback(
    Output("add-publisher-modal", "is_open"),
    Input("add-publisher-button", "n_clicks"),
    Input("close-add-publisher-modal", "n_clicks"),
    Input("cancel-add-publisher", "n_clicks"),
    State("add-publisher-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_add_publisher_modal(add_clicks, close_clicks, cancel_clicks, is_open):
    """Toggle add publisher modal."""
    if add_clicks or close_clicks or cancel_clicks:
        return not is_open
    return is_open


@callback(
    Output("add-publisher-feedback", "children"),
    Output("publishers-refresh-token", "data"),
    Output("add-publisher-modal", "is_open", allow_duplicate=True),
    Output("publisher-name-input", "value"),
    Output("publisher-url-input", "value"),
    Output("publisher-frequency-input", "value"),
    Input("submit-add-publisher", "n_clicks"),
    State("publisher-name-input", "value"),
    State("publisher-url-input", "value"),
    State("publisher-frequency-input", "value"),
    prevent_initial_call=True,
)
def submit_add_publisher(n_clicks, name, url, frequency):
    """Handle publisher submission."""
    if not n_clicks:
        raise PreventUpdate

    try:
        if not name or not url:
            return (
                dmc.Alert("Name and URL are required.", color="red", title="Error"),
                None,
                True,
                name or "",
                url or "",
                frequency or "Weekly",
            )

        create_publisher(name=name, url=url, frequency=frequency or "Weekly")
        import uuid
        return (
            dmc.Alert(f"Publisher '{name}' added successfully!", color="green", title="Success"),
            str(uuid.uuid4()),  # Refresh token
            False,  # Close modal
            "",  # Clear inputs
            "",
            "Weekly",
        )
    except Exception as e:
        logger.error(f"Error adding publisher: {e}")
        return (
            dmc.Alert(f"Error: {str(e)}", color="red", title="Error"),
            None,
            True,
            name or "",
            url or "",
            frequency or "Weekly",
        )
