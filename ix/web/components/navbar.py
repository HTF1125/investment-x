from dash import html, dcc, callback, Input, Output, State, clientside_callback, ctx
import json
from dash_iconify import DashIconify
import dash_mantine_components as dmc

# Navigation items
NAV_ITEMS = [
    {"name": "Dashboard", "href": "/", "icon": "fa6-solid:chart-line"},
    {"name": "Macro", "href": "/macro", "icon": "fa6-solid:globe"},
    {"name": "Insights", "href": "/insights", "icon": "fa6-solid:lightbulb"},
    {"name": "Strategies", "href": "/strategies", "icon": "fa6-solid:bolt"},
    {"name": "Data", "href": "/data", "icon": "fa6-solid:database"},
    {"name": "Risk", "href": "/risk", "icon": "fa6-solid:shield-halved"},
]


def create_nav_link(item, is_mobile=False):
    """Create navigation link using DashIconify"""
    base_style = {
        "display": "flex",
        "alignItems": "center",
        "padding": "12px 16px" if is_mobile else "8px 16px",
        "margin": "3px 0" if is_mobile else "0 4px",
        "borderRadius": "6px" if is_mobile else "8px",
        "color": "#b8b8b8",
        "textDecoration": "none",
        "fontSize": "16px" if is_mobile else "14px",
        "fontWeight": "500",
        "transition": "all 0.3s ease",
        "justifyContent": "center" if is_mobile else "flex-start",
        "textAlign": "center" if is_mobile else "left",
    }

    return dcc.Link(
        [
            DashIconify(
                icon=item["icon"], width=16, height=16, style={"color": "inherit"}
            ),
            html.Span(item["name"], style={"marginLeft": "8px"}),
        ],
        href=item["href"],
        id=f"nav-link-{item['name'].lower()}-{'mobile' if is_mobile else 'desktop'}",
        className="nav-link",
        style=base_style,
        refresh=False,
    )


def create_action_button(icon, button_id, title=None, is_mobile=False):
    """Create action button (notification, theme switch) using DashIconify"""
    # icon: either a DashIconify icon string or a tuple (icon, alt_icon) for toggle
    iconify_props = {
        "width": 18,
        "height": 18,
        "style": {"color": "inherit"},
    }
    if isinstance(icon, str):
        icon_component = DashIconify(icon=icon, **iconify_props)
    else:
        # fallback, should not happen
        icon_component = DashIconify(icon=icon[0], **iconify_props)

    return html.Button(
        icon_component,
        id=button_id,
        className="action-button",
        title=title,
        style={
            "backgroundColor": "transparent",
            "border": "none",
            "color": "#b8b8b8",
            "padding": "6px" if is_mobile else "8px",
            "borderRadius": "50%" if "toggle" not in button_id else "4px",
            "cursor": "pointer",
            "transition": "all 0.3s ease",
            "display": "none" if button_id == "mobile-menu-toggle" else "block",
        },
    )


