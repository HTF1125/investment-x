import ix
import click
import os
from dash import Dash, dcc, html, page_container
import dash_bootstrap_components as dbc
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


from dash import Dash, html
from flask import Blueprint, jsonify
import pandas as pd

server = app.server  # Get the underlying Flask server

# Create a Flask Blueprint for your API endpoints
api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/metadata")
def get_metadata():
    try:
        metadatas = pd.DataFrame(
            [metadata.model_dump() for metadata in ix.db.Metadata.find().run()]
        )
        # metadatas = metadatas.filter(
        #     items=[
        #         "code",
        #         "exchange",
        #         "market",
        #         "name",
        #         "id_isin",
        #         "remark",
        #         "bbg_ticker",
        #         "yah_ticker",
        #         "fred_ticker",
        #     ]
        # )
    except Exception as e:
        return jsonify({"error": "Failed to fetch metadata"}), 500
    return metadatas.to_dict("records")


# Register the blueprint with the Flask server
server.register_blueprint(api_bp)


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
        dcc.Interval(
            id="refresh-interval",
            interval=300000,
            n_intervals=0,
        ),
        navbar,
        html.Div(style={"height": "70px"}),
        dbc.Container(
            page_container,
            fluid=True,
            className="py-2",
            style={
                "maxWidth": "1680px",
                "margin": "0 auto",
            },
        ),
    ],
)


@click.command()
@click.option("--debug", is_flag=True, help="Enable task mode.")
def cli(debug: bool = False):
    """Run the application with specified tasks."""

    if debug:
        app.run(debug=True)
        logger.info("All Tasks Completed Successfully.")
        return
    app.run_server(host="0.0.0.0", port=int(os.environ.get("PORT", 8050)))


if __name__ == "__main__":
    cli()
