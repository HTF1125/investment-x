import pandas as pd
import dash
from dash import dcc, html, Input, Output, clientside_callback, _dash_renderer
import dash_mantine_components as dmc
from dash_iconify import DashIconify

# Set React version for Mantine compatibility
_dash_renderer._set_react_version("18.2.0")

# Initialize Dash app with pages
# Specify absolute pages_folder to prevent duplicate page discovery
import os

pages_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pages")

app = dash.Dash(
    __name__,
    use_pages=True,
    pages_folder=pages_folder,
    suppress_callback_exceptions=True,
)
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

            /* Scrollbar styling for insights table */
            #scroll-container::-webkit-scrollbar {
                width: 12px;
                height: 12px;
            }
            #scroll-container::-webkit-scrollbar-track {
                background: #1e293b;
                border-radius: 6px;
            }
            #scroll-container::-webkit-scrollbar-thumb {
                background: #475569;
                border-radius: 6px;
                border: 2px solid #1e293b;
            }
            #scroll-container::-webkit-scrollbar-thumb:hover {
                background: #64748b;
            }

            /* Enhanced Insights page full height layout */
            .insights-page-container {
                height: 100vh;
                display: flex;
                flex-direction: column;
                overflow: hidden;
                position: relative;
            }
            .insights-search-header {
                flex-shrink: 0;
            }
            #scroll-container {
                flex: 1;
                overflow-y: auto !important;
                overflow-x: auto !important;
                scroll-behavior: smooth;
                min-height: 0;
                position: relative;
                padding: 0;
            }

            /* Ensure table fills container */
            #insights-table-container {
                width: 100%;
            }

            /* Enhanced Insights table styling */
            .insight-table-row {
                transition: all 0.2s ease;
            }
            .insight-table-row:hover {
                background-color: #1e293b !important;
                cursor: pointer;
                transform: scale(1.001);
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            }

            /* Table container enhancements */
            .insights-scroll-container {
                scrollbar-width: thin;
                scrollbar-color: #475569 #1e293b;
            }
            .insights-scroll-container::-webkit-scrollbar {
                width: 10px;
                height: 10px;
            }
            .insights-scroll-container::-webkit-scrollbar-track {
                background: #1e293b;
                border-radius: 5px;
            }
            .insights-scroll-container::-webkit-scrollbar-thumb {
                background: #475569;
                border-radius: 5px;
                border: 2px solid #1e293b;
            }
            .insights-scroll-container::-webkit-scrollbar-thumb:hover {
                background: #64748b;
            }

            /* Enhanced header styling */
            .insights-search-header {
                backdrop-filter: blur(10px);
                background-color: rgba(15, 23, 42, 0.95) !important;
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
            # Stores for app data
            dcc.Store(id="token-store", data=None, storage_type="session"),
            dcc.Store(id="global-data", data=None),
            dcc.Location(id="url", refresh=False),
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


# Initialize scheduler
from .scheduler import start_scheduler

# Register API routes
from .api.app import register_api_routes

register_api_routes(app)

# Initialize and start the scheduler
# try:
#     scheduler = start_scheduler(8)
#     print("Task scheduler initialized and started")
# except Exception as e:
#     print(f"Warning: Failed to initialize scheduler: {e}")

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
    print("  - Strategies: http://localhost:8050/strategies")
    print("  - Data: http://localhost:8050/data")
    print("  - Risk: http://localhost:8050/risk")
    print("  - Login: http://localhost:8050/login")
    print("  - Register: http://localhost:8050/register")
    print("API endpoints available:")
    print("  - Health check: http://localhost:8050/api/health")
    print("  - Timeseries list: http://localhost:8050/api/timeseries")
    print("  - Timeseries by ID: http://localhost:8050/api/timeseries/{id}")
    print("  - Timeseries by code: http://localhost:8050/api/timeseries/code/{code}")
    print("  - Upload data: http://localhost:8050/api/upload_data")
    print("Scheduled tasks:")
    print("  - Daily data updates at 9:00 AM UTC")
    app.run_server(debug=True, host="0.0.0.0", port=8050)
