import pandas as pd
import dash
from dash import dcc, html, Input, Output, clientside_callback, _dash_renderer
import dash_mantine_components as dmc
from dash_iconify import DashIconify

# Set React version for Mantine compatibility
_dash_renderer._set_react_version("18.2.0")

# Initialize Dash app with pages
app = dash.Dash(__name__, use_pages=True, suppress_callback_exceptions=True)
app.title = "Global Markets Dashboard"

# Include external CSS file
app.css.config.serve_locally = True

from .components.navbar import navbar, layout as navbar_layout
import plotly.graph_objects as go
import pandas as pd

# Include external CSS file with CSS variables for navbar spacing
app.index_string = """
<!DOCTYPE html>
<html>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
        <link rel="stylesheet" href="/assets/styles/global.css">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            :root {
                --navbar-height: 70px;
            }

            /* Ensure pages don't overlap with navbar */
            #page-content {
                margin-top: 90px !important;
                min-height: calc(100vh - 90px) !important;
                padding: 20px !important;
                transition: margin-top 0.3s ease;
            }

            /* Mobile adjustments */
            @media (max-width: 767px) {
                :root {
                    --navbar-height: 55px;
                }
                #page-content {
                    margin-top: 75px !important;
                    min-height: calc(100vh - 75px) !important;
                    padding: 16px !important;
                }
            }

            /* Tablet adjustments */
            @media (min-width: 768px) and (max-width: 1023px) {
                :root {
                    --navbar-height: 65px;
                }
                #page-content {
                    margin-top: 85px !important;
                    min-height: calc(100vh - 85px) !important;
                    padding: 18px !important;
                }
            }

            /* Ensure smooth transitions */
            body {
                transition: all 0.3s ease;
            }

            /* Additional safety margin for content */
            .dash-page-content {
                padding-top: 20px !important;
            }

            /* Responsive sticky positioning for time period selector */
            @media (max-width: 767px) {
                .time-period-selector {
                    top: 75px !important;
                }
            }

            @media (min-width: 768px) and (max-width: 1023px) {
                .time-period-selector {
                    top: 85px !important;
                }
            }

            @media (min-width: 1024px) {
                .time-period-selector {
                    top: 90px !important;
                }
            }

            /* Skeleton loader animations for dashboard */
            @keyframes pulse {
                0% { background-position: 200% 0; }
                100% { background-position: -200% 0; }
            }

            .skeleton-pulse {
                animation: pulse 2s ease-in-out infinite;
            }

            /* Responsive sticky positioning for time period selector */
            @media (max-width: 767px) {
                .time-period-selector {
                    top: 75px !important;
                }
            }

            @media (min-width: 768px) and (max-width: 1023px) {
                .time-period-selector {
                    top: 85px !important;
                }
            }

            @media (min-width: 1024px) {
                .time-period-selector {
                    top: 90px !important;
                }
            }

            /* Skeleton loader animations */
            @keyframes pulse {
                0% { background-position: 200% 0; }
                100% { background-position: -200% 0; }
            }

            .skeleton-pulse {
                animation: pulse 2s ease-in-out infinite;
            }
        </style>
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""

# App layout with MantineProvider and proper spacing
app.layout = dmc.MantineProvider(
    html.Div(
        [
            # Store for token data
            dcc.Store(id="token-store", data=None),
            # Navbar (fixed position)
            navbar_layout,
            # Page content with proper spacing
            html.Div(
                dash.page_container,
                id="page-content",
                style={
                    "backgroundColor": "#0f172a",
                    "color": "#ffffff",
                    "minHeight": "calc(100vh - 90px)",
                    "marginTop": "90px",  # Fixed margin to ensure no overlap
                    "padding": "20px",
                    "transition": "all 0.3s ease",
                },
            ),
        ],
        style={
            "backgroundColor": "#0f172a",
            "color": "#ffffff",
            "minHeight": "100vh",
        },
    ),
    id="mantine-provider",
    forceColorScheme="dark",
)


# Enhanced Mantine theme switching callback with proper spacing updates
clientside_callback(
    """
    function(n_clicks) {
        if (n_clicks) {
            const currentScheme = document.documentElement.getAttribute('data-mantine-color-scheme') || 'dark';
            const newScheme = currentScheme === 'dark' ? 'light' : 'dark';

            // Set Mantine color scheme
            document.documentElement.setAttribute('data-mantine-color-scheme', newScheme);

            // Update CSS variables for our custom components
            const root = document.documentElement;
            const pageContent = document.getElementById('page-content');

            if (newScheme === 'light') {
                // Light theme
                root.style.setProperty('--bg-primary', '#ffffff');
                root.style.setProperty('--bg-secondary', '#f8fafc');
                root.style.setProperty('--text-primary', '#1f2937');
                root.style.setProperty('--text-secondary', '#6b7280');
                root.style.setProperty('--border', '#e5e7eb');
                root.style.setProperty('--surface', '#ffffff');
                root.setAttribute('data-theme', 'light');
                document.body.style.background = 'linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 50%, #cbd5e1 100%)';
                document.body.style.color = '#1f2937';

                // Update page content background
                if (pageContent) {
                    pageContent.style.backgroundColor = '#f8fafc';
                    pageContent.style.color = '#1f2937';
                }

                // Update navbar
                const navbar = document.querySelector('nav');
                if (navbar) {
                    navbar.style.backgroundColor = 'rgba(255, 255, 255, 0.95)';
                    navbar.style.borderBottom = '1px solid rgba(0, 0, 0, 0.1)';
                }

                // Update mobile menu
                const mobileMenu = document.getElementById('mobile-menu');
                if (mobileMenu) {
                    mobileMenu.style.backgroundColor = 'rgba(255, 255, 255, 0.98)';
                    mobileMenu.style.borderBottom = '1px solid rgba(0, 0, 0, 0.1)';
                }

                // Update logo for light theme
                const logo = document.getElementById('navbar-logo');
                if (logo) {
                    logo.src = '/assets/images/investment-x-logo-dark.svg';
                    logo.style.filter = 'drop-shadow(0 0 10px rgba(0, 0, 0, 0.1))';
                }
            } else {
                // Dark theme
                root.style.setProperty('--bg-primary', '#0f172a');
                root.style.setProperty('--bg-secondary', '#1e293b');
                root.style.setProperty('--text-primary', '#ffffff');
                root.style.setProperty('--text-secondary', '#cbd5e0');
                root.style.setProperty('--border', '#475569');
                root.style.setProperty('--surface', 'rgba(30, 41, 59, 0.95)');
                root.setAttribute('data-theme', 'dark');
                document.body.style.background = 'linear-gradient(135deg, #0c1623 0%, #1a2332 50%, #2d3748 100%)';
                document.body.style.color = '#ffffff';

                // Update page content background
                if (pageContent) {
                    pageContent.style.backgroundColor = '#0f172a';
                    pageContent.style.color = '#ffffff';
                }

                // Update navbar
                const navbar = document.querySelector('nav');
                if (navbar) {
                    navbar.style.backgroundColor = 'rgba(15, 15, 15, 0.95)';
                    navbar.style.borderBottom = '1px solid rgba(255, 255, 255, 0.1)';
                }

                // Update mobile menu
                const mobileMenu = document.getElementById('mobile-menu');
                if (mobileMenu) {
                    mobileMenu.style.backgroundColor = 'rgba(15, 15, 15, 0.98)';
                    mobileMenu.style.borderBottom = '1px solid rgba(255, 255, 255, 0.1)';
                }

                // Update logo for dark theme
                const logo = document.getElementById('navbar-logo');
                if (logo) {
                    logo.src = '/assets/images/investment-x-logo-light.svg';
                    logo.style.filter = 'drop-shadow(0 0 10px rgba(255, 255, 255, 0.1))';
                }
            }
        }

        return window.dash_clientside.no_update;
    }
    """,
    Output("color-scheme-toggle", "id"),
    Input("color-scheme-toggle", "n_clicks"),
)


# Callback to ensure proper spacing on page load and window resize
clientside_callback(
    """
    function() {
        function updatePageContentSpacing() {
            const navbar = document.getElementById('main-navbar');
            const pageContent = document.getElementById('page-content');

            if (navbar && pageContent) {
                const navbarHeight = navbar.offsetHeight;
                pageContent.style.marginTop = navbarHeight + 'px';
                pageContent.style.minHeight = `calc(100vh - ${navbarHeight}px)`;
            }
        }

        // Initial spacing update
        updatePageContentSpacing();

        // Update spacing when window resizes (navbar height might change)
        window.addEventListener('resize', updatePageContentSpacing);

        // Use MutationObserver to detect when navbar height changes
        const navbar = document.getElementById('main-navbar');
        if (navbar) {
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'style') {
                        updatePageContentSpacing();
                    }
                });
            });

            observer.observe(navbar, {
                attributes: true,
                attributeFilter: ['style']
            });
        }

        return window.dash_clientside.no_update;
    }
    """,
    Output("page-content", "title"),
    Input("page-content", "id"),
)


# Export the Flask server for use in other applications
server = app.server

# Run the app
if __name__ == "__main__":
    print("Starting Investment-X Dashboard...")
    print("Dashboard will be available at: http://localhost:8050")
    print("Pages available:")
    print("  - Dashboard: http://localhost:8050/")
    print("  - Macro: http://localhost:8050/macro")
    print("  - Insights: http://localhost:8050/insights")
    print("  - Views: http://localhost:8050/views")
    print("  - Strategies: http://localhost:8050/strategies")
    app.run_server(debug=True, host="0.0.0.0", port=8050)
