"""
Login page for user authentication
"""

import dash
from dash import html, dcc, Input, Output, State, callback
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash.exceptions import PreventUpdate
from ix.misc import get_logger
from ix.misc.auth import authenticate_user, create_user_token

# Register page
dash.register_page(__name__, path="/login", title="Login", name="Login")

logger = get_logger(__name__)

# Login page layout
layout = html.Div(
    [
        dcc.Location(id="login-redirect", refresh=False),
        dmc.Container(
            [
                dmc.Paper(
                    [
                        # Logo and header
                        dmc.Center(
                            [
                                dmc.Stack(
                                    [
                                        dmc.ThemeIcon(
                                            DashIconify(
                                                icon="material-symbols:lock", width=50
                                            ),
                                            size=80,
                                            radius="xl",
                                            variant="light",
                                            color="blue",
                                        ),
                                        dmc.Title(
                                            "Welcome Back",
                                            order=2,
                                            style={
                                                "textAlign": "center",
                                                "marginTop": "16px",
                                            },
                                        ),
                                        dmc.Text(
                                            "Sign in to your account",
                                            c="dimmed",
                                            size="sm",
                                            style={"textAlign": "center"},
                                        ),
                                    ],
                                    gap="xs",
                                    align="center",
                                )
                            ],
                            style={"marginBottom": "24px"},
                        ),
                        # Login form
                        dmc.Stack(
                            [
                                dmc.TextInput(
                                    id="login-username",
                                    label="Username",
                                    placeholder="Enter your username",
                                    leftSection=DashIconify(
                                        icon="material-symbols:person"
                                    ),
                                    size="md",
                                    required=True,
                                ),
                                dmc.PasswordInput(
                                    id="login-password",
                                    label="Password",
                                    placeholder="Enter your password",
                                    leftSection=DashIconify(
                                        icon="material-symbols:lock"
                                    ),
                                    size="md",
                                    required=True,
                                ),
                                html.Div(id="login-error", style={"marginTop": "8px"}),
                                dmc.Button(
                                    "Sign In",
                                    id="login-submit",
                                    fullWidth=True,
                                    size="md",
                                    variant="filled",
                                    color="blue",
                                    leftSection=DashIconify(
                                        icon="material-symbols:login"
                                    ),
                                    style={"marginTop": "16px"},
                                ),
                                dmc.Divider(
                                    label="OR", labelPosition="center", my="md"
                                ),
                                dmc.Button(
                                    "Create an account",
                                    id="goto-register",
                                    fullWidth=True,
                                    size="md",
                                    variant="outline",
                                    color="gray",
                                    leftSection=DashIconify(
                                        icon="material-symbols:person-add"
                                    ),
                                ),
                            ],
                            gap="md",
                        ),
                    ],
                    p="xl",
                    radius="lg",
                    shadow="xl",
                    style={
                        "maxWidth": "450px",
                        "width": "100%",
                        "backgroundColor": "var(--bg-secondary)",
                    },
                ),
            ],
            size="xs",
            px="md",
            style={
                "minHeight": "100vh",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                "paddingTop": "20px",
                "paddingBottom": "20px",
            },
        ),
    ],
    style={
        "minHeight": "100vh",
        "backgroundColor": "var(--bg-primary)",
    },
)


# Login callback
@callback(
    [
        Output("token-store", "data", allow_duplicate=True),
        Output("login-error", "children"),
        Output("login-redirect", "pathname"),
    ],
    Input("login-submit", "n_clicks"),
    [
        State("login-username", "value"),
        State("login-password", "value"),
    ],
    prevent_initial_call=True,
)
def handle_login(n_clicks, username, password):
    """Handle user login"""
    if not n_clicks:
        raise PreventUpdate

    # Normalize inputs
    username = (username or "").strip()
    password = password or ""

    # Validate inputs
    if not username or not password:
        error_message = dmc.Alert(
            "Please enter both username and password",
            title="Error",
            color="red",
            icon=DashIconify(icon="material-symbols:error"),
        )
        return None, error_message, dash.no_update

    try:
        # Authenticate user
        user = authenticate_user(username, password)

        if not user:
            error_message = dmc.Alert(
                "Invalid username or password",
                title="Authentication Failed",
                color="red",
                icon=DashIconify(icon="material-symbols:error"),
            )
            return None, error_message, dash.no_update

        # Create token
        token = create_user_token(user.username, user.is_admin)

        # Store token and redirect
        token_data = {
            "token": token,
            "username": user.username,
            "is_admin": user.is_admin,
        }

        logger.info(f"User {username} logged in successfully")

        return token_data, "", "/"

    except Exception as e:
        logger.error(f"Login error: {e}")
        error_message = dmc.Alert(
            f"An error occurred: {str(e)}",
            title="Error",
            color="red",
            icon=DashIconify(icon="material-symbols:error"),
        )
        return None, error_message, dash.no_update


# Navigate to registration
@callback(
    Output("login-redirect", "pathname", allow_duplicate=True),
    Input("goto-register", "n_clicks"),
    prevent_initial_call=True,
)
def goto_register(n_clicks):
    """Navigate to registration page"""
    if not n_clicks:
        raise PreventUpdate
    return "/register"