def create_mobile_menu():
    """Create mobile menu overlay"""
    return html.Div(
        [
            html.Div(
                [create_nav_link(item, is_mobile=True) for item in NAV_ITEMS],
                style={
                    "display": "flex",
                    "flexDirection": "column",
                    "gap": "8px",
                    "marginBottom": "20px",
                },
            ),
            html.Div(
                [
                    create_action_button(
                        "fa6-solid:bell", "notification-bell-mobile", is_mobile=True
                    ),
                    create_action_button(
                        "fa6-solid:moon",
                        "theme-switch-mobile",
                        "Toggle theme",
                        is_mobile=True,
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "gap": "16px",
                },
            ),
        ],
        id="mobile-menu",
        style={
            "position": "fixed",
            "top": "var(--navbar-height, 70px)",  # Use CSS variable for dynamic height
            "left": 0,
            "right": 0,
            "backgroundColor": "rgba(15, 15, 15, 0.98)",
            "backdropFilter": "blur(20px)",
            "padding": "20px",
            "borderBottom": "1px solid rgba(255, 255, 255, 0.1)",
            "transform": "translateY(-100%)",
            "transition": "transform 0.3s ease",
            "zIndex": 999,
            "display": "none",
            "boxShadow": "0 8px 32px rgba(0, 0, 0, 0.4)",
        },
    )


def create_navbar():
    """Create responsive navbar"""
    return html.Div(
        [
            html.Nav(
                html.Div(
                    [
                        # Logo
                        dcc.Link(
                            html.Img(
                                id="navbar-logo",
                                src="/assets/images/investment-x-logo-light.svg",
                                alt="Investment X Logo",
                                style={
                                    "height": "28px",
                                    "transition": "all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94)",
                                    "filter": "drop-shadow(0 0 10px rgba(255, 255, 255, 0.1))",
                                },
                            ),
                            href="/",
                            style={"textDecoration": "none"},
                            refresh=False,
                        ),
                        # Desktop navigation
                        html.Div(
                            [create_nav_link(item) for item in NAV_ITEMS],
                            id="desktop-nav-links",
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "gap": "4px",
                            },
                        ),
                        # Desktop actions
                        html.Div(
                            [
                                create_action_button(
                                    "fa6-solid:bell", "notification-bell-desktop"
                                ),
                                create_action_button(
                                    "fa6-solid:moon",
                                    "theme-switch-desktop",
                                    "Toggle theme",
                                ),
                                html.Div(id="user-menu-container"),
                            ],
                            id="desktop-nav-actions",
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "gap": "8px",
                            },
                        ),
                        # Mobile menu toggle
                        create_action_button("fa6-solid:bars", "mobile-menu-toggle"),
                    ],
                    id="navbar-container",
                    style={
                        "display": "flex",
                        "justifyContent": "space-between",
                        "alignItems": "center",
                        "padding": "0 20px",
                        "height": "70px",
                        "maxWidth": "1680px",
                        "margin": "0 auto",
                    },
                ),
                id="main-navbar",
                style={
                    "backgroundColor": "rgba(15, 15, 15, 0.95)",
                    "backdropFilter": "blur(20px)",
                    "borderBottom": "1px solid rgba(255, 255, 255, 0.1)",
                    "boxShadow": "0 8px 32px rgba(0, 0, 0, 0.3)",
                    "position": "fixed",
                    "top": 0,
                    "left": 0,
                    "right": 0,
                    "zIndex": 1000,
                    "height": "70px",
                },
            ),
            create_mobile_menu(),
        ]
    )


# Create navbar instance
navbar = create_navbar()
layout = html.Div([navbar])


# Callbacks
@callback(
    [
        Output("notification-bell-desktop", "children"),
        Output("notification-bell-mobile", "children"),
    ],
    [
        Input("notification-bell-desktop", "n_clicks"),
        Input("notification-bell-mobile", "n_clicks"),
    ],
    prevent_initial_call=True,
)
def handle_notifications(desktop_clicks, mobile_clicks):
    bell_icon = DashIconify(
        icon="fa6-solid:bell", width=18, height=18, style={"color": "inherit"}
    )
    return bell_icon, bell_icon


@callback(
    [
        Output("navbar-logo", "src"),
        Output("theme-switch-desktop", "children"),
        Output("theme-switch-mobile", "children"),
    ],
    [
        Input("theme-switch-desktop", "n_clicks"),
        Input("theme-switch-mobile", "n_clicks"),
    ],
    [State("navbar-logo", "src")],
    prevent_initial_call=True,
)
def handle_theme_switch(desktop_clicks, mobile_clicks, current_logo_src):
    if not (desktop_clicks or mobile_clicks):
        moon_icon = DashIconify(
            icon="fa6-solid:moon", width=18, height=18, style={"color": "inherit"}
        )
        return current_logo_src, moon_icon, moon_icon

    is_currently_light = "light" in current_logo_src

    if is_currently_light:
        new_logo_src = "/assets/images/investment-x-logo-dark.svg"
        new_icon = DashIconify(
            icon="fa6-solid:sun", width=18, height=18, style={"color": "inherit"}
        )
    else:
        new_logo_src = "/assets/images/investment-x-logo-light.svg"
        new_icon = DashIconify(
            icon="fa6-solid:moon", width=18, height=18, style={"color": "inherit"}
        )

    return new_logo_src, new_icon, new_icon


