import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from wx.components.navbar import navbar

# Initialize the Dash app with dark mode (using the DARKLY theme)
app = dash.Dash(
    __name__,
    use_pages=True,  # Enable multi-page routing
    assets_folder="wx/assets",  # Specify the assets folder
    pages_folder="wx/pages",
    suppress_callback_exceptions=True,
    external_stylesheets=[
        dbc.themes.DARKLY,
        "https://cdn.jsdelivr.net/npm/summernote@0.8.18/dist/summernote.min.css",
    ],
    external_scripts=[
        "https://cdn.jsdelivr.net/npm/summernote@0.8.18/dist/summernote.min.js",
    ],
)

app.layout = html.Div(
    style={
        "backgroundColor": "#000000",
        "color": "#ffffff",
        "minHeight": "100vh",
    },
    children=[
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="token-store", storage_type="local"),
        navbar,
        html.Div(style={"height": "70px"}),
        dbc.Container(
            dash.page_container,
            fluid=True,
            className="py-2",
            style={
                "maxWidth": "1240px",
                "margin": "0 auto",
            },
        ),
    ],
)


import os



if __name__ == "__main__":
    app.run_server(host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))
