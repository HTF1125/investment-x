import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State
from ix.wx.utils import (
    get_user_from_token,
)  # Your utility for extracting user info from token.

# Updated inline CSS definitions wrapped in a <style> tag.
css_text = """
<style>
/* Navbar Links */
.nav-link-custom {
    color: var(--bs-light);
    border-bottom: 2px solid transparent;
    transition: border-bottom 0.3s ease-in-out;
    padding-bottom: 3px;
}
.nav-link-custom:hover {
    border-bottom: 2px solid var(--bs-light);
}

/* Sign In Button */
.signin-btn {
    border-color: #FFFFFF;
    color: #FFFFFF;
    background-color: transparent;
    transition: background-color 0.3s ease-in-out;
}

/* User Dropdown Toggle */
.user-dropdown-menu .dropdown-toggle {
    min-width: 120px;
    color: #FFFFFF;
    background-color: #000000;
    border: 1px solid #FFFFFF;
    border-radius: 4px;
    padding: 0.25rem 0.75rem;
    transition: background-color 0.3s ease-in-out;
}

/* Override default dropdown menu styles */
.user-dropdown-menu .dropdown-menu {
    background-color: #000000 !important;
    border: 1px solid #FFFFFF;
    margin-top: 0.5rem;
    opacity: 1 !important;
    transform: none !important;
    box-shadow: none !important;
}

/* User Dropdown Items */
.user-dropdown-menu .dropdown-item {
    background-color: #000000;
    color: #FFFFFF;
}
.user-dropdown-menu .dropdown-item:hover {
    background-color: #333333;
    color: #FFFFFF;
}
</style>
"""

# Inject the CSS into the layout using a Markdown component with raw HTML enabled.
inline_styles = dcc.Markdown(css_text, dangerously_allow_html=True)

# Navigation items for the navbar.
NAV_ITEMS = [
    {"name": "Dashboard", "href": "/"},
    {"name": "Insights", "href": "/insights"},
    {"name": "Views", "href": "/views"},
    {"name": "Strategies", "href": "/strategies"},
]


def create_nav_link(item):
    """Create a navigation link using dbc.NavLink with our custom CSS class."""
    return dbc.NavItem(
        dbc.NavLink(
            item["name"],
            href=item["href"],
            active="exact",
            className="mx-2 nav-link-custom",
        )
    )


def create_navbar():
    """Construct a responsive, production-ready navbar with logo, links, and a user menu placeholder."""
    # Build the nav links.
    nav_links = [create_nav_link(item) for item in NAV_ITEMS]
    # Append a container for the user menu.
    nav_links.append(
        html.Div(id="user-menu", className="d-flex align-items-center ms-2")
    )

    return dbc.Navbar(
        dbc.Container(
            [
                # Logo and branding area.
                html.A(
                    dbc.Row(
                        dbc.Col(
                            html.Img(
                                src="/assets/images/investment-x-logo-light.svg",
                                height="30",
                                className="navbar-logo",
                                alt="Investment X Logo",
                                style={
                                    "maxWidth": "300px",
                                    "width": "100%",
                                    "objectFit": "contain",
                                },
                            )
                        ),
                        align="center",
                        className="g-0",
                    ),
                    href="/",
                    style={"textDecoration": "none"},
                ),
                # Navbar toggler for mobile view.
                dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
                # Collapsible area for navigation links and user menu.
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
            ],
            fluid=True,
            style={
                "display": "flex",
                "alignItems": "center",
                "height": "60px",
                "maxWidth": "1680px",
                "margin": "0 auto",
            },
        ),
        color="dark",
        dark=True,
        fixed="top",
        expand="lg",
        style={
            "paddingTop": "0.5rem",
            "paddingBottom": "0.5rem",
            "backgroundColor": "#000000",
            "boxShadow": "0 2px 4px rgba(255, 255, 255, 0.1)",
            "borderBottom": "1px solid #FFFFFF",
            "transition": "background-color 0.3s ease-in-out",
            "minHeight": "60px",
        },
    )


# Instantiate the navbar component.
navbar = create_navbar()


# Callback to update the user menu based on token data.
@callback(Output("user-menu", "children"), Input("token-store", "data"))
def update_user_menu(token_data):
    """
    If no token is provided or the token is invalid, display a "Sign In" button.
    Otherwise, display a dropdown with Profile, Settings, and Log Out options.
    """
    if not token_data:
        return dbc.Button(
            "Sign In",
            href="/signin",
            color="light",
            outline=True,
            size="sm",
            className="signin-btn",
        )
    user = get_user_from_token(token_data)
    if user is None:
        return dbc.Button(
            "Sign In",
            href="/signin",
            color="light",
            outline=True,
            size="sm",
            className="signin-btn",
        )
    # Define dropdown items.
    dropdown_items = [
        dbc.DropdownMenuItem("Profile", href="/profile", className="dropdown-item"),
        dbc.DropdownMenuItem("Settings", href="/settings", className="dropdown-item"),
        dbc.DropdownMenuItem(divider=True),
        dbc.DropdownMenuItem("Log Out", id="logout-btn", className="dropdown-item"),

    ]
    if user.is_admin:
        dropdown_items.insert(
            0,
            dbc.DropdownMenuItem("Admin", href="/admin", className="dropdown-item"),
        )
    return dbc.DropdownMenu(
        label=user.username,
        children=dropdown_items,
        nav=True,
        in_navbar=True,
        toggle_style={},  # Styling is handled via CSS.
        className="user-dropdown-menu",
    )


# Callback to handle the navbar collapse on mobile devices.
@callback(
    Output("navbar-collapse", "is_open"),
    Input("navbar-toggler", "n_clicks"),
    State("navbar-collapse", "is_open"),
)
def toggle_navbar_collapse(n_clicks, is_open):
    """Toggle the collapse state of the navbar."""
    return not is_open if n_clicks else is_open


# Define the overall layout, including the inline CSS and the navbar.
layout = html.Div([inline_styles, navbar])
