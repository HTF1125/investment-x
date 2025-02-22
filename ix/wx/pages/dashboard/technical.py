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
        "xaxis": {"rangeslider": {"visible": False}},
        "yaxis": {"fixedrange": False},
        "font": {"family": "Arial, sans-serif", "size": 12, "color": "#ffffff"},
        "paper_bgcolor": "#212529",
        "plot_bgcolor": "#212529",
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
            ma_type="SMA + BBands",
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


layout = dbc.Container(
    fluid=True,
    children=[
        dbc.Card(
            style={
                "backgroundColor": "#212529",
                "color": "#ffffff",
                "border": "1px solid #f8f9fa",
            },
            children=[
                dbc.CardHeader(
                    style={
                        "backgroundColor": "#212529",
                        "borderBottom": "2px solid #f8f9fa",
                    },
                    children=dbc.Row(
                        [
                            dbc.Col(
                                html.H3(
                                    "Technical Analysis", style={"color": "#ffffff"}
                                )
                            ),
                            dbc.Col(
                                dcc.Dropdown(
                                    id="asset-select",
                                    options=[
                                        {"label": "IAU", "value": "IAU US Equity"},
                                        {"label": "SPY", "value": "SPY US Equity"},
                                    ],
                                    value="IAU US Equity",
                                    style={
                                        "backgroundColor": "#343a40",
                                        "color": "#ffffff",
                                    },
                                )
                            ),
                            dbc.Col(
                                dcc.DatePickerSingle(
                                    id="start-date",
                                    date=(datetime.now() - timedelta(days=365)).date(),
                                    display_format="YYYY-MM-DD",
                                    style={
                                        "backgroundColor": "#343a40",
                                        "color": "#ffffff",
                                        "border": "1px solid #f8f9fa",
                                    },
                                )
                            ),
                            dbc.Col(
                                dcc.DatePickerSingle(
                                    id="end-date",
                                    date=datetime.now().date(),
                                    display_format="YYYY-MM-DD",
                                    style={
                                        "backgroundColor": "#343a40",
                                        "color": "#ffffff",
                                        "border": "1px solid #f8f9fa",
                                    },
                                )
                            ),
                        ]
                    ),
                ),
                dbc.CardBody(
                    style={"backgroundColor": "#212529", "color": "#ffffff"},
                    children=[
                        dcc.Loading(
                            id="loading-performance-graphs",
                            type="default",
                            children=[
                                dbc.Row(
                                    dbc.Col(
                                        dcc.Graph(
                                            id="sm-chart",
                                            config={"displayModeBar": False},
                                        )
                                    )
                                ),
                                dbc.Row(
                                    dbc.Col(
                                        dcc.Graph(
                                            id="rsi-chart",
                                            config={"displayModeBar": False},
                                        )
                                    )
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        ),
    ],
)
