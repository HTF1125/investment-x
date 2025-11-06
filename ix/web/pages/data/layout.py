# layout.py
from dash import html, dcc, Input, Output, State, callback, ALL, dash_table
from dash.exceptions import PreventUpdate
import json
import pandas as pd
from ix.db import models
import dash_mantine_components as dmc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from ix.misc import get_logger
from dash_iconify import DashIconify
import dash
from ix.web.pages.data import modal

# Register Page
dash.register_page(__name__, path="/data", title="Data", name="Data")

logger = get_logger(__name__)

# Header component
header = dmc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    [
                        dmc.Title(
                            "📊 Timeseries",
                            order=1,
                            style={
                                "color": "var(--text-primary)",
                                "marginBottom": "8px",
                                "fontSize": "1rem",
                                "fontWeight": "700",
                            },
                        ),
                        dmc.Text(
                            "Manage and analyze your financial data",
                            c="gray",
                            size="md",
                        ),
                    ],
                    md=8,
                ),
                dbc.Col(
                    [
                        dmc.Group(
                            [
                                dmc.Button(
                                    [
                                        dmc.ThemeIcon(
                                            DashIconify(
                                                icon="material-symbols:download"
                                            ),
                                            size="sm",
                                            variant="light",
                                        ),
                                        "Download Template",
                                    ],
                                    id="download-template-btn",
                                    variant="outline",
                                    color="gray",
                                    size="md",
                                    style={"height": "40px"},
                                ),
                                dmc.Button(
                                    [
                                        dmc.ThemeIcon(
                                            DashIconify(icon="material-symbols:add"),
                                            size="sm",
                                            variant="light",
                                        ),
                                        "New",
                                    ],
                                    id="create-btn",
                                    variant="filled",
                                    color="blue",
                                    size="md",
                                    style={"height": "40px"},
                                ),
                            ],
                            gap="sm",
                        ),
                    ],
                    md=4,
                    style={
                        "display": "flex",
                        "justifyContent": "flex-end",
                        "alignItems": "center",
                    },
                ),
            ],
            style={"marginBottom": "24px"},
        ),
    ],
    size="xl",
    px="md",
)

# Search and filters
controls = dmc.Container(
    [
        dmc.Paper(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dmc.TextInput(
                                    id="search",
                                    placeholder="Search timeseries...",
                                    leftSection=DashIconify(
                                        icon="material-symbols:search"
                                    ),
                                    size="md",
                                    style={"width": "100%"},
                                ),
                            ],
                            md=12,
                        ),
                    ],
                    style={"marginBottom": "0"},
                ),
            ],
            p="md",
            radius="md",
            shadow="sm",
            style={"marginBottom": "24px"},
        ),
    ],
    size="xl",
    px="md",
)

# Data table container
data_container = dmc.Container(
    [
        dmc.Paper(
            [
                dmc.Divider(
                    id="stats-bar",
                    label="Loading...",
                    size="sm",
                    style={"marginBottom": "16px"},
                ),
                dmc.ScrollArea(
                    html.Div(id="timeseries-grid"), style={"height": "600px"}
                ),
                dmc.Divider(
                    size="sm", style={"marginTop": "16px", "marginBottom": "16px"}
                ),
                dmc.Center(
                    dmc.Pagination(
                        id="pagination", total=1, value=1, size="sm", withEdges=True
                    )
                ),
            ],
            p="md",
            radius="md",
            shadow="sm",
        ),
    ],
    size="xl",
    px="md",
)


