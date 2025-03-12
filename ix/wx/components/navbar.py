import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State, dcc
from ix.wx.utils import get_user_from_token  # Your token utility

CSS_TEXT = """
<style>
/* Gradient Overlay */
.navbar-gradient {
    background: linear-gradient(135deg, #1a1a1a 0%, #000000 100%);
    border-bottom: 2px solid rgba(255, 255, 255, 0.1);
}

/* Improved Logo Styles */
.navbar-logo {
    transition: transform 0.3s ease-in-out, filter 0.3s ease;
}
.navbar-logo:hover {
    transform: scale(1.05);
    filter: drop-shadow(0 0 8px rgba(255, 255, 255, 0.3));
}

/* Enhanced Nav Links */
.nav-link-custom {
    color: #e0e0e0;
    position: relative;
    padding: 1rem 1.25rem;
    transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
.nav-link-custom:hover {
    color: #ffffff;
}
.nav-link-custom::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 50%;
    width: 0;
    height: 2px;
    background: linear-gradient(90deg, #00f2ff, #ff00ff);
    transition: all 0.3s ease;
}
.nav-link-custom:hover::after {
    width: 100%;
    left: 0;
}

/* Animated Sign In Button */
.signin-btn {
    border: 2px solid #ffffff;
    color: #ffffff;
    padding: 0.375rem 1.5rem;
    transition: all 0.3s ease-in-out;
}
.signin-btn:hover {
    background: linear-gradient(135deg, #00f2ff 0%, #ff00ff 100%);
    border-color: transparent;
    transform: translateY(-1px);
    box-shadow: 0 4px 15px rgba(0, 242, 255, 0.3);
}

/* Modern User Dropdown */
.user-dropdown-menu .dropdown-toggle {
    background: linear-gradient(135deg, #1a1a1a 0%, #000000 100%);
    border: 2px solid #ffffff;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
    transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
    min-width: 140px;
}
.user-dropdown-menu .dropdown-toggle:focus {
    box-shadow: 0 0 0 3px rgba(0, 242, 255, 0.5);
}

.user-dropdown-menu .dropdown-menu {
    background: linear-gradient(135deg, #1a1a1a 0%, #000000 100%);
    border: 2px solid #ffffff;
    border-radius: 8px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    transform: translateY(8px);
    transition: transform 0.3s ease-in-out, opacity 0.3s ease-in-out;
    opacity: 0;
    pointer-events: none;
}
.user-dropdown-menu.show .dropdown-menu {
    transform: translateY(0);
    opacity: 1;
    pointer-events: auto;
}

.user-dropdown-menu .dropdown-item {
    border-radius: 4px;
    margin: 4px 0;
    transition: all 0.3s ease;
}
.user-dropdown-menu .dropdown-item:hover {
    background: linear-gradient(135deg, #333333 0%, #262626 100%);
    transform: translateX(8px);
}

/* Mobile Improvements */
@media (max-width: 992px) {
    .navbar-collapse {
        background: linear-gradient(135deg, #1a1a1a 0%, #000000 100%);
        border-radius: 0 0 10px 10px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    }

    .navbar-toggler {
        border-color: #ffffff !important;
    }
    .navbar-toggler-icon {
        background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 30 30'%3e%3cpath stroke='rgba%28255, 255, 255, 0.8%29' stroke-linecap='round' stroke-miterlimit='10' stroke-width='2' d='M4 7h22M4 15h22M4 23h22'/%3e%3c/svg%3e") !important;
    }
}
</style>
"""

# Inject CSS
inline_styles = dcc.Markdown(CSS_TEXT, dangerously_allow_html=True)

# Navigation items
NAV_ITEMS = [
    {"name": "Dashboard", "href": "/"},
    {"name": "Macro", "href": "/macro"},
    {"name": "Insights", "href": "/insights"},
    {"name": "Views", "href": "/views"},
    {"name": "Strategies", "href": "/strategies"},
]


def create_nav_link(item):
    """Create enhanced navigation link"""
    return dbc.NavItem(
        dbc.NavLink(
            item["name"],
            href=item["href"],
            active="exact",
            className="nav-link-custom",
        )
    )


def create_navbar():
    """Create enhanced navbar component"""
    nav_links = [create_nav_link(item) for item in NAV_ITEMS]
    nav_links.append(
        html.Div(id="user-menu", className="d-flex align-items-center ms-2")
    )

    return dbc.Navbar(
        dbc.Container(
            [
                html.A(
                    dbc.Row(
                        [
                            dbc.Col(
                                html.Img(
                                    src="/assets/images/investment-x-logo-light.svg",
                                    height="30",
                                    className="navbar-logo",
                                    alt="Investment X Logo",
                                    style={
                                        "maxWidth": "280px",
                                        "width": "100%",
                                        "objectFit": "contain",
                                        "filter": "drop-shadow(0 2px 4px rgba(0, 0, 0, 0.3))",
                                    },
                                )
                            )
                        ],
                        align="center",
                        className="g-0 flex-nowrap",
                    ),
                    href="/",
                    style={"textDecoration": "none"},
                ),
                dbc.NavbarToggler(id="navbar-toggler", n_clicks=0, className="ms-2"),
                dbc.Collapse(
                    dbc.Nav(
                        nav_links,
                        className="ms-auto align-items-lg-center",
                        navbar=True,
                    ),
                    id="navbar-collapse",
                    is_open=False,
                    navbar=True,
                ),
            ],
            fluid=True,
            style={
                "maxWidth": "1680px",
                "margin": "0 auto",
                "padding": "0 1rem",
            },
        ),
        color="dark",
        dark=True,
        fixed="top",
        expand="lg",
        className="navbar-gradient",
        style={
            "padding": "0.75rem 0",
            "transition": "all 0.3s ease-in-out",
            "boxShadow": "0 2px 8px rgba(0, 0, 0, 0.3)",
        },
    )


navbar = create_navbar()


@callback(Output("user-menu", "children"), Input("token-store", "data"))
def update_user_menu(token_data):
    if not token_data:
        return dbc.Button(
            "Sign In",
            href="/signin",
            outline=True,
            className="signin-btn",
            style={"borderWidth": "2px"},
        )

    user = get_user_from_token(token_data)
    if not user:
        return dbc.Button(
            "Sign In",
            href="/signin",
            outline=True,
            className="signin-btn",
            style={"borderWidth": "2px"},
        )

    dropdown_items = [
        dbc.DropdownMenuItem("Profile", href="/profile"),
        dbc.DropdownMenuItem("Settings", href="/settings"),
        dbc.DropdownMenuItem(divider=True),
        dbc.DropdownMenuItem("Log Out", id="logout-btn"),
    ]

    if user.is_admin:
        dropdown_items.insert(
            0,
            dbc.DropdownMenuItem("Admin", href="/admin"),
        )

    return dbc.DropdownMenu(
        label=user.username,
        children=dropdown_items,
        nav=True,
        in_navbar=True,
        className="user-dropdown-menu",
        toggle_style={"padding": "0.375rem 1rem"},
    )


@callback(
    Output("navbar-collapse", "is_open"),
    Input("navbar-toggler", "n_clicks"),
    State("navbar-collapse", "is_open"),
)
def toggle_navbar(n_clicks, is_open):
    return not is_open if n_clicks else is_open


# Final layout
layout = html.Div([inline_styles, navbar])
