import json
import zlib
import base64
import pandas as pd
import logging

from dash import dcc, html, Input, Output, State, callback, ALL
import dash_bootstrap_components as dbc
import dash

from ix.bt.analysis.performance import performance_fig
from ix import db
from ix.misc import periods

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# --- Utility functions for compression ---
def compress_data(data: dict) -> str:
    """
    Compress a JSON-serializable dict to a base64 encoded string.
    """
    try:
        json_str = json.dumps(data)
    except Exception as e:
        logger.exception("Error serializing data to JSON")
        raise e
    try:
        compressed = zlib.compress(json_str.encode("utf-8"))
    except Exception as e:
        logger.exception("Error compressing JSON data")
        raise e
    try:
        encoded = base64.b64encode(compressed).decode("utf-8")
    except Exception as e:
        logger.exception("Error encoding compressed data to base64")
        raise e
    return encoded

def decompress_data(data_str) -> dict:
    """
    Decompress a base64 encoded string back into a dict.
    If the data is already a dict, return it directly.
    """
    if isinstance(data_str, dict):
        return data_str
    try:
        decompressed = zlib.decompress(base64.b64decode(data_str.encode("utf-8")))
    except Exception as e:
        logger.exception("Error decompressing data")
        raise e
    try:
        return json.loads(decompressed.decode("utf-8"))
    except Exception as e:
        logger.exception("Error parsing decompressed JSON data")
        raise e

# --- Layout ---
layout = dbc.Container(
    [
        # Interval component to trigger refresh every 5 minutes (300,000 ms)
        dcc.Interval(
            id="refresh-interval",
            interval=300000,
            n_intervals=0,
        ),
        # Using compressed data in the store (as a string)
        dcc.Store(id="performance-store", storage_type="local"),
        dbc.Card(
            [
                dbc.CardHeader(
                    dbc.Row(
                        [
                            dbc.Col(html.H3("Performance", className="mb-0")),
                        ],
                        align="center",
                    ),
                    style={
                        "backgroundColor": "transparent",
                        "color": "#f8f9fa",
                        "borderBottom": "2px solid #f8f9fa",
                        "padding": "1rem",
                    },
                ),
                dbc.CardBody(
                    [
                        # Period selector using a button group.
                        html.Div(
                            [
                                html.Label(
                                    "Select Period: ",
                                    style={
                                        "marginRight": "20px",
                                        "fontWeight": "bold",
                                        "color": "#f8f9fa",
                                    },
                                ),
                                dbc.ButtonGroup(
                                    [
                                        dbc.Button(
                                            period,
                                            id={
                                                "type": "period-button",
                                                "period": period,
                                            },
                                            n_clicks=0,
                                            style={
                                                "backgroundColor": "transparent",
                                                "border": "1px solid #f8f9fa",
                                                "padding": "0.5rem",
                                                "margin": "0.25rem",
                                                "color": "#f8f9fa",
                                                "borderRadius": "4px",
                                                "cursor": "pointer",
                                            },
                                        )
                                        for period in periods
                                    ]
                                ),
                            ],
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "marginBottom": "1rem",
                            },
                        ),
                        dcc.Loading(
                            id="loading-performance-graphs",
                            children=html.Div(
                                id="performance-graphs-container",
                                style={
                                    "display": "grid",
                                    "gridTemplateColumns": "repeat(4, 1fr)",
                                    "gridGap": "10px",
                                    "justifyItems": "center",
                                },
                            ),
                            type="default",
                        ),
                        html.Div(id="dummy-output", style={"display": "none"}),
                    ],
                    style={
                        "backgroundColor": "transparent",
                        "color": "#f8f9fa",
                        "padding": "1.5rem",
                    },
                ),
            ],
            style={
                "backgroundColor": "transparent",
                "border": "1px solid #f8f9fa",
                "borderRadius": "8px",
                "boxShadow": "2px 2px 5px rgba(0,0,0,0.5)",
                "margin": "1rem 0",
            },
            className="rounded-3 w-100",
        ),
    ],
    fluid=True,
    className="py-1",
    style={"backgroundColor": "transparent"},
)

