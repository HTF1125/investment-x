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


# Include external CSS file
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

# App layout with MantineProvider
app.layout = dmc.MantineProvider(
    html.Div(
        [
            # Store for token data
            dcc.Store(id="token-store", data=None),
            # Navbar with integrated Mantine theme toggle
            html.Div(
                [
                    navbar_layout,
                ]
            ),
            # Page content
            dash.page_container,
        ],
        style={
            "backgroundColor": "#0f172a",
            "color": "#ffffff",
            "minHeight": "100vh",
            "marginTop": "80px",
            "padding": "20px",
        },
    ),
    id="mantine-provider",
    forceColorScheme="dark",

)


# Mantine theme switching callback with logo switching
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
