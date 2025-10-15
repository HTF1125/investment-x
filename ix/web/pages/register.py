"""
Registration page for new user sign up
"""

import dash
from dash import html, dcc, Input, Output, State, callback
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash.exceptions import PreventUpdate
from ix.misc import get_logger
from ix.db.models import User

# Register page
dash.register_page(__name__, path="/register", title="Register", name="Register")

logger = get_logger(__name__)

# Registration page layout
layout = html.Div(
    [
        dcc.Location(id="register-redirect", refresh=True),
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
                                                icon="material-symbols:person-add",
                                                width=50,
                                            ),
                                            size=80,
                                            radius="xl",
                                            variant="light",
                                            color="blue",
                                        ),
                                        dmc.Title(
                                            "Create Account",
                                            order=2,
                                            style={
                                                "textAlign": "center",
                                                "marginTop": "16px",
                                            },
                                        ),
                                        dmc.Text(
                                            "Sign up to get started",
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
                        # Registration form
                        dmc.Stack(
                            [
                                dmc.TextInput(
                                    id="register-username",
                                    label="Username",
                                    placeholder="Choose a username",
                                    leftSection=DashIconify(
                                        icon="material-symbols:person"
                                    ),
                                    size="md",
                                    required=True,
                                ),
                                dmc.TextInput(
                                    id="register-email",
                                    label="Email",
                                    placeholder="Enter your email",
                                    leftSection=DashIconify(
                                        icon="material-symbols:mail"
                                    ),
                                    size="md",
                                ),
                                dmc.PasswordInput(
                                    id="register-password",
                                    label="Password",
                                    placeholder="Choose a password",
                                    leftSection=DashIconify(
                                        icon="material-symbols:lock"
                                    ),
                                    size="md",
                                    required=True,
                                ),
                                dmc.PasswordInput(
                                    id="register-password-confirm",
                                    label="Confirm Password",
                                    placeholder="Confirm your password",
                                    leftSection=DashIconify(
                                        icon="material-symbols:lock"
                                    ),
                                    size="md",
                                    required=True,
                                ),
                                html.Div(
                                    id="register-message", style={"marginTop": "8px"}
                                ),
                                dmc.Button(
                                    "Create Account",
                                    id="register-submit",
                                    fullWidth=True,
                                    size="md",
                                    variant="filled",
                                    color="blue",
                                    leftSection=DashIconify(
                                        icon="material-symbols:person-add"
                                    ),
                                    style={"marginTop": "16px"},
                                ),
                                dmc.Divider(
                                    label="OR", labelPosition="center", my="md"
                                ),
                                dmc.Button(
                                    "Already have an account? Sign in",
                                    id="goto-login",
                                    fullWidth=True,
                                    size="md",
                                    variant="outline",
                                    color="gray",
                                    leftSection=DashIconify(
                                        icon="material-symbols:login"
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


# Registration callback
@callback(
    [
        Output("register-message", "children"),
        Output("register-redirect", "pathname"),
    ],
    Input("register-submit", "n_clicks"),
    [
        State("register-username", "value"),
        State("register-email", "value"),
        State("register-password", "value"),
        State("register-password-confirm", "value"),
    ],
    prevent_initial_call=True,
)
def handle_registration(n_clicks, username, email, password, password_confirm):
    """Handle user registration"""
    if not n_clicks:
        raise PreventUpdate

    # Validate inputs
    if not username or not password:
        error_message = dmc.Alert(
            "Username and password are required",
            title="Error",
            color="red",
            icon=DashIconify(icon="material-symbols:error"),
        )
        return error_message, dash.no_update

    if len(username) < 3:
        error_message = dmc.Alert(
            "Username must be at least 3 characters long",
            title="Error",
            color="red",
            icon=DashIconify(icon="material-symbols:error"),
        )
        return error_message, dash.no_update

    if len(password) < 6:
        error_message = dmc.Alert(
            "Password must be at least 6 characters long",
            title="Error",
            color="red",
            icon=DashIconify(icon="material-symbols:error"),
        )
        return error_message, dash.no_update

    if password != password_confirm:
        error_message = dmc.Alert(
            "Passwords do not match",
            title="Error",
            color="red",
            icon=DashIconify(icon="material-symbols:error"),
        )
        return error_message, dash.no_update

    try:
        # Check if user already exists
        if User.exists(username):
            error_message = dmc.Alert(
                "Username already exists",
                title="Error",
                color="red",
                icon=DashIconify(icon="material-symbols:error"),
            )
            return error_message, dash.no_update

        # Create new user
        User.new_user(username=username, password=password, email=email)

        logger.info(f"New user registered: {username}")

        success_message = dmc.Alert(
            "Account created successfully! Redirecting to login...",
            title="Success",
            color="green",
            icon=DashIconify(icon="material-symbols:check-circle"),
        )

        return success_message, "/login"

    except Exception as e:
        logger.error(f"Registration error: {e}")
        error_message = dmc.Alert(
            f"An error occurred: {str(e)}",
            title="Error",
            color="red",
            icon=DashIconify(icon="material-symbols:error"),
        )
        return error_message, dash.no_update


# Navigate to login
@callback(
    Output("register-redirect", "pathname", allow_duplicate=True),
    Input("goto-login", "n_clicks"),
    prevent_initial_call=True,
)
def goto_login(n_clicks):
    """Navigate to login page"""
    if not n_clicks:
        raise PreventUpdate
    return "/login"
