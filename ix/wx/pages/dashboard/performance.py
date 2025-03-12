from dash import dcc, html
from dash import Input, Output, State, callback, callback_context, ALL
import dash_bootstrap_components as dbc
import json
import pandas as pd
from ix.bt.analysis.performance import performance_fig
from ix import db
from ix.misc import periods
from cachetools import cached, TTLCache


# Cache configuration (5-minute cache)
cache = TTLCache(maxsize=1, ttl=300)


def create_chart_layout():
    """Reusable chart layout configuration."""
    return {
        "margin": {"l": 20, "r": 20, "t": 20, "b": 20},
        "xaxis": {
            "rangeslider": {"visible": False},
            "gridcolor": "#444",
            "zerolinecolor": "#666",
        },
        "yaxis": {
            "fixedrange": False,
            "gridcolor": "#444",
            "zerolinecolor": "#666",
        },
        "font": {"family": "Roboto Mono, monospace", "size": 12, "color": "#ffffff"},
        "paper_bgcolor": "#000000",
        "plot_bgcolor": "#000000",
        "hovermode": "closest",
        "hoverlabel": {
            "bgcolor": "#000000",
            "bordercolor": "#ffffff",
            "font": {"color": "#ffffff"},
        },
    }


def create_button(period):
    """Reusable button component for period selection."""
    return dbc.Button(
        period,
        id={"type": "period-button", "period": period},
        n_clicks=0,
        style={
            "backgroundColor": "#000000",
            "border": "2px solid #ffffff",
            "color": "#ffffff",
            "transition": "all 0.3s ease-in-out",
            "boxShadow": "0 0 8px rgba(255, 255, 255, 0.3)",
        },
        className="me-2",
    )


def create_performance_graph(universe, fig):
    """Reusable graph component for each universe."""
    return dbc.Col(
        html.Div(
            [
                html.H4(
                    f"{universe}",
                    style={
                        "textAlign": "center",
                        "color": "#ffffff",
                        "textTransform": "uppercase",
                        "letterSpacing": "1px",
                        "marginBottom": "10px",
                    },
                ),
                dcc.Graph(
                    figure=fig,
                    config={"displayModeBar": False},
                    style={
                        "height": "250px",
                        "borderRadius": "8px",
                        "overflow": "hidden",
                    },
                ),
            ],
            style={
                "backgroundColor": "#000000",
                "border": "2px solid #ffffff",
                "borderRadius": "8px",
                "padding": "15px",
                "boxShadow": "0 4px 12px rgba(255, 255, 255, 0.2)",
                "transition": "transform 0.3s ease-in-out",
            },
            className="hover-grow",
        ),
        width=12,
        lg=6,
        xl=3,
    )


@cached(cache)
def get_performance() -> dict:
    """
    Fetch and cache performance data for all universes.
    Returns a dictionary mapping universe names to their performance data.
    """
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
        universe_obj = db.Universe.find_one({"code": universe}).run()
        if not universe_obj:
            continue
        data[universe] = []
        for asset in universe_obj.assets:
            metadata = db.Metadata.find_one({"code": asset.code}).run()
            if metadata is None:
                continue
            perf = asset.model_dump()
            tp_data = metadata.tp().data
            for period in periods:
                perf[period] = tp_data[f"PCT_CHG_{period}"]
            data[universe].append(perf)
    return data


layout = dbc.Container(
    fluid=True,
    children=[
        dbc.Card(
            style={
                "backgroundColor": "#000000",
                "color": "#ffffff",
                "border": "2px solid #ffffff",
                "boxShadow": "0 8px 20px rgba(255, 255, 255, 0.3)",
                "borderRadius": "12px",
                "overflow": "hidden",
            },
            children=[
                dbc.CardHeader(
                    style={
                        "backgroundColor": "#000000",
                        "borderBottom": "2px solid #ffffff",
                        "padding": "15px",
                    },
                    children=dbc.Row(
                        [
                            dbc.Col(
                                html.H3(
                                    "Performance Dashboard",
                                    style={
                                        "color": "#ffffff",
                                        "fontWeight": "bold",
                                        "textTransform": "uppercase",
                                        "letterSpacing": "1px",
                                    },
                                )
                            ),
                        ]
                    ),
                ),
                dbc.CardBody(
                    style={"backgroundColor": "#000000", "color": "#ffffff"},
                    children=[
                        html.Div(
                            [
                                html.Label(
                                    "Select Period: ",
                                    style={
                                        "fontWeight": "bold",
                                        "color": "#ffffff",
                                        "marginRight": "10px",
                                    },
                                ),
                                dbc.ButtonGroup(
                                    [create_button(period) for period in periods],
                                    style={"marginBottom": "20px"},
                                ),
                            ],
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "padding": "10px",
                            },
                        ),
                        dcc.Loading(
                            id="loading-performance-graphs",
                            type="default",
                            children=html.Div(id="performance-graphs-container"),
                        ),
                    ],
                ),
            ],
        ),
    ],
)


@callback(
    Output("performance-graphs-container", "children"),
    Input({"type": "period-button", "period": ALL}, "n_clicks"),
)
def update_graphs(n_clicks_list):
    """
    Update graphs based on the selected period.
    """
    ctx = callback_context
    selected_period = "1D"  # Default period

    # Determine which button was clicked
    for t in ctx.triggered:
        if "period-button" in t["prop_id"]:
            try:
                selected_period = json.loads(t["prop_id"].split(".")[0]).get(
                    "period", "1D"
                )
                break
            except (json.JSONDecodeError, KeyError):
                selected_period = "1D"

    # Generate graphs for each universe
    graph_divs = []
    for universe, performances in get_performance().items():
        performance_data = pd.DataFrame(performances)
        if "name" not in performance_data.columns:
            continue
        performance_data = performance_data.set_index("name")
        if selected_period not in performance_data.columns:
            continue

        # Create the figure
        fig = performance_fig(performance_data[selected_period].copy())
        fig.update_layout(create_chart_layout())

        # Append the graph component
        graph_divs.append(create_performance_graph(universe, fig))

    return dbc.Row(graph_divs, className="g-4")


CSS_TEXT = """
<style>
/* Hover grow effect */
.hover-grow:hover {
    transform: scale(1.02);
    box-shadow: 0 6px 16px rgba(255, 255, 255, 0.4);
}

/* Button hover effect */
.btn-secondary:hover {
    background-color: #ffffff !important;
    color: #000000 !important;
    border-color: #ffffff !important;
    box-shadow: 0 0 12px rgba(255, 255, 255, 0.6) !important;
}

/* Loading spinner customization */
.dash-loading-spinner {
    border-top-color: #ffffff !important;
    border-left-color: #ffffff !important;
}
</style>
"""

# Inject CSS
inline_styles = dcc.Markdown(CSS_TEXT, dangerously_allow_html=True)

# Final layout
final_layout = html.Div([inline_styles, layout])
