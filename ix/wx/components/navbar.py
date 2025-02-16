import dash_bootstrap_components as dbc
from dash import html, callback, Input, Output, State
from ix.wx.utils import get_user_from_token

# Constants for navigation items
NAV_ITEMS = [
    {"name": "Dashboard", "href": "/"},
    {"name": "Insights", "href": "/insights"},
    {"name": "Views", "href": "/views"},
    {"name": "Strategies", "href": "/strategies"},
]


def create_nav_link(item):
    """Create a navigation link using dbc.NavLink with inline styles."""
    return dbc.NavItem(
        dbc.NavLink(
            item["name"],
            href=item["href"],
            active="exact",
            className="mx-2 nav-link-custom",
            style={
                "color": "#FFFFFF",
                "borderBottom": "2px solid transparent",
                "transition": "border-bottom 0.3s ease-in-out",
                "paddingBottom": "3px",
            },
        )
    )


def create_navbar():
    """Construct a responsive, modern navbar with pure black background and white accents."""
    nav_links = [create_nav_link(item) for item in NAV_ITEMS]
    # Add a placeholder for the user menu
    nav_links.append(
        html.Div(id="user-menu", className="d-flex align-items-center ms-2")
    )

    return dbc.Navbar(
        dbc.Container(
            [
                html.A(
                    dbc.Row(
                        dbc.Col(
                            html.Img(
                                src="/assets/images/investment-x-logo-light.svg",
                                height="25px",
                                className="navbar-logo",
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
                dbc.NavbarToggler(id="navbar-toggler", n_clicks=0),
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
            # Set a maximum width for the entire navbar content and center it.
            style={
                "display": "flex",
                "alignItems": "center",
                "height": "60px",
                "maxWidth": "1680px",  # Adjust this value as needed
                "margin": "0 auto",
            },
        ),
        color="#000000",
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
            "minHeight": "60px",  # Ensure consistent navbar height
        },
    )


# Instantiate the navbar component
navbar = create_navbar()


# -----------------------------------------------------------------------------
# PART 2: User Menu Callback
# -----------------------------------------------------------------------------
@callback(Output("user-menu", "children"), Input("token-store", "data"))
def update_user_menu(token_data):
    """Update the user menu with inline styles ensuring dark dropdown styling."""
    if not token_data:
        return dbc.Button(
            "Sign In",
            href="/signin",
            color="light",
            outline=True,
            className="btn-sm",
            style={
                "borderColor": "#FFFFFF",
                "color": "#FFFFFF",
                "backgroundColor": "transparent",
                "transition": "background-color 0.3s ease-in-out",
            },
        )

    user = get_user_from_token(token_data)
    if user is None:
        return dbc.Button(
            "Sign In",
            href="/signin",
            color="light",
            outline=True,
            className="btn-sm",
            style={
                "borderColor": "#FFFFFF",
                "color": "#FFFFFF",
                "backgroundColor": "#000000",
                "transition": "background-color 0.3s ease-in-out",
            },
        )

    dropdown_toggle_style = {
        "width" : "100px",
        "color": "#FFFFFF",
        "backgroundColor": "#000000",
        "border": "1px solid #FFFFFF",
        "borderRadius": "4px",
        "padding": "0.25rem 0.5rem",
        "transition": "background-color 0.3s ease-in-out",
    }

    item_style = {"backgroundColor": "#000000", "color": "#FFFFFF"}

    dropdown_items = [
        dbc.DropdownMenuItem("Profile", href="/profile", style=item_style),
        dbc.DropdownMenuItem("Settings", href="/settings", style=item_style),
        dbc.DropdownMenuItem(divider=True, style=item_style),
        dbc.DropdownMenuItem("Log Out", href="/logout", style=item_style),
    ]

    if user.is_admin:
        dropdown_items.insert(
            0,
            dbc.DropdownMenuItem("Admin", href="/admin", style=item_style),
        )

    return dbc.DropdownMenu(
        label=user.username,
        children=dropdown_items,
        nav=True,
        in_navbar=True,
        toggle_style=dropdown_toggle_style,
    )


# -----------------------------------------------------------------------------
# PART 3: Navbar Collapse Callback
# -----------------------------------------------------------------------------
@callback(
    Output("navbar-collapse", "is_open"),
    Input("navbar-toggler", "n_clicks"),
    State("navbar-collapse", "is_open"),
)
def toggle_navbar_collapse(n_clicks, is_open):
    """Toggle the collapse on small screens."""
    return not is_open if n_clicks else is_open
