import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta
import plotly.graph_objects as go
from ix.core.tech import RSI, SqueezeMomentum


def create_chart_layout():
    return {
        "margin": {"l": 25, "r": 25, "t": 25, "b": 25},
        "showlegend": True,
        "legend": {
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "center",
            "x": 0.5,
        },
        "xaxis": {"rangeslider": {"visible": False}, "gridcolor": "#555"},
        "yaxis": {"fixedrange": False, "gridcolor": "#555"},
        "font": {"family": "Arial, sans-serif", "size": 12, "color": "#ffffff"},
        # Make backgrounds transparent.
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
    }


@callback(
    [Output("sm-chart", "figure"), Output("rsi-chart", "figure")],
    [
        Input("asset-select", "value"),
        Input("start-date", "date"),
        Input("end-date", "date"),
    ],
)
def update_dashboard(asset, start_date, end_date):
    try:
        rsi = RSI.from_meta(
            code=asset,
            window=14,
            overbought=70,
            oversold=30,
            ma_type="SMA",
            ma_length=14,
        )
        sm = SqueezeMomentum.from_meta(asset)
        start_date_str = str(start_date) if start_date else None
        end_date_str = str(end_date) if end_date else None
        sm_fig = sm.plot(start=start_date_str, end=end_date_str)
        rsi_fig = rsi.plot(start=start_date_str, end=end_date_str)
        sm_fig.update_layout(create_chart_layout())
        rsi_fig.update_layout(create_chart_layout())
        return sm_fig, rsi_fig
    except Exception as e:
        empty_fig = go.Figure(layout=create_chart_layout())
        return empty_fig, empty_fig


def get_layout():
    return dbc.Container(
        fluid=True,
        className="py-3",
        style={"backgroundColor": "transparent", "color": "#f8f9fa"},
        children=[
            dbc.Card(
                className="shadow rounded-3 w-100",
                style={
                    "backgroundColor": "transparent",
                    "color": "#f8f9fa",
                    "border": "1px solid #f8f9fa",
                    "marginBottom": "1rem",
                },
                children=[
                    dbc.CardHeader(
                        dbc.Row(
                            [
                                dbc.Col(
                                    html.H3("Technical Analysis", className="mb-0"),
                                    width=True,
                                ),
                                dbc.Col(
                                    dbc.Select(
                                        id="asset-select",
                                        options=[
                                            {"label": "IAU", "value": "IAU US Equity"},
                                            {"label": "SPY", "value": "SPY US Equity"},
                                        ],
                                        value="IAU US Equity",
                                        style={
                                            "backgroundColor": "transparent",
                                            "color": "#f8f9fa",
                                            "border": "1px solid #f8f9fa",
                                            "borderRadius": "4px",
                                            "padding": "0.25rem 0.5rem",
                                        },
                                    ),
                                    width="auto",
                                ),
                                dbc.Col(
                                    dcc.DatePickerSingle(
                                        id="start-date",
                                        date=(
                                            datetime.now() - timedelta(days=365)
                                        ).date(),
                                        display_format="YYYY-MM-DD",
                                        style={
                                            "backgroundColor": "transparent",
                                            "color": "#f8f9fa",
                                            "border": "1px solid #f8f9fa",
                                            "borderRadius": "4px",
                                            "padding": "0.25rem",
                                        },
                                    ),
                                    width="auto",
                                ),
                                dbc.Col(
                                    dcc.DatePickerSingle(
                                        id="end-date",
                                        date=datetime.now().date(),
                                        display_format="YYYY-MM-DD",
                                        style={
                                            "backgroundColor": "transparent",
                                            "color": "#f8f9fa",
                                            "border": "1px solid #f8f9fa",
                                            "borderRadius": "4px",
                                            "padding": "0.25rem",
                                        },
                                    ),
                                    width="auto",
                                ),
                            ],
                            align="center",
                            className="g-2",
                        ),
                        style={
                            "backgroundColor": "transparent",
                            "color": "#f8f9fa",
                            "borderBottom": "2px solid #f8f9fa",
                            "padding": "1rem",
                        },
                    ),
                    dbc.CardBody(
                        style={
                            "backgroundColor": "transparent",
                            "color": "#f8f9fa",
                            "padding": "1.5rem",
                        },
                        children=[
                            dcc.Loading(
                                id="loading-performance-graphs",
                                type="default",
                                children=[
                                    dbc.Row(
                                        dbc.Col(
                                            dbc.Card(
                                                dbc.CardBody(
                                                    dcc.Graph(
                                                        id="sm-chart",
                                                        config={
                                                            "displayModeBar": False
                                                        },
                                                        style={
                                                            "height": "300px",
                                                            "width": "100%",
                                                        },
                                                    )
                                                ),
                                                className="mb-3",
                                                style={
                                                    "backgroundColor": "transparent",
                                                    "border": "1px solid #f8f9fa",
                                                    "padding": "0.5rem",
                                                },
                                            ),
                                            width=12,
                                        )
                                    ),
                                    dbc.Row(
                                        dbc.Col(
                                            dbc.Card(
                                                dbc.CardBody(
                                                    dcc.Graph(
                                                        id="rsi-chart",
                                                        config={
                                                            "displayModeBar": False
                                                        },
                                                        style={
                                                            "height": "300px",
                                                            "width": "100%",
                                                        },
                                                    )
                                                ),
                                                style={
                                                    "backgroundColor": "transparent",
                                                    "border": "1px solid #f8f9fa",
                                                    "padding": "0.5rem",
                                                },
                                            ),
                                            width=12,
                                        )
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            )
        ],
    )
