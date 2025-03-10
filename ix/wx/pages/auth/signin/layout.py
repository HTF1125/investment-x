import dash
from dash import html, dcc, callback, Input, Output, State, callback_context, no_update
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


# Function to verify passwords
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return crypt_context.verify(plain_password, hashed_password)


# Function to authenticate users
def authenticate_user(username: str, password: str):
    user = db.User.find_one(db.User.username == username).run()
    if not user or not verify_password(password, user.password):
        return None
    return user


# Function to create JWT token
def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=Settings.access_token_expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, Settings.secret_key, algorithm=Settings.algorithm)


# Layout of the Sign-In Page
layout = dbc.Container(
    fluid=True,
    style={
        "height": "100vh",
        "display": "flex",
        "justifyContent": "center",
        "alignItems": "center",
        "background": "linear-gradient(135deg, #2c3e50, #000000)",
    },
    children=[
        # Location for redirecting and a store for the token
        dcc.Location(id="signin-url", refresh=True),
        dcc.Store(id="token-store", storage_type="session"),
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.Div(
                                [
                                    html.Img(
                                        src="/assets/images/investment-x-logo-light.svg",
                                        style={
                                            "height": "15px",
                                            "marginBottom": "1rem",
                                        },
                                    ),
                                    html.H2(
                                        "Welcome Back",
                                        style={
                                            "fontWeight": "bold",
                                            "textAlign": "center",
                                            "marginBottom": "1.5rem",
                                            "color": "#ffffff",
                                        },
                                    ),
                                ],
                                style={"textAlign": "center"},
                            ),
                            dbc.Form(
                                [
                                    html.Div(
                                        [
                                            dbc.Label(
                                                "Username",
                                                html_for="username-input",
                                                style={"color": "#ffffff"},
                                            ),
                                            dbc.Input(
                                                type="text",
                                                id="username-input",
                                                placeholder="Enter your username",
                                                required=True,
                                                style={
                                                    "borderRadius": "0.5rem",
                                                    "backgroundColor": "#495057",
                                                    "color": "#ffffff",
                                                },
                                            ),
                                        ],
                                        style={"marginBottom": "1.5rem"},
                                    ),
                                    html.Div(
                                        [
                                            dbc.Label(
                                                "Password",
                                                html_for="password-input",
                                                style={"color": "#ffffff"},
                                            ),
                                            dbc.Input(
                                                type="password",
                                                id="password-input",
                                                placeholder="Enter your password",
                                                required=True,
                                                style={
                                                    "borderRadius": "0.5rem",
                                                    "backgroundColor": "#495057",
                                                    "color": "#ffffff",
                                                },
                                            ),
                                        ],
                                        style={"marginBottom": "1.5rem"},
                                    ),
                                    dbc.Button(
                                        "Sign In",
                                        id="signin-button",
                                        color="primary",
                                        n_clicks=0,
                                        style={
                                            "borderRadius": "0.5rem",
                                            "padding": "0.75rem",
                                            "width": "100%",
                                            "marginTop": "1rem",
                                        },
                                    ),
                                ]
                            ),
                            html.Div(
                                id="signin-output",
                                style={
                                    "color": "red",
                                    "textAlign": "center",
                                    "marginTop": "1rem",
                                },
                            ),
                            html.Div(
                                [
                                    html.Span(
                                        "Don't have an account? ",
                                        style={"color": "#ffffff"},
                                    ),
                                    html.A(
                                        "Sign Up",
                                        href="/signup",
                                        style={
                                            "textDecoration": "none",
                                            "fontWeight": "bold",
                                            "color": "#ffffff",
                                        },
                                    ),
                                ],
                                style={"textAlign": "center", "marginTop": "1rem"},
                            ),
                        ],
                        style={
                            "display": "flex",
                            "flexDirection": "column",
                            "justifyContent": "center",
                        },
                    ),
                    style={
                        "borderRadius": "1rem",
                        "maxWidth": "400px",
                        "width": "100%",
                        "minWidth": "350px",
                        "minHeight": "500px",
                        "boxShadow": "0 1rem 3rem rgba(0,0,0,0.175)",
                        "backgroundColor": "#343a40",
                        "color": "#ffffff",
                    },
                ),
                xs=12,
                sm=8,
                md=6,
                lg=4,
                xl=4,
            ),
        ),
    ],
)


# Callback to handle authentication
@callback(
    [
        Output("token-store", "data"),
        Output("signin-url", "href"),
        Output("signin-output", "children"),
    ],
    [Input("signin-button", "n_clicks")],
    [
        State("username-input", "value"),
        State("password-input", "value"),
        State("signin-url", "pathname"),
    ],
    prevent_initial_call=True,
)
def handle_signin(signin_clicks, username, password, current_pathname):
    """
    Handle sign-in:
      - Validate input fields.
      - Authenticate the user.
      - Generate and store an access token upon success.
      - Redirect to the dashboard if sign-in is successful.
      - Display an error message if authentication fails.
    """
    if signin_clicks is None or signin_clicks == 0:
        return no_update, no_update, no_update

    if not username or not password:
        return no_update, no_update, "Please enter both username and password."

    user = authenticate_user(username, password)
    if user:
        access_token = create_access_token(data={"sub": user.username})
        token_data = {"access_token": access_token, "token_type": "bearer"}
        redirect_path = "/" if current_pathname == "/signin" else current_pathname
        return token_data, redirect_path, ""
    else:
        return no_update, no_update, "Invalid username or password."