# Hover effects and responsive behavior
clientside_callback(
    """
    function() {
        // Add hover effects for nav links
        document.addEventListener('DOMContentLoaded', function() {
            const navLinks = document.querySelectorAll('.nav-link');
            navLinks.forEach(link => {
                link.addEventListener('mouseenter', function() {
                    this.style.backgroundColor = 'rgba(255, 255, 255, 0.05)';
                    this.style.color = '#ffffff';
                    this.style.transform = 'translateY(-1px)';
                    // Also color iconify icon
                    const icon = this.querySelector('span.dash-iconify');
                    if (icon) icon.style.color = '#ffffff';
                });
                link.addEventListener('mouseleave', function() {
                    this.style.backgroundColor = 'transparent';
                    this.style.color = '#b8b8b8';
                    this.style.transform = 'translateY(0)';
                    // Also color iconify icon
                    const icon = this.querySelector('span.dash-iconify');
                    if (icon) icon.style.color = 'inherit';
                });
            });

            // Add hover effects for action buttons
            const buttons = document.querySelectorAll('.action-button');
            buttons.forEach(button => {
                button.addEventListener('mouseenter', function() {
                    this.style.color = '#3b82f6';
                    this.style.backgroundColor = 'rgba(59, 130, 246, 0.1)';
                });
                button.addEventListener('mouseleave', function() {
                    this.style.color = '#b8b8b8';
                    this.style.backgroundColor = 'transparent';
                });
            });

            // Add hover effect for logo
            const logo = document.getElementById('navbar-logo');
            if (logo) {
                logo.addEventListener('mouseenter', function() {
                    this.style.transform = 'scale(1.05)';
                    this.style.filter = 'drop-shadow(0 0 15px rgba(59, 130, 246, 0.3))';
                });
                logo.addEventListener('mouseleave', function() {
                    this.style.transform = 'scale(1)';
                    this.style.filter = 'drop-shadow(0 0 10px rgba(255, 255, 255, 0.1))';
                });
            }
        });

        return window.dash_clientside.no_update;
    }
    """,
    Output("navbar-container", "title"),
    Input("navbar-container", "id"),
)