# Create modal
create_modal = dbc.Modal(
    [
        dbc.ModalHeader(
            dmc.Title("Create New Timeseries", order=3),
        ),
        dbc.ModalBody(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dmc.TextInput(
                                    id="new-code",
                                    label="Code",
                                    placeholder="e.g., AAPL",
                                    size="md",
                                ),
                            ],
                            md=6,
                        ),
                        dbc.Col(
                            [
                                dmc.TextInput(
                                    id="new-name",
                                    label="Name",
                                    placeholder="e.g., Apple Inc.",
                                    size="md",
                                ),
                            ],
                            md=6,
                        ),
                    ],
                    style={"marginBottom": "16px"},
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                dbc.Label("Asset Class", className="form-label"),
                                dbc.Select(
                                    id="new-class",
                                    options=[
                                        {"label": "Equity", "value": "equity"},
                                        {"label": "Bond", "value": "bond"},
                                        {"label": "Commodity", "value": "commodity"},
                                    ],
                                    size="md",
                                ),
                            ],
                            md=6,
                        ),
                        dbc.Col(
                            [
                                dbc.Label("Frequency", className="form-label"),
                                dbc.Select(
                                    id="new-freq",
                                    options=[
                                        {"label": "Daily", "value": "daily"},
                                        {"label": "Weekly", "value": "weekly"},
                                        {"label": "Monthly", "value": "monthly"},
                                    ],
                                    size="md",
                                ),
                            ],
                            md=6,
                        ),
                    ],
                    style={"marginBottom": "16px"},
                ),
            ],
        ),
        dbc.ModalFooter(
            [
                dmc.Button(
                    "Cancel",
                    id="cancel-create",
                    variant="outline",
                    color="gray",
                ),
                dmc.Button(
                    "Create",
                    id="save-create",
                    variant="filled",
                    color="blue",
                ),
            ],
            style={"justifyContent": "flex-end", "gap": "8px"},
        ),
    ],
    id="create-modal",
    centered=True,
)

# Main layout
layout = html.Div(
    [
        # Components
        header,
        controls,
        data_container,
        modal.layout,
        create_modal,
        html.Div(
            id="notifications",
            style={"position": "fixed", "top": "20px", "right": "20px", "zIndex": 1000},
        ),
        # Data stores
        dcc.Store(id="selected-ts"),
        dcc.Store(id="page-data"),
        # Hidden download component
        dcc.Download(id="download-template-file"),
    ],
    style={
        "minHeight": "100vh",
        "backgroundColor": "var(--bg-primary)",
        "color": "var(--text-primary)",
        "fontFamily": "Inter, sans-serif",
    },
)


# =============================================================================
# CALLBACKS
# =============================================================================


@callback(
    Output("download-template-file", "data"),
    Input("download-template-btn", "n_clicks"),
    prevent_initial_call=True,
)
def download_template(n_clicks):
    """Handle template download"""
    if not n_clicks:
        raise PreventUpdate

    import base64
    import os

    # Get the file path
    file_path = os.path.join("ix", "Data.xlsm")

    if os.path.exists(file_path):
        # Read the file and encode it
        with open(file_path, "rb") as file:
            file_content = file.read()
            encoded_content = base64.b64encode(file_content).decode()

        return dict(
            content=encoded_content,
            filename="Data.xlsm",
            type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            base64=True,
        )
    else:
        raise PreventUpdate