# --- Callback 1: Refresh Performance Data ---
@callback(
    Output("performance-store", "data"),
    Input("refresh-interval", "n_intervals"),
)
def refresh_data(n_intervals):
    """
    Refresh performance data every 5 minutes and store a compressed version in local storage.
    """
    logger.info(f"Refreshing performance data at interval: {n_intervals}")
    universes = [
        "LocalIndices",
        "GicsUS",
        "GlobalMarkets",
        "Styles",
        "GlobalBonds",
        "Commodities",
        "Themes",
        "Currencies",
    ]
    data = {}
    for universe in universes:
        logger.debug(f"Processing universe: {universe}")
        try:
            universe_obj = db.Universe.find_one({"code": universe}).run()
        except Exception as e:
            logger.exception(f"Error fetching universe {universe}: {e}")
            continue
        if not universe_obj:
            logger.warning(f"No universe object found for: {universe}")
            continue
        data[universe] = []
        for asset in universe_obj.assets:
            logger.debug(f"Processing asset: {asset.code} in universe: {universe}")
            try:
                metadata = db.Metadata.find_one({"code": asset.code}).run()
            except Exception as e:
                logger.exception(f"Error fetching metadata for asset {asset.code}: {e}")
                continue
            if metadata is None:
                logger.warning(f"No metadata found for asset: {asset.code}")
                continue
            # Build a lean performance dictionary rather than a full model dump.
            perf = {"name": asset.code}
            for period in periods:
                try:
                    value = metadata.tp(field=f"PCT_CHG_{period}").data
                    # Ensure the value is JSON serializable by trying to cast it to a float.
                    try:
                        value = float(value)
                    except Exception as conv_err:
                        logger.debug(f"Value for {asset.code} period {period} not castable to float: {value}")
                    perf[period] = value
                except Exception as e:
                    logger.exception(f"Error retrieving performance for period {period} for asset {asset.code}: {e}")
                    perf[period] = None
            data[universe].append(perf)
    try:
        compressed = compress_data(data)
    except Exception as e:
        logger.exception("Error compressing performance data")
        raise e
    logger.info("Performance data compressed successfully")
    return compressed

# --- Callback 2: Update Graphs Based on Selected Period ---
@callback(
    Output("performance-graphs-container", "children"),
    Input({"type": "period-button", "period": ALL}, "n_clicks"),
    State("performance-store", "data"),
)
def update_graphs(n_clicks_list, compressed_data):
    """
    Update performance graphs based on the selected period.
    Decompress the stored data before processing.
    """
    if not compressed_data:
        logger.info("No compressed data found in performance-store; returning empty list.")
        return []  # No data yet; dcc.Loading will show a spinner

    try:
        data = decompress_data(compressed_data)
    except Exception as e:
        logger.exception("Error decompressing performance data")
        return []

    ctx = dash.callback_context
    selected_period = "1D"  # default period
    for t in ctx.triggered:
        if "period-button" in t["prop_id"]:
            try:
                selected_period = json.loads(t["prop_id"].split(".")[0]).get("period", "1D")
                break
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Error parsing triggered period: {e}")
                selected_period = "1D"

    logger.info(f"Selected period for graphs: {selected_period}")
    graph_divs = []
    for universe, performances in data.items():
        logger.debug(f"Building graph for universe: {universe}")
        performance_data = pd.DataFrame(performances)
        if "name" not in performance_data.columns:
            logger.warning(f"'name' column not found for universe: {universe}")
            continue
        performance_data = performance_data.set_index("name")
        if selected_period not in performance_data.columns:
            logger.warning(f"Selected period {selected_period} not found for universe: {universe}")
            continue

        try:
            fig = performance_fig(performance_data[selected_period])
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(gridcolor="#555"),
                yaxis=dict(gridcolor="#555"),
            )
        except Exception as e:
            logger.exception(f"Error creating figure for universe {universe}: {e}")
            continue
        graph_divs.append(
            html.Div(
                [
                    html.H3(
                        f"{universe}",
                        style={
                            "textAlign": "center",
                            "fontSize": "12px",
                            "color": "#f8f9fa",
                            "marginBottom": "0.5rem",
                        },
                    ),
                    dcc.Graph(
                        figure=fig,
                        config={"displayModeBar": False, "responsive": True},
                        style={"height": "250px"},
                    ),
                ],
                style={
                    "border": "1px solid #f8f9fa",
                    "padding": "5px",
                    "backgroundColor": "transparent",
                    "boxShadow": "1px 1px 3px rgba(0,0,0,0.5)",
                    "width": "100%",
                },
            )
        )
    return graph_divs

# --- Callback 3: Update Period Button Styles ---
@callback(
    Output({"type": "period-button", "period": ALL}, "style"),
    Input({"type": "period-button", "period": ALL}, "n_clicks"),
)
def update_button_styles(n_clicks_list):
    ctx = dash.callback_context
    if not ctx.triggered:
        active_period = "1D"
    else:
        try:
            active_period = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])["period"]
        except Exception as e:
            logger.warning(f"Error parsing active period from triggered context: {e}")
            active_period = "1D"
    return [
        {
            "backgroundColor": "transparent",
            "border": ("2px solid #f8f9fa" if period == active_period else "1px solid #f8f9fa"),
            "padding": "0.5rem",
            "margin": "0.25rem",
            "color": "#f8f9fa",
            "borderRadius": "4px",
            "cursor": "pointer",
        }
        for period in periods
    ]
