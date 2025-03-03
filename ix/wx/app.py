import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, page_container
from ix.misc import get_logger
from ix.wx.components.navbar import navbar

logger = get_logger("InvestmentX")

# Initialize the Dash app with dark mode (using the DARKLY theme)
app = Dash(
    __name__,
    use_pages=True,
    assets_folder="assets",
    pages_folder="pages",
    suppress_callback_exceptions=True,
    external_stylesheets=[dbc.themes.DARKLY, dbc.icons.FONT_AWESOME],
)

# Get the underlying Flask server
server = app.server


# Define the layout for the Dash app
app.layout = html.Div(
    style={
        "backgroundColor": "#000000",
        "color": "#ffffff",
        "minHeight": "100vh",
        "fontFamily": "Cascadia Code, sans-serif",
        "fontSize": "16px",
    },
    children=[
        dcc.Location(id="url", refresh=False),
        dcc.Store(id="token-store", storage_type="local"),
        navbar,
        html.Div(style={"height": "70px"}),
        dbc.Container(
            page_container,
            fluid=True,
            className="py-2",
            style={"maxWidth": "1680px", "margin": "0 auto"},
        ),
    ],
)
