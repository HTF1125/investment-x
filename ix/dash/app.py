import pandas as pd
import dash
from dash import dcc, html
import dash_bootstrap_components as dbc

# Initialize Dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Global Markets Dashboard"

# Include external CSS file
app.css.config.serve_locally = True

# Import analysis modules
from .ism_analysis import create_ism_section
from .performance_analysis import create_universe_section, UNIVERSES

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




# App layout
app.layout = dbc.Container(
    [
        # Header
        html.H1("📈 Global Markets Dashboard", className="main-title"),
        html.P(
            "Real-time performance analysis across all asset universes",
            className="subtitle",
        ),
        # ISM Cycle Analysis section
        create_ism_section(),
        # Universe sections
        html.Div(
            [
                create_universe_section(universe_name, icon)
                for universe_name, icon in UNIVERSES
            ]
        ),
        # Footer
        html.Div(
            [
                html.Hr(
                    style={
                        "border-color": "rgba(255, 255, 255, 0.2)",
                        "margin": "40px 0",
                    }
                ),
                html.P(
                    "📈 Global Markets Dashboard | Powered by Dash & Plotly",
                    style={
                        "text-align": "center",
                        "color": "#718096",
                        "margin": "20px 0",
                    },
                ),
            ]
        ),
    ],
    fluid=True,
)



# Export the Flask server for use in other applications
server = app.server

# Run the app
if __name__ == "__main__":
    app.run_server(debug=True, host='0.0.0.0', port=8050)
