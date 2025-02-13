import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext
from ix import db
from ix.misc.settings import Settings

# Register the page
dash.register_page(__name__, path="/signin", title="Sign In", name="Sign In")

# Initialize password hashing context
crypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify that the provided password matches the stored hash."""
    return crypt_context.verify(plain_password, hashed_password)

def authenticate_user(username: str, password: str):
    """Fetch the user and verify credentials."""
    user = db.User.find_one(db.User.username == username).run()
    if not user or not verify_password(password, user.password):
        return None
    return user

def create_access_token(data: dict) -> str:
    """Create a JWT access token with an expiration time."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=Settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, Settings.secret_key, algorithm=Settings.algorithm)

# Revised layout with full viewport height, enhanced design, and a taller login card
layout = dbc.Container(
    fluid=True,
    style={
        "height": "100vh",
        "display": "flex",
        "justifyContent": "center",
        "alignItems": "center",
        "background": "linear-gradient(135deg, #71b7e6, #9b59b6)",
    },
    children=[
        # Location for redirecting and a hidden store for the token
        dcc.Location(id="signin-url", refresh=True),
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.Div(
                                [
                                    # Optional logo; replace with your logo path if needed
                                    html.Img(src="/assets/images/investment-x-logo-dark.svg", height="15px", className="mb-3"),
                                    html.H2("Welcome Back", className="text-center mb-4", style={"fontWeight": "bold"}),
                                ],
                                className="text-center"
                            ),
                            dbc.Form(
                                [
                                    html.Div(
                                        [
                                            dbc.Label("Username", html_for="username-input"),
                                            dbc.Input(
                                                type="text",
                                                id="username-input",
                                                placeholder="Enter your username",
                                                required=True,
                                                style={"borderRadius": "0.5rem"},
                                            ),
                                        ],
                                        className="mb-3"
                                    ),
                                    html.Div(
                                        [
                                            dbc.Label("Password", html_for="password-input"),
                                            dbc.Input(
                                                type="password",
                                                id="password-input",
                                                placeholder="Enter your password",
                                                required=True,
                                                style={"borderRadius": "0.5rem"},
                                            ),
                                        ],
                                        className="mb-3"
                                    ),
                                    dbc.Button(
                                        "Sign In",
                                        id="signin-button",
                                        color="primary",
                                        className="w-100 mt-3",
                                        n_clicks=0,
                                        style={"borderRadius": "0.5rem", "padding": "0.75rem"},
                                    ),
                                ]
                            ),
                            html.Div(
                                id="signin-output",
                                className="text-center mt-3",
                                style={"color": "red"},
                            ),
                            html.Div(
                                [
                                    html.Span("Don't have an account? "),
                                    html.A("Sign Up", href="/signup", style={"textDecoration": "none", "fontWeight": "bold"}),
                                ],
                                className="text-center mt-3",
                            ),
                        ],
                        # Center the card content vertically
                        style={
                            "display": "flex",
                            "flexDirection": "column",
                            "justifyContent": "center",
                            "height": "100%",
                        }
                    ),
                    className="shadow-lg",
                    style={
                        "borderRadius": "1rem",
                        "maxWidth": "400px",
                        "width": "100%",
                        "minWidth": "350px",
                        "minHeight": "500px"  # Increases the card height
                    },
                ),
                xs=12, sm=8, md=6, lg=4, xl=4,
            ),
        ),
    ],
)

@callback(
    [
        Output("token-store", "data"),
        Output("signin-url", "href"),
        Output("signin-output", "children"),
    ],
    Input("signin-button", "n_clicks"),
    [
        State("username-input", "value"),
        State("password-input", "value"),
        State("signin-url", "pathname"),
        State("token-store", "data"),
    ],
    prevent_initial_call=True,
)
def handle_signin(n_clicks, username, password, current_pathname, token):
    """
    Handle sign-in button clicks:
      - Validate input fields.
      - Authenticate the user.
      - Generate and store an access token upon success.
      - Redirect to the dashboard if sign-in is successful.
      - Display an error message if authentication fails.
    """
    if n_clicks is None or n_clicks == 0:
        return dash.no_update, dash.no_update, dash.no_update

    if not username or not password:
        return dash.no_update, dash.no_update, "Please enter both username and password."

    user = authenticate_user(username, password)
    if user:
        access_token = create_access_token(data={"sub": user.username})
        token_data = {"access_token": access_token, "token_type": "bearer"}
        redirect_path = "/" if current_pathname == "/signin" else current_pathname
        return token_data, redirect_path, ""
    else:
        return dash.no_update, dash.no_update, "Invalid username or password."
