import os
import click
import pandas as pd
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, page_container
from flask import jsonify

import ix
from ix.wx.components.navbar import navbar

logger = ix.misc.get_logger("InvestmentX")

# Initialize the Dash app with dark mode (using the DARKLY theme)
app = Dash(
    __name__,
    use_pages=True,
    assets_folder="wx/assets",
    pages_folder="wx/pages",
    suppress_callback_exceptions=True,
    external_stylesheets=[
        dbc.themes.DARKLY,
        dbc.icons.FONT_AWESOME,
        "https://cdn.jsdelivr.net/npm/summernote@0.8.18/dist/summernote.min.css",
    ],
    external_scripts=[
        "https://cdn.jsdelivr.net/npm/summernote@0.8.18/dist/summernote.min.js",
    ],
)

# Get the underlying Flask server
server = app.server


@server.route("/api/metadata")
def get_metadata():
    """
    API endpoint to retrieve metadata.
    """
    try:
        metadatas = pd.DataFrame(
            [metadata.model_dump() for metadata in ix.db.Metadata.find().run()]
        )
    except Exception as e:
        logger.error("Error fetching metadata: %s", e)
        return jsonify({"error": "Failed to fetch metadata"}), 500

    return jsonify(metadatas.to_dict("records"))


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


@click.command()
@click.option("--debug", is_flag=True, help="Run the app in debug mode.")
def cli(debug: bool = False) -> None:
    """
    Run the Dash application.
    """
    port = int(os.environ.get("PORT", 8050))
    logger.info("Starting app on port %d", port)
    app.run_server(port=port, debug=debug)


if __name__ == "__main__":
    cli()
