"""
Authentication middleware for protecting routes
"""

from dash import dcc, html, callback, Input, Output, State
from dash.exceptions import PreventUpdate
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from ix.misc import get_logger
from ix.misc.auth import get_current_user

logger = get_logger(__name__)

# Public routes that don't require authentication
PUBLIC_ROUTES = ["/login", "/register"]


def create_auth_callback(app):
    """
    Create authentication callback to protect routes

    This callback should be called after app initialization
    """

    @callback(
        Output("page-content", "children", allow_duplicate=True),
        [Input("url", "pathname"), Input("token-store", "data")],
        prevent_initial_call="initial_duplicate",
    )
    def check_authentication(pathname, token_data):
        """Check if user is authenticated before rendering page"""
        # Allow public routes
        if pathname in PUBLIC_ROUTES:
            raise PreventUpdate

        # Check if token exists
        if not token_data or not token_data.get("token"):
            # Redirect to login
            return html.Div(
                [
                    dcc.Location(id="auth-redirect", pathname="/login", refresh=True),
                    dmc.Center(
                        dmc.Stack(
                            [
                                dmc.ThemeIcon(
                                    DashIconify(icon="material-symbols:lock", width=50),
                                    size=80,
                                    radius="xl",
                                    variant="light",
                                    color="blue",
                                ),
                                dmc.Text(
                                    "Authentication required",
                                    size="xl",
                                    style={"textAlign": "center", "fontWeight": "500"},
                                ),
                                dmc.Text(
                                    "Redirecting to login...",
                                    c="gray",
                                    size="sm",
                                    style={"textAlign": "center"},
                                ),
                            ],
                            gap="md",
                            align="center",
                        ),
                        style={"minHeight": "100vh"},
                    ),
                ],
                style={"minHeight": "100vh", "backgroundColor": "var(--bg-primary)"},
            )

        # Verify token is still valid
        token = token_data.get("token")
        user = get_current_user(token)

        if not user:
            # Token is invalid or expired
            return html.Div(
                [
                    dcc.Location(id="auth-redirect", pathname="/login", refresh=True),
                    dmc.Center(
                        dmc.Stack(
                            [
                                dmc.ThemeIcon(
                                    DashIconify(
                                        icon="material-symbols:error", width=50
                                    ),
                                    size=80,
                                    radius="xl",
                                    variant="light",
                                    color="red",
                                ),
                                dmc.Text(
                                    "Session expired",
                                    size="xl",
                                    style={"textAlign": "center", "fontWeight": "500"},
                                ),
                                dmc.Text(
                                    "Please log in again",
                                    c="gray",
                                    size="sm",
                                    style={"textAlign": "center"},
                                ),
                            ],
                            gap="md",
                            align="center",
                        ),
                        style={"minHeight": "100vh"},
                    ),
                ],
                style={"minHeight": "100vh", "backgroundColor": "var(--bg-primary)"},
            )

        # User is authenticated, allow page to render
        raise PreventUpdate