# Mobile menu toggle
clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks) {
            const mobileMenu = document.getElementById('mobile-menu');
            const toggleBtn = document.getElementById('mobile-menu-toggle');

            if (mobileMenu && toggleBtn) {
                const isVisible = mobileMenu.style.display === 'block';
                const icon = toggleBtn.querySelector('i');

                if (isVisible) {
                    mobileMenu.style.display = 'none';
                    mobileMenu.style.transform = 'translateY(-100%)';
                    if (icon) icon.className = 'fas fa-bars';
                } else {
                    mobileMenu.style.display = 'block';
                    mobileMenu.style.transform = 'translateY(0)';
                    if (icon) icon.className = 'fas fa-times';
                }
            }
        }
        return window.dash_clientside.no_update;
    }
    """,
    Output("mobile-menu-toggle", "title"),
    Input("mobile-menu-toggle", "n_clicks"),
    prevent_initial_call=True,
)


# Responsive behavior with CSS variable updates
clientside_callback(
    """
    function() {
        function updateNavbarForScreenSize() {
            const navbar = document.getElementById('main-navbar');
            const container = document.getElementById('navbar-container');
            const logo = document.getElementById('navbar-logo');
            const desktopNavLinks = document.getElementById('desktop-nav-links');
            const desktopNavActions = document.getElementById('desktop-nav-actions');
            const mobileToggle = document.getElementById('mobile-menu-toggle');
            const mobileMenu = document.getElementById('mobile-menu');

            if (!navbar || !container) return;

            const width = window.innerWidth;
            let navbarHeight;

            if (width < 768) {
                // Mobile
                navbarHeight = '55px';
                navbar.style.height = navbarHeight;
                container.style.height = navbarHeight;
                container.style.padding = '0 16px';
                if (logo) logo.style.height = '20px';
                if (desktopNavLinks) desktopNavLinks.style.display = 'none';
                if (desktopNavActions) desktopNavActions.style.display = 'none';
                if (mobileToggle) mobileToggle.style.display = 'block';
                if (mobileMenu) mobileMenu.style.top = navbarHeight;
            } else if (width < 1024) {
                // Tablet
                navbarHeight = '65px';
                navbar.style.height = navbarHeight;
                container.style.height = navbarHeight;
                container.style.padding = '0 20px';
                if (logo) logo.style.height = '24px';
                if (desktopNavLinks) {
                    desktopNavLinks.style.display = 'flex';
                    desktopNavLinks.style.gap = '2px';
                    // Hide text on tablet, show only icons
                    const navLinks = desktopNavLinks.querySelectorAll('.nav-link span');
                    navLinks.forEach(span => span.style.display = 'none');
                }
                if (desktopNavActions) {
                    desktopNavActions.style.display = 'flex';
                    desktopNavActions.style.gap = '6px';
                }
                if (mobileToggle) mobileToggle.style.display = 'none';
                if (mobileMenu) mobileMenu.style.top = navbarHeight;
            } else {
                // Desktop
                navbarHeight = '70px';
                navbar.style.height = navbarHeight;
                container.style.height = navbarHeight;
                container.style.padding = '0 20px';
                if (logo) logo.style.height = '28px';
                if (desktopNavLinks) {
                    desktopNavLinks.style.display = 'flex';
                    desktopNavLinks.style.gap = '4px';
                    // Show text on desktop
                    const navLinks = desktopNavLinks.querySelectorAll('.nav-link span');
                    navLinks.forEach(span => span.style.display = 'inline');
                }
                if (desktopNavActions) {
                    desktopNavActions.style.display = 'flex';
                    desktopNavActions.style.gap = '8px';
                }
                if (mobileToggle) mobileToggle.style.display = 'none';
                if (mobileMenu) mobileMenu.style.top = navbarHeight;
            }

            // Set CSS variable for navbar height
            document.documentElement.style.setProperty('--navbar-height', navbarHeight);
        }

        // Initial call
        updateNavbarForScreenSize();

        // Listen for resize events
        window.addEventListener('resize', updateNavbarForScreenSize);

        return window.dash_clientside.no_update;
    }
    """,
    Output("main-navbar", "title"),
    Input("main-navbar", "id"),
)


# Callback to show user menu or login button
@callback(
    Output("user-menu-container", "children"),
    Input("token-store", "data"),
    prevent_initial_call=False,
)
def update_user_menu(token_data):
    """Update user menu based on authentication status"""
    if token_data and token_data.get("token"):
        # User is logged in, show user menu
        username = token_data.get("username", "User")
        is_admin = token_data.get("is_admin", False)

        return dmc.Menu(
            [
                dmc.MenuTarget(
                    html.Button(
                        [
                            DashIconify(
                                icon="material-symbols:person",
                                width=20,
                                height=20,
                                style={"color": "inherit"},
                            ),
                        ],
                        id="user-menu-button",
                        style={
                            "backgroundColor": "transparent",
                            "border": "1px solid rgba(255, 255, 255, 0.2)",
                            "color": "#b8b8b8",
                            "padding": "8px",
                            "borderRadius": "50%",
                            "cursor": "pointer",
                            "transition": "all 0.3s ease",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                            "width": "36px",
                            "height": "36px",
                        },
                    )
                ),
                dmc.MenuDropdown(
                    [
                        dmc.MenuItem(
                            username,
                            leftSection=DashIconify(
                                icon="material-symbols:person", width=16
                            ),
                            disabled=True,
                            style={"fontWeight": "bold"},
                        ),
                        dmc.MenuDivider(),
                        dmc.MenuItem(
                            "Profile",
                            leftSection=DashIconify(
                                icon="material-symbols:account-circle", width=16
                            ),
                            id="menu-profile",
                        ),
                        dmc.MenuItem(
                            "Settings",
                            leftSection=DashIconify(
                                icon="material-symbols:settings", width=16
                            ),
                            id="menu-settings",
                        ),
                        dmc.MenuDivider(),
                        dmc.MenuItem(
                            "Logout",
                            leftSection=DashIconify(
                                icon="material-symbols:logout", width=16
                            ),
                            id="menu-logout",
                            color="red",
                        ),
                    ]
                ),
            ],
            position="bottom-end",
            width=200,
        )
    else:
        # User is not logged in, show login button
        return dcc.Link(
            html.Button(
                [
                    DashIconify(
                        icon="material-symbols:login",
                        width=18,
                        height=18,
                        style={"color": "inherit", "marginRight": "6px"},
                    ),
                    html.Span("Login"),
                ],
                style={
                    "backgroundColor": "transparent",
                    "border": "1px solid rgba(255, 255, 255, 0.2)",
                    "color": "#b8b8b8",
                    "padding": "8px 16px",
                    "borderRadius": "8px",
                    "cursor": "pointer",
                    "transition": "all 0.3s ease",
                    "display": "flex",
                    "alignItems": "center",
                    "fontSize": "14px",
                    "fontWeight": "500",
                },
            ),
            href="/login",
            style={"textDecoration": "none"},
            refresh=False,
        )


# Logout callback
@callback(
    [
        Output("token-store", "data", allow_duplicate=True),
        Output("url", "pathname", allow_duplicate=True),
    ],
    Input("menu-logout", "n_clicks"),
    prevent_initial_call=True,
)
def handle_logout(n_clicks):
    """Handle user logout"""
    if n_clicks:
        # Clear token and redirect to login
        return None, "/login"
    return None, "/"
