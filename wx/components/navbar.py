import dash_bootstrap_components as dbc
from dash import html, callback, Input, Output, State

# Constants for navigation items
NAV_ITEMS = [
    {"name": "Dashboard", "href": "/"},
    {"name": "Insights", "href": "/insights"},
    {"name": "Views", "href": "/views"},
    {"name": "Strategies", "href": "/strategies"},
]


def create_nav_link(item):
    """Create a navigation link using dbc.NavLink."""
    return dbc.NavItem(
        dbc.NavLink(
            item["name"],
            href=item["href"],
            active="exact",
            className="mx-1 nav-link-custom",
        )
    )


def create_navbar():
    """Construct a responsive, modern, transparent navbar with reduced vertical padding."""
    # Build nav links from constants
    nav_links = [create_nav_link(item) for item in NAV_ITEMS]
    # Append a placeholder for the dynamic user menu/dropdown
    nav_links.append(html.Div(id="user-menu", className="d-flex align-items-center"))

    return dbc.Navbar(
        dbc.Container(
            [
                # Brand logo and name
                html.A(
                    dbc.Row(
                        dbc.Col(
                            html.Img(
                                src="/assets/images/investment-x-logo-light.svg",
                                height="20px",
                                className="navbar-logo",
                            )
                        ),
                        align="center",
                    ),
                    href="/",
                    className="navbar-brand",
                    style={"textDecoration": "none"},
                ),
                # Navbar toggler for mobile view
                dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
                # Collapsible nav links (including the user menu)
                dbc.Collapse(
                    dbc.Nav(
                        nav_links,
                        className="ms-auto",
                        navbar=True,
                    ),
                    id="navbar-collapse",
                    is_open=False,
                    navbar=True,
                ),
            ]
        ),
        color="#000000",  # Set the navbar to transparent
        dark=True,  # Keep text white for good contrast (adjust as needed)
        fixed="top",
        expand="lg",
        className="shadow-sm navbar-custom",  # Custom CSS class for further styling
        style={
            "paddingTop": "0.25rem",
            "paddingBottom": "0.25rem",
            "backgroundColor": "#000000",  # Transparent background
        },
    )


# Instantiate the navbar component
navbar = create_navbar()


# --- Authentication Logic & Callbacks ---
from jose import jwt, JWTError
from ix.misc.settings import Settings
from ix.db import User


def get_user_from_token(token_data: dict):
    """Decode the access token and retrieve the corresponding user."""
    if not token_data or "access_token" not in token_data:
        return None

    try:
        access_token = token_data["access_token"]
        payload = jwt.decode(
            access_token, Settings.secret_key, algorithms=[Settings.algorithm]
        )
        username = payload.get("sub")
        if not username:
            return None
        user = User.find_one(User.username == username).run()
        return user
    except JWTError:
        return None
    except Exception as e:
        print(f"Error decoding token: {e}")
        return None


@callback(Output("user-menu", "children"), Input("token-store", "data"))
def update_user_menu(token_data):
    """
    Update the user menu:
      - Show a "Sign In" button if no user is authenticated.
      - If authenticated, display a dropdown with user options.
    """
    if not token_data:
        return dbc.Button("Sign In", href="/signin", color="dark")

    user = get_user_from_token(token_data)
    if user is None:
        return dbc.Button("Sign In", href="/signin", color="dark")

    # If user is logged in, show a dropdown menu with additional options
    return dbc.DropdownMenu(
        label=user.username,
        children=[
            dbc.DropdownMenuItem("Profile", href="/profile"),
            dbc.DropdownMenuItem("Settings", href="/settings"),
            dbc.DropdownMenuItem(divider=True),
            dbc.DropdownMenuItem("Log Out", href="/logout"),
        ],
        nav=True,
        in_navbar=True,
        className="ms-1",
        menu_variant="dark",
        toggle_style={"color": "#fff"},
    )


@callback(
    Output("navbar-collapse", "is_open"),
    Input("navbar-toggler", "n_clicks"),
    State("navbar-collapse", "is_open"),
)
def toggle_navbar_collapse(n_clicks, is_open):
    """Toggle the collapse on small screens when the navbar toggler is clicked."""
    if n_clicks:
        return not is_open
    return is_open
