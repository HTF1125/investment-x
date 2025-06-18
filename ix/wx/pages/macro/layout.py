from dash import html, dcc, register_page, callback, ctx, MATCH
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from dash.dependencies import Input, Output, State
from ix.wx.pages.macro.charts import *

register_page(__name__, path="/macro", title="Macro", name="Macro")

# Blank figure for placeholders
blank_fig = go.Figure()
blank_fig.update_layout(
    template="plotly_dark",
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    xaxis=dict(showgrid=False, zeroline=False, visible=False),
    yaxis=dict(showgrid=False, zeroline=False, visible=False),
)

# Chart configurations
chart_configs = [
    {"key": "sp500", "label": "S&P500", "plot_func": PMI_SP500_YoY},
    {"key": "treasury10y", "label": "Treasury 10Y", "plot_func": PMI_Treasury10Y_YoY},
    {"key": "wti", "label": "WTI", "plot_func": PMI_WTI_YoY},
    {
        "key": "usoecdclisp500",
        "label": "US OECD CLI vs S&P500",
        "plot_func": US_OECD_CLI_SP500,
    },
]

CHARTS_PER_PAGE = 4

# Layout
layout = dbc.Container(
    fluid=True,
    className="p-3",
    style={"backgroundColor": "#111111", "minHeight": "100vh"},
    children=[
        html.H2(
            "Macro Dashboard", className="text-center mb-4", style={"color": "#fff"}
        ),
        html.Div(id="charts-container"),
        dbc.Row(
            [
                dbc.Col(
                    dbc.Button(
                        "Previous",
                        id="prev-page",
                        color="secondary",
                        className="me-2",
                        n_clicks=0,
                        disabled=True,
                        style={"minWidth": "100px"},
                    ),
                    width="auto",
                ),
                dbc.Col(
                    html.Div(
                        id="page-indicator",
                        className="text-white fw-bold",
                        style={"paddingTop": "8px"},
                    ),
                    width="auto",
                ),
                dbc.Col(
                    dbc.Button(
                        "Next",
                        id="next-page",
                        color="secondary",
                        n_clicks=0,
                        style={"minWidth": "100px"},
                    ),
                    width="auto",
                ),
            ],
            justify="center",
            className="mt-2",
        ),
        dcc.Store(id="current-page", data=0),
    ],
)


# Pagination and chart rendering callback
@callback(
    Output("charts-container", "children"),
    Output("current-page", "data"),
    Output("prev-page", "disabled"),
    Output("next-page", "disabled"),
    Output("page-indicator", "children"),
    Input("prev-page", "n_clicks"),
    Input("next-page", "n_clicks"),
    State("current-page", "data"),
)
def update_charts(prev_clicks, next_clicks, current_page):
    triggered = ctx.triggered_id
    num_pages = (len(chart_configs) - 1) // CHARTS_PER_PAGE + 1
    if triggered == "next-page" and current_page < num_pages - 1:
        current_page += 1
    elif triggered == "prev-page" and current_page > 0:
        current_page -= 1
    start = current_page * CHARTS_PER_PAGE
    end = start + CHARTS_PER_PAGE
    charts_to_show = chart_configs[start:end]

    # Responsive grid: 2 charts per row on md+, 1 per row on xs
    rows = []
    for i in range(0, len(charts_to_show), 2):
        row = dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        [
                            dbc.CardHeader(
                                charts_to_show[j]["label"],
                                className="text-center fw-bold",
                                style={"backgroundColor": "#222", "color": "#fff"},
                            ),
                            dbc.CardBody(
                                dcc.Loading(
                                    dcc.Graph(
                                        id={
                                            "type": "chart",
                                            "index": charts_to_show[j]["key"],
                                        },
                                        figure=blank_fig,
                                        config={"displayModeBar": False},
                                        style={"width": "100%", "height": "350px"},
                                    ),
                                    type="circle",
                                    color="#888888",
                                )
                            ),
                        ],
                        style={
                            "backgroundColor": "#222222",
                            "borderRadius": "8px",
                            "boxShadow": "0 2px 8px rgba(0,0,0,0.5)",
                            "marginBottom": "20px",
                        },
                    ),
                    width=12 if len(charts_to_show) == 1 else 6,
                )
                for j in range(i, min(i + 2, len(charts_to_show)))
            ],
            justify="start",
            align="stretch",
            className="mb-3",
        )
        rows.append(row)

    prev_disabled = current_page == 0
    next_disabled = current_page >= num_pages - 1
    page_indicator = f"Page {current_page + 1} of {num_pages}"
    return rows, current_page, prev_disabled, next_disabled, page_indicator


# Chart update callback
@callback(
    Output({"type": "chart", "index": MATCH}, "figure"),
    Input({"type": "chart", "index": MATCH}, "id"),
)
def update_chart(id):
    key = id["index"]
    config = next((c for c in chart_configs if c["key"] == key), None)
    if config is None or "plot_func" not in config:
        return blank_fig
    try:
        fig = config["plot_func"]()
        return fig
    except Exception as e:
        error_fig = go.Figure()
        error_fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            annotations=[
                dict(
                    text=f"Error loading chart: {str(e)}",
                    x=0.5,
                    y=0.5,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(color="red", size=16),
                )
            ],
        )
        return error_fig
