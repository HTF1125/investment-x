"""Callback to toggle upload zone visibility."""

from dash import callback, Input, Output, State
from dash.exceptions import PreventUpdate


@callback(
    Output("upload-zone-container", "style"),
    Output("toggle-upload-zone", "rightSection"),
    Input("toggle-upload-zone", "n_clicks"),
    State("upload-zone-container", "style"),
    prevent_initial_call=True,
)
def toggle_upload_zone(n_clicks, current_style):
    """Toggle upload zone visibility."""
    if not n_clicks:
        raise PreventUpdate

    # Determine current visibility state
    is_visible = current_style.get("display", "none") != "none"

    # Toggle visibility
    if is_visible:
        new_style = {
            "marginBottom": "24px",
            "flexShrink": 0,
            "display": "none",
        }
        icon = "carbon:chevron-down"
    else:
        new_style = {
            "marginBottom": "24px",
            "flexShrink": 0,
            "display": "block",
        }
        icon = "carbon:chevron-up"

    # Import DashIconify here to avoid circular imports
    from dash_iconify import DashIconify

    return new_style, DashIconify(icon=icon, width=16)