def format_number(num):
    """Format large numbers with K, M suffixes"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(num)


def create_timeseries_card(ts):
    """Create a simple card for timeseries - accepts dict or Timeseries object"""
    # Handle both dict and object
    if isinstance(ts, dict):
        code = ts.get('code', '')
        name = ts.get('name', 'Unnamed')
        asset_class = ts.get('asset_class', 'Unknown')
        num_data = ts.get('num_data', 0)
        start = ts.get('start')
        frequency = ts.get('frequency', 'Unknown')
    else:
        code = ts.code
        name = ts.name or "Unnamed"
        asset_class = ts.asset_class or "Unknown"
        num_data = ts.num_data or 0
        start = ts.start
        frequency = ts.frequency or "Unknown"

    start_str = start.strftime('%Y-%m-%d') if start and hasattr(start, 'strftime') else (str(start) if start else 'N/A')

    return html.Div(
        dmc.Card(
            [
                dmc.CardSection(
                    [
                        dmc.Group(
                            [
                                dmc.Group(
                                    [
                                        dmc.Title(
                                            code, order=4, style={"margin": 0}
                                        ),
                                        dmc.Text(
                                            name,
                                            size="sm",
                                            c="gray",
                                            style={"margin": 0},
                                        ),
                                    ],
                                    style={"flex": 1},
                                ),
                                dmc.Group(
                                    [
                                        dmc.Badge(
                                            asset_class,
                                            color="blue",
                                            variant="light",
                                        ),
                                        dmc.Badge(
                                            f"{format_number(num_data)} pts",
                                            color="gray",
                                            variant="outline",
                                        ),
                                    ],
                                    gap="xs",
                                ),
                            ],
                            justify="space-between",
                            align="flex-start",
                            style={"marginBottom": "12px"},
                        ),
                        dmc.Divider(size="xs", style={"marginBottom": "12px"}),
                        dmc.Group(
                            [
                                dmc.Text(
                                    f"📅 {start_str}",
                                    size="xs",
                                    c="gray",
                                ),
                                dmc.Text(
                                    f"🔄 {frequency}",
                                    size="xs",
                                    c="gray",
                                ),
                            ],
                            gap="md",
                        ),
                    ],
                    p="md",
                ),
            ],
            shadow="sm",
            radius="md",
            style={
                "height": "100%",
            },
        ),
        style={
            "cursor": "pointer",
            "transition": "transform 0.2s, box-shadow 0.2s",
        },
        id={"type": "ts-card", "index": code},
    )


@callback(
    [
        Output("timeseries-grid", "children"),
        Output("stats-bar", "label"),
        Output("pagination", "total"),
    ],
    [
        Input("search", "value"),
        Input("pagination", "value"),
    ],
)
def update_timeseries_list(search, current_page):
    if current_page is None:
        current_page = 1

    # Query database using SQLAlchemy
    from ix.db.conn import Session
    from ix.db.models import Timeseries

    with Session() as session:
        if search:
            search_pattern = f"%{search.lower()}%"
            query = session.query(Timeseries).filter(
                (Timeseries.code.ilike(search_pattern)) |
                (Timeseries.name.ilike(search_pattern))
            )
        else:
            query = session.query(Timeseries)

        # Get all results and extract attributes while in session
        timeseries_list = query.all()
        filtered = []
        for ts in timeseries_list:
            filtered.append({
                'id': ts.id,
                'code': ts.code,
                'name': ts.name,
                'provider': ts.provider,
                'asset_class': ts.asset_class,
                'category': ts.category,
                'source': ts.source,
                'frequency': ts.frequency,
                'start': ts.start,
                'end': ts.end,
                'num_data': ts.num_data,
            })

    # Sort by code
    filtered.sort(key=lambda x: x.get('code', '') or "")

    total_count = len(filtered)
    total_pages = max(1, (total_count + 50 - 1) // 50)

    # Paginate
    start_idx = (current_page - 1) * 50
    page_items = filtered[start_idx : start_idx + 50]

    # Create grid
    if page_items:
        grid = dbc.Row(
            [
                dbc.Col(
                    create_timeseries_card(ts),
                    lg=4,
                    md=6,
                    style={"marginBottom": "16px"},
                )
                for ts in page_items
            ],
            className="g-3",
        )
    else:
        grid = dmc.Center(
            [
                dmc.Stack(
                    [
                        DashIconify(
                            icon="material-symbols:chart-line",
                            width=60,
                            color="var(--mantine-color-gray-5)",
                        ),
                        dmc.Title("No timeseries found", order=3, c="gray"),
                        dmc.Text(
                            "Try adjusting your search or filters",
                            c="gray",
                            size="sm",
                        ),
                    ],
                    align="center",
                    gap="md",
                ),
            ],
            style={"height": "300px"},
        )

    # Stats bar
    stats_label = f"Showing {len(page_items)} of {total_count:,} timeseries"

    return grid, stats_label, total_pages


@callback(
    [Output("detail-modal", "opened"), Output("selected-ts", "data")],
    [Input({"type": "ts-card", "index": ALL}, "n_clicks")],
    prevent_initial_call=True,
)
def open_detail_modal(clicks):
    if not any(clicks or []):
        raise PreventUpdate

    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    # Get clicked card ID
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    ts_id = json.loads(button_id)["index"]

    return True, ts_id


@callback(
    [
        Output("modal-header", "children"),
        Output("tab-overview", "children"),
        Output("tab-details", "children"),
        Output("chart", "figure"),
        Output("tab-data", "children"),
    ],
    [Input("selected-ts", "data")],
    prevent_initial_call=True,
)
def load_modal_content(ts_code):
    if not ts_code:
        raise PreventUpdate

    # Get timeseries by code using SQLAlchemy
    from ix.db.conn import Session
    from ix.db.models import Timeseries

    with Session() as session:
        ts = session.query(Timeseries).filter(Timeseries.code == ts_code).first()
        if not ts:
            return "Not found", "Error", "Error", {}, "Error"

        # Extract all needed attributes while in session
        ts_code = ts.code
        ts_name = ts.name
        ts_provider = ts.provider
        ts_asset_class = ts.asset_class
        ts_category = ts.category
        ts_source = ts.source
        ts_source_code = ts.source_code
        ts_frequency = ts.frequency
        ts_unit = ts.unit
        ts_scale = ts.scale
        ts_currency = ts.currency
        ts_country = ts.country
        ts_start = ts.start
        ts_end = ts.end
        ts_num_data = ts.num_data
        ts_remark = ts.remark
        # Get data within session
        ts_data = ts.data.copy() if hasattr(ts, 'data') else pd.Series()

    # Header
    header = [
        dmc.Title(ts_code, order=2, style={"margin": 0}),
        dmc.Text(ts_name or "Unnamed", c="gray", size="sm"),
    ]

    # Overview tab - Basic info
    overview = dbc.Row(
        [
            dbc.Col(
                [
                    dmc.Title(
                        "Basic Information", order=4, style={"marginBottom": "12px"}
                    ),
                    dmc.Stack(
                        [
                            dmc.Text(
                                [
                                    dmc.Text("Code: ", fw="bold"),
                                    ts_code or "N/A",
                                ]
                            ),
                            dmc.Text(
                                [
                                    dmc.Text("Name: ", fw="bold"),
                                    ts_name or "N/A",
                                ]
                            ),
                            dmc.Text(
                                [
                                    dmc.Text("Provider: ", fw="bold"),
                                    ts_provider or "N/A",
                                ]
                            ),
                            dmc.Text(
                                [
                                    dmc.Text("Asset Class: ", fw="bold"),
                                    ts_asset_class or "N/A",
                                ]
                            ),
                            dmc.Text(
                                [
                                    dmc.Text("Category: ", fw="bold"),
                                    ts_category or "N/A",
                                ]
                            ),
                        ],
                        gap="xs",
                    ),
                ],
                md=4,
            ),
            dbc.Col(
                [
                    dmc.Title(
                        "Data Statistics", order=4, style={"marginBottom": "12px"}
                    ),
                    dmc.Stack(
                        [
                            dmc.Text(
                                [
                                    dmc.Text("Data Points: ", fw="bold"),
                                    f"{ts_num_data or 0:,}",
                                ]
                            ),
                            dmc.Text(
                                [
                                    dmc.Text("Start Date: ", fw="bold"),
                                    (
                                        ts_start.strftime("%Y-%m-%d")
                                        if ts_start
                                        else "N/A"
                                    ),
                                ]
                            ),
                            dmc.Text(
                                [
                                    dmc.Text("End Date: ", fw="bold"),
                                    (ts_end.strftime("%Y-%m-%d") if ts_end else "N/A"),
                                ]
                            ),
                            dmc.Text(
                                [
                                    dmc.Text("Frequency: ", fw="bold"),
                                    ts_frequency or "N/A",
                                ]
                            ),
                            dmc.Text(
                                [
                                    dmc.Text("Unit: ", fw="bold"),
                                    ts_unit or "N/A",
                                ]
                            ),
                        ],
                        gap="xs",
                    ),
                ],
                md=4,
            ),
            dbc.Col(
                [
                    dmc.Title(
                        "Location & Scale", order=4, style={"marginBottom": "12px"}
                    ),
                    dmc.Stack(
                        [
                            dmc.Text(
                                [
                                    dmc.Text("Currency: ", fw="bold"),
                                    ts_currency or "N/A",
                                ]
                            ),
                            dmc.Text(
                                [
                                    dmc.Text("Country: ", fw="bold"),
                                    ts_country or "N/A",
                                ]
                            ),
                            dmc.Text(
                                [
                                    dmc.Text("Scale: ", fw="bold"),
                                    (str(ts_scale) if ts_scale is not None else "N/A"),
                                ]
                            ),
                            dmc.Text(
                                [
                                    dmc.Text("Timeseries Code: ", fw="bold"),
                                    str(ts_code),
                                ]
                            ),
                            dmc.Text(
                                [
                                    dmc.Text("Source Code: ", fw="bold"),
                                    ts_source_code or "N/A",
                                ]
                            ),
                        ],
                        gap="xs",
                    ),
                ],
                md=4,
            ),
        ],
    )

    # Details tab - All attributes
    details = dbc.Row(
        [
            dbc.Col(
                [
                    dmc.Title(
                        "Source & Metadata", order=4, style={"marginBottom": "12px"}
                    ),
                    dmc.Stack(
                        [
                            dmc.Text(
                                [
                                    dmc.Text("Source: ", fw="bold"),
                                    ts_source or "N/A",
                                ]
                            ),
                            dmc.Text(
                                [
                                    dmc.Text("Source Code: ", fw="bold"),
                                    ts_source_code or "N/A",
                                ]
                            ),
                            dmc.Text(
                                [
                                    dmc.Text("Provider: ", fw="bold"),
                                    ts_provider or "N/A",
                                ]
                            ),
                            dmc.Text(
                                [
                                    dmc.Text("Asset Class: ", fw="bold"),
                                    ts_asset_class or "N/A",
                                ]
                            ),
                            dmc.Text(
                                [
                                    dmc.Text("Category: ", fw="bold"),
                                    ts_category or "N/A",
                                ]
                            ),
                        ],
                        gap="xs",
                    ),
                ],
                md=4,
            ),
            dbc.Col(
                [
                    dmc.Title(
                        "Data & Technical",
                        order=4,
                        style={"marginBottom": "12px"},
                    ),
                    dmc.Stack(
                        [
                            dmc.Text(
                                [
                                    dmc.Text("Data Points: ", fw="bold"),
                                    f"{ts_num_data or 0:,}",
                                ]
                            ),
                            dmc.Text(
                                [
                                    dmc.Text("Start Date: ", fw="bold"),
                                    (
                                        ts_start.strftime("%Y-%m-%d")
                                        if ts_start
                                        else "N/A"
                                    ),
                                ]
                            ),
                            dmc.Text(
                                [
                                    dmc.Text("End Date: ", fw="bold"),
                                    (ts_end.strftime("%Y-%m-%d") if ts_end else "N/A"),
                                ]
                            ),
                            dmc.Text(
                                [
                                    dmc.Text("Frequency: ", fw="bold"),
                                    ts_frequency or "N/A",
                                ]
                            ),
                            dmc.Text(
                                [
                                    dmc.Text("Unit: ", fw="bold"),
                                    ts_unit or "N/A",
                                ]
                            ),
                        ],
                        gap="xs",
                    ),
                ],
                md=4,
            ),
            dbc.Col(
                [
                    dmc.Title(
                        "Location & Relationships",
                        order=4,
                        style={"marginBottom": "12px"},
                    ),
                    dmc.Stack(
                        [
                            dmc.Text(
                                [
                                    dmc.Text("Currency: ", fw="bold"),
                                    ts_currency or "N/A",
                                ]
                            ),
                            dmc.Text(
                                [
                                    dmc.Text("Country: ", fw="bold"),
                                    ts_country or "N/A",
                                ]
                            ),
                            dmc.Text(
                                [
                                    dmc.Text("Scale: ", fw="bold"),
                                    (str(ts_scale) if ts_scale is not None else "N/A"),
                                ]
                            ),
                            dmc.Text(
                                [
                                    dmc.Text("Remark: ", fw="bold"),
                                    ts_remark or "N/A",
                                ]
                            ),
                        ],
                        gap="xs",
                    ),
                ],
                md=4,
            ),
        ],
    )

    # Chart
    data = ts_data
    df = data.dropna().reset_index()
    # Ensure we have proper column names
    if len(df.columns) == 2:
        df.columns = ["date", "value"]
    else:
        # If more columns, use the first as date and second as value
        df.columns = ["date", "value"] + list(df.columns[2:])

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df["date"],
            y=df["value"],
            mode="lines",
            name=ts_code,
            line=dict(color="#3b82f6", width=2),
        )
    )
    fig.update_layout(
        title=f"{ts_code} Time Series",
        xaxis_title="Date",
        yaxis_title="Value",
        height=400,
        margin=dict(l=0, r=0, t=30, b=0),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="var(--text-primary)"),
        xaxis=dict(color="var(--text-primary)"),
        yaxis=dict(color="var(--text-primary)"),
    )

    # Data table
    df_display = df.head(100).copy()
    # Use the actual column names from the dataframe
    df_display.columns = ["Date", "Value"] + (
        list(df_display.columns[2:]) if len(df_display.columns) > 2 else []
    )
    table = dash_table.DataTable(
        data=df_display.to_dict("records"),
        columns=[{"name": i, "id": i} for i in df_display.columns],
        style_table={"height": "400px", "overflowY": "auto"},
        style_cell={
            "textAlign": "left",
            "padding": "10px",
            "backgroundColor": "var(--bg-secondary)",
            "color": "var(--text-primary)",
        },
        style_header={
            "backgroundColor": "var(--bg-primary)",
            "fontWeight": "bold",
            "color": "var(--text-primary)",
        },
        page_size=50,
    )

    return header, overview, details, fig, table


@callback(
    Output("detail-modal", "opened", allow_duplicate=True),
    Input("close-modal", "n_clicks"),
    prevent_initial_call=True,
)
def close_modal(n_clicks):
    return False


@callback(
    Output("create-modal", "is_open"),
    [
        Input("create-btn", "n_clicks"),
        Input("cancel-create", "n_clicks"),
        Input("save-create", "n_clicks"),
    ],
    prevent_initial_call=True,
)
def toggle_create_modal(create_clicks, cancel_clicks, save_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]
    return trigger == "create-btn"


@callback(
    Output("notifications", "children", allow_duplicate=True),
    [Input("save-create", "n_clicks")],
    [
        State("new-code", "value"),
        State("new-name", "value"),
        State("new-class", "value"),
        State("new-freq", "value"),
    ],
    prevent_initial_call=True,
)
def create_timeseries(n_clicks, code, name, asset_class, frequency):
    if not n_clicks or not code:
        raise PreventUpdate

    try:
        # Create new timeseries
        # Here you would implement the actual database save logic for empty timeseries
        message = f"Timeseries '{code}' created successfully!"

        return dmc.Notification(
            title="Success",
            message=message,
            color="green",
            icon=DashIconify(icon="material-symbols:check-circle"),
            id="success-notification",
            action="show",
            autoClose=4000,
        )
    except Exception as e:
        return dmc.Notification(
            title="Error",
            message=f"Error creating timeseries: {e}",
            color="red",
            icon=DashIconify(icon="material-symbols:error"),
            id="error-notification",
            action="show",
            autoClose=4000,
        )
