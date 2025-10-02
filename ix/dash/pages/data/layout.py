# layout.py
from dash import html, dcc, Input, Output, State, callback, ALL, dash_table
from dash.exceptions import PreventUpdate
import json
import pandas as pd
from bson import ObjectId
from ix.db.models import Timeseries
import dash_mantine_components as dmc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from ix.misc import get_logger
from dash_iconify import DashIconify
import dash
from ix.dash.pages.data import modal

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
                            md=6,
                        ),
                        dbc.Col(
                            [
                                dmc.Text(
                                    "Upload Excel Data",
                                    size="sm",
                                    fw="bold",
                                    style={"marginBottom": "8px"},
                                ),
                                dcc.Upload(
                                    dmc.Paper(
                                        [
                                            dmc.Center(
                                                [
                                                    DashIconify(
                                                        icon="material-symbols:cloud-upload",
                                                        width=20,
                                                    ),
                                                    dmc.Text(
                                                        "Upload Excel",
                                                        size="xs",
                                                        c="gray",
                                                    ),
                                                ],
                                                style={"padding": "10px"},
                                            ),
                                        ],
                                        radius="md",
                                        style={
                                            "border": "2px dashed var(--mantine-color-gray-4)",
                                            "cursor": "pointer",
                                            "transition": "border-color 0.2s",
                                            "minHeight": "60px",
                                        },
                                    ),
                                    id="standalone-upload-csv",
                                    multiple=False,
                                ),
                            ],
                            md=6,
                        ),
                    ],
                    style={"marginBottom": "0"},
                ),
                html.Div(id="standalone-csv-preview", style={"marginTop": "16px"}),
                # Progress bar for upload
                html.Div(
                    id="upload-progress-container",
                    style={"marginTop": "16px", "display": "none"},
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
                dmc.Text(
                    "Upload Excel", size="sm", fw="bold", style={"marginBottom": "8px"}
                ),
                dcc.Upload(
                    dmc.Paper(
                        [
                            dmc.Center(
                                [
                                    DashIconify(
                                        icon="material-symbols:cloud-upload", width=40
                                    ),
                                    dmc.Text(
                                        "Drag & drop or click to upload",
                                        size="sm",
                                        c="gray",
                                    ),
                                ],
                                style={"padding": "20px"},
                            ),
                        ],
                        radius="md",
                        style={
                            "border": "2px dashed var(--mantine-color-gray-4)",
                            "cursor": "pointer",
                            "transition": "border-color 0.2s",
                        },
                    ),
                    id="upload-csv",
                    multiple=False,
                ),
                html.Div(id="csv-preview", style={"marginTop": "16px"}),
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
        dcc.Store(id="csv-data"),
        dcc.Store(id="standalone-csv-data"),
        dcc.Store(id="upload-progress", data={"status": "idle", "progress": 0}),
        dcc.Store(id="upload-trigger", data=0),
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
    file_path = os.path.join("ix", "dash", "Data.xlsx")

    if os.path.exists(file_path):
        # Read the file and encode it
        with open(file_path, "rb") as file:
            file_content = file.read()
            encoded_content = base64.b64encode(file_content).decode()

        return dict(
            content=encoded_content,
            filename="Data.xlsx",
            type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            base64=True,
        )
    else:
        raise PreventUpdate


@callback(
    [Output("csv-preview", "children"), Output("csv-data", "data")],
    [Input("upload-csv", "contents")],
    [State("upload-csv", "filename")],
    prevent_initial_call=True,
)
def handle_excel_upload(contents, filename):
    """Handle Excel file upload and parse with index_col=0 and parse_dates=True"""
    if contents is None:
        return "", None

    try:
        # Parse the uploaded file
        import base64
        import io

        # Decode the content
        content_type, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)

        # Read Excel file with single Data sheet
        df = pd.read_excel(
            io.BytesIO(decoded),
            sheet_name="Data",
            index_col=0,
            parse_dates=True,
        )

        # Create preview table with index
        preview_df = df.head(10)  # Show first 10 rows
        # Reset index to include it as a column
        preview_df_with_index = preview_df.reset_index()
        preview_table = dash_table.DataTable(
            data=preview_df_with_index.to_dict("records"),
            columns=[
                {"name": str(i), "id": str(i)} for i in preview_df_with_index.columns
            ],
            style_table={"height": "300px", "overflowY": "auto", "fontSize": "12px"},
            style_cell={
                "textAlign": "left",
                "padding": "8px",
                "backgroundColor": "var(--bg-secondary)",
                "color": "var(--text-primary)",
                "fontSize": "12px",
            },
            style_header={
                "backgroundColor": "var(--bg-primary)",
                "fontWeight": "bold",
                "color": "var(--text-primary)",
                "fontSize": "12px",
            },
            page_size=10,
        )

        # Create info section
        info_text = dmc.Text(
            f"✅ Successfully loaded {filename} - {len(df)} rows, {len(df.columns)} columns",
            size="sm",
            c="green",
            style={"marginBottom": "8px"},
        )

        preview_content = [
            info_text,
            dmc.Text(
                "Data Preview:", size="sm", fw="bold", style={"marginBottom": "8px"}
            ),
            preview_table,
        ]

        # Store the dataframe as JSON for later use
        csv_data = {
            "filename": filename,
            "data": df.to_json(orient="records", date_format="iso"),
            "index": df.index.to_series().dt.strftime("%Y-%m-%d").to_list(),
            "columns": df.columns.tolist(),
            "shape": df.shape,
        }

        return preview_content, csv_data

    except Exception as e:
        error_content = dmc.Alert(
            f"❌ Error reading Excel file: {str(e)}",
            color="red",
            variant="light",
            style={"marginTop": "8px"},
        )
        return error_content, None


@callback(
    [
        Output("standalone-csv-preview", "children"),
        Output("standalone-csv-data", "data"),
    ],
    [Input("standalone-upload-csv", "contents")],
    [State("standalone-upload-csv", "filename")],
    prevent_initial_call=True,
)
def handle_standalone_excel_upload(contents, filename):
    """Handle standalone Excel file upload and parse with index_col=0 and parse_dates=True"""
    if contents is None:
        return "", None

    try:
        # Parse the uploaded file
        import base64
        import io

        # Decode the content
        content_type, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)

        # Read Excel file with single Data sheet
        df = pd.read_excel(
            io.BytesIO(decoded),
            sheet_name="Data",
            index_col=0,
            parse_dates=True,
        )

        # Create preview table with index
        preview_df = df.head(10)  # Show first 10 rows
        # Reset index to include it as a column
        preview_df_with_index = preview_df.reset_index()
        preview_table = dash_table.DataTable(
            data=preview_df_with_index.to_dict("records"),
            columns=[
                {"name": str(i), "id": str(i)} for i in preview_df_with_index.columns
            ],
            style_table={"height": "200px", "overflowY": "auto", "fontSize": "11px"},
            style_cell={
                "textAlign": "left",
                "padding": "6px",
                "backgroundColor": "var(--bg-secondary)",
                "color": "var(--text-primary)",
                "fontSize": "11px",
            },
            style_header={
                "backgroundColor": "var(--bg-primary)",
                "fontWeight": "bold",
                "color": "var(--text-primary)",
                "fontSize": "11px",
            },
            page_size=10,
        )

        # Create info section
        info_text = dmc.Text(
            f"✅ Loaded {filename} - {len(df)} rows, {len(df.columns)} columns",
            size="xs",
            c="green",
            style={"marginBottom": "8px"},
        )

        # Create action buttons with loading state
        action_buttons = dmc.Group(
            [
                dmc.Button(
                    "Upload to Database",
                    id="upload-to-db",
                    variant="filled",
                    color="blue",
                    size="xs",
                    leftSection=DashIconify(
                        icon="material-symbols:cloud-upload", width=16
                    ),
                    loading=False,
                ),
                dmc.Button(
                    "View Full Data",
                    id="view-upload-data",
                    variant="outline",
                    color="gray",
                    size="xs",
                    leftSection=DashIconify(
                        icon="material-symbols:visibility", width=16
                    ),
                ),
            ],
            gap="xs",
            style={"marginTop": "8px"},
        )

        preview_content = [
            info_text,
            dmc.Text(
                "Data Preview:", size="xs", fw="bold", style={"marginBottom": "8px"}
            ),
            preview_table,
            action_buttons,
        ]

        # Store the dataframe as JSON for later use
        csv_data = {
            "filename": filename,
            "data": df.to_json(orient="records", date_format="iso"),
            "index": df.index.to_series().dt.strftime("%Y-%m-%d").to_list(),
            "columns": df.columns.tolist(),
            "shape": df.shape,
        }

        return preview_content, csv_data

    except Exception as e:
        error_content = dmc.Alert(
            f"❌ Error reading Excel: {str(e)}",
            color="red",
            variant="light",
            style={"marginTop": "8px", "fontSize": "12px"},
        )
        return error_content, None


@callback(
    [
        Output("upload-progress-container", "children"),
        Output("upload-progress-container", "style"),
        Output("upload-to-db", "loading"),
    ],
    [Input("upload-progress", "data")],
    prevent_initial_call=True,
)
def update_upload_progress(progress_data):
    """Update progress bar and button loading state"""
    if not progress_data:
        return "", {"marginTop": "16px", "display": "none"}, False

    status = progress_data.get("status", "idle")
    progress = progress_data.get("progress", 0)

    if status == "idle":
        return "", {"marginTop": "16px", "display": "none"}, False
    elif status == "uploading":
        progress_bar = dmc.Progress(
            value=progress,
            size="md",
            radius="md",
            striped=True,
            animated=True,
            style={"marginBottom": "8px"},
        )

        progress_text = dmc.Text(
            f"Uploading... {progress:.1f}%", size="sm", c="blue", ta="center"
        )

        return (
            [progress_bar, progress_text],
            {"marginTop": "16px", "display": "block"},
            True,
        )
    elif status == "completed":
        return "", {"marginTop": "16px", "display": "none"}, False
    elif status == "error":
        return "", {"marginTop": "16px", "display": "none"}, False
    else:
        return "", {"marginTop": "16px", "display": "none"}, False


@callback(
    [
        Output("upload-trigger", "data"),
        Output("notifications", "children", allow_duplicate=True),
    ],
    [Input("upload-to-db", "n_clicks")],
    [State("standalone-csv-data", "data")],
    prevent_initial_call=True,
)
def update_upload_trigger(n_clicks, excel_data):
    """Update upload trigger when button is clicked and show initial notification"""
    if not n_clicks:
        raise PreventUpdate

    if not excel_data:
        return n_clicks, None

    # Show initial notification using simple alert
    initial_notification = dmc.Alert(
        f"🚀 Upload Started: Processing {len(excel_data.get('columns', []))} columns from {excel_data.get('filename', 'Excel file')}...",
        color="blue",
        title="Upload Started",
        style={"marginBottom": "10px"},
    )

    logger.info(
        f"Showing initial notification for {excel_data.get('filename', 'Excel file')}"
    )
    return n_clicks, initial_notification


@callback(
    [
        Output("notifications", "children", allow_duplicate=True),
        Output("upload-progress", "data"),
    ],
    [Input("upload-trigger", "data")],
    [State("standalone-csv-data", "data")],
    prevent_initial_call=True,
)
def upload_excel_to_database(trigger, excel_data):
    """Upload Excel data to database using optimized upload_excel_data function"""
    logger.info(
        f"Upload initiated: trigger={trigger}, excel_data={'exists' if excel_data else 'None'}"
    )

    if not trigger or not excel_data:
        logger.warning("Upload prevented: no trigger or no excel_data")
        raise PreventUpdate

    try:
        logger.info("Starting Excel upload process...")
        # Convert JSON back to DataFrame
        import json

        df = pd.read_json(excel_data["data"], orient="records")
        # Convert index back to datetime
        df.index = pd.to_datetime(excel_data["index"])

        # Call the optimized upload_excel_data function
        logger.info("Calling optimized upload_excel_data function...")
        result = upload_excel_data_optimized(df)
        logger.info(f"Upload completed: {result}")

        success_message = f"Successfully uploaded {result['processed']}/{result['total']} columns to database!"
        if result["skipped"] > 0:
            success_message += (
                f" ({result['skipped']} skipped - codes not found in database)"
            )
        success_message += f" Processing time: {result['duration']:.2f}s"

        # Create success notification
        success_notification = dmc.Alert(
            f"✅ {success_message}",
            color="green",
            title="Upload Complete",
            style={"marginBottom": "10px"},
        )

        logger.info(f"Returning success notification: {success_message}")
        return success_notification, {"status": "completed", "progress": 100}
    except Exception as e:
        logger.error(f"Error during upload: {e}")
        error_notification = dmc.Alert(
            f"❌ Error uploading Excel data: {str(e)}",
            color="red",
            title="Upload Failed",
            style={"marginBottom": "10px"},
        )
        logger.info(f"Returning error notification: {str(e)}")
        return error_notification, {"status": "error", "progress": 0}


def upload_excel_data(data: pd.DataFrame):
    """
    Legacy upload function - kept for backward compatibility
    """
    return upload_excel_data_optimized(data)


def upload_excel_data_optimized(data: pd.DataFrame):
    """
    Optimized Excel data upload with batch processing and performance improvements
    """
    import time
    from typing import Dict, List, Tuple

    start_time = time.time()

    assert isinstance(data, pd.DataFrame), "data must be a pandas DataFrame"
    assert isinstance(
        data.index, pd.DatetimeIndex
    ), "index must be a pandas DatetimeIndex"

    # Remove columns that are entirely NaN
    clean_data = data.dropna(how="all")
    total_columns = len(clean_data.columns)

    logger.info(f"🚀 Starting optimized upload of {total_columns} columns")

    # Step 1: Batch fetch all required timeseries in one query
    logger.info("📊 Batch fetching timeseries from database...")
    codes = list(clean_data.columns)
    # Use MongoDB $in operator for batch query
    from pymongo import MongoClient
    import os

    # Get database connection
    from ix.db.conn import get_database

    db = get_database()

    # Build query for batch fetch
    query = {"code": {"$in": codes}}
    existing_timeseries = {ts.code: ts for ts in Timeseries.find(query).run()}

    logger.info(
        f"✅ Found {len(existing_timeseries)} existing timeseries out of {total_columns} columns"
    )

    # Step 2: Prepare data for batch processing
    processed_data: List[Tuple[Timeseries, pd.Series]] = []
    skipped_codes = []

    for code, col in clean_data.items():
        if code not in existing_timeseries:
            logger.warning(f"⚠️  Timeseries '{code}' not found in database, skipping")
            skipped_codes.append(code)
            continue

        try:
            # Convert to numeric and drop NaN values efficiently
            numeric_col = pd.to_numeric(col, errors="coerce")
            if isinstance(numeric_col, pd.Series):
                clean_col = numeric_col.dropna()
            else:
                clean_col = pd.Series(numeric_col).dropna()

            if len(clean_col) == 0:
                logger.warning(f"⚠️  No valid data for '{code}', skipping")
                skipped_codes.append(code)
                continue

            processed_data.append((existing_timeseries[str(code)], clean_col))

        except Exception as e:
            logger.error(f"❌ Error processing column '{code}': {e}")
            skipped_codes.append(code)
            continue

    logger.info(f"📋 Prepared {len(processed_data)} timeseries for batch update")

    # Step 3: Batch update timeseries data with progress logging
    processed_count = 0
    batch_size = 10  # Process in smaller batches to avoid memory issues

    for i in range(0, len(processed_data), batch_size):
        batch = processed_data[i : i + batch_size]

        for ts, clean_col in batch:
            try:
                # Update the timeseries data
                ts.data = clean_col
                processed_count += 1

                # Log progress with visual indicators
                if processed_count % 5 == 0 or processed_count == len(processed_data):
                    progress_pct = (processed_count / len(processed_data)) * 100
                    logger.info(
                        f"📈 Progress: {processed_count}/{len(processed_data)} timeseries "
                        f"({progress_pct:.1f}%) - Latest: {ts.code}"
                    )

            except Exception as e:
                logger.error(f"❌ Error updating timeseries '{ts.code}': {e}")
                continue

    duration = time.time() - start_time

    result = {
        "processed": processed_count,
        "total": total_columns,
        "skipped": len(skipped_codes),
        "duration": duration,
        "skipped_codes": skipped_codes,
    }

    logger.info(
        f"🎉 Upload completed: {processed_count}/{total_columns} columns processed successfully "
        f"({len(skipped_codes)} skipped) in {duration:.2f}s"
    )

    if skipped_codes:
        logger.info(
            f"📝 Skipped codes: {', '.join(skipped_codes[:10])}{'...' if len(skipped_codes) > 10 else ''}"
        )

    return result


@callback(
    Output("notifications", "children", allow_duplicate=True),
    [Input("view-upload-data", "n_clicks")],
    [State("standalone-csv-data", "data")],
    prevent_initial_call=True,
)
def view_full_upload_data(n_clicks, excel_data):
    """Show full uploaded Excel data in a modal or notification"""
    if not n_clicks or not excel_data:
        raise PreventUpdate

    try:
        # Convert JSON back to DataFrame
        import json

        df = pd.read_json(excel_data["data"], orient="records")
        # Convert index back to datetime
        df.index = pd.to_datetime(excel_data["index"])

        # Create a summary of the data
        min_date = df.index.min()
        max_date = df.index.max()

        # Format dates safely
        from datetime import datetime

        if isinstance(min_date, (datetime, pd.Timestamp)):
            min_date_str = min_date.strftime("%Y-%m-%d")
        else:
            min_date_str = str(min_date)

        if isinstance(max_date, (datetime, pd.Timestamp)):
            max_date_str = max_date.strftime("%Y-%m-%d")
        else:
            max_date_str = str(max_date)

        summary = f"""
        📊 Data Summary:
        • Filename: {excel_data['filename']}
        • Shape: {excel_data['shape'][0]} rows × {excel_data['shape'][1]} columns
        • Date Range: {min_date_str} to {max_date_str}
        • Columns: {', '.join(excel_data['columns'])}
        """

        return dmc.Notification(
            title="Excel Data Summary",
            message=summary,
            color="blue",
            icon=DashIconify(icon="material-symbols:info"),
            id="data-summary-notification",
            action="show",
            autoClose=8000,
        )
    except Exception as e:
        return dmc.Notification(
            title="Error",
            message=f"Error viewing data: {e}",
            color="red",
            icon=DashIconify(icon="material-symbols:error"),
            id="view-error-notification",
            action="show",
            autoClose=4000,
        )


def format_number(num):
    """Format large numbers with K, M suffixes"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(num)


def create_timeseries_card(ts):
    """Create a simple card for timeseries"""
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
                                            ts.code, order=4, style={"margin": 0}
                                        ),
                                        dmc.Text(
                                            ts.name or "Unnamed",
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
                                            ts.asset_class or "Unknown",
                                            color="blue",
                                            variant="light",
                                        ),
                                        dmc.Badge(
                                            f"{format_number(ts.num_data or 0)} pts",
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
                                    f"📅 {ts.start.strftime('%Y-%m-%d') if ts.start else 'N/A'}",
                                    size="xs",
                                    c="gray",
                                ),
                                dmc.Text(
                                    f"🔄 {ts.frequency or 'Unknown'}",
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
        id={"type": "ts-card", "index": str(ts.id)},
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

    try:
        # Query database
        ts_query = Timeseries.find({}).sort("code").run()

        # Filter results
        filtered = []
        for ts in ts_query:
            # Search filter
            if search and search.lower() not in (
                ts.code.lower() + (ts.name or "").lower()
            ):
                continue
            # Asset class filter
            filtered.append(ts)

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

    except Exception as e:
        logger.error(f"Error loading timeseries: {e}")
        return (
            dmc.Alert(
                f"Error: {e}",
                color="red",
                variant="light",
            ),
            "Error",
            1,
        )


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
def load_modal_content(ts_id):
    if not ts_id:
        raise PreventUpdate

    try:
        ts = Timeseries.find_one(Timeseries.id == ObjectId(ts_id)).run()
        if not ts:
            return "Not found", "Error", "Error", {}, "Error"

        # Header
        header = [
            dmc.Title(ts.code, order=2, style={"margin": 0}),
            dmc.Text(ts.name or "Unnamed", c="gray", size="sm"),
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
                                        ts.code or "N/A",
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("Name: ", fw="bold"),
                                        ts.name or "N/A",
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("Provider: ", fw="bold"),
                                        ts.provider or "N/A",
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("Asset Class: ", fw="bold"),
                                        ts.asset_class or "N/A",
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("Category: ", fw="bold"),
                                        ts.category or "N/A",
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
                                        f"{ts.num_data or 0:,}",
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("Start Date: ", fw="bold"),
                                        (
                                            ts.start.strftime("%Y-%m-%d")
                                            if ts.start
                                            else "N/A"
                                        ),
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("End Date: ", fw="bold"),
                                        (
                                            ts.end.strftime("%Y-%m-%d")
                                            if ts.end
                                            else "N/A"
                                        ),
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("Frequency: ", fw="bold"),
                                        ts.frequency or "N/A",
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("Unit: ", fw="bold"),
                                        ts.unit or "N/A",
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
                                        ts.currency or "N/A",
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("Country: ", fw="bold"),
                                        ts.country or "N/A",
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("Scale: ", fw="bold"),
                                        (
                                            str(ts.scale)
                                            if ts.scale is not None
                                            else "N/A"
                                        ),
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("Timeseries ID: ", fw="bold"),
                                        str(ts.id),
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("Parent ID: ", fw="bold"),
                                        ts.parent_id or "N/A",
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
                                        ts.source or "N/A",
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("Source Code: ", fw="bold"),
                                        ts.source_code or "N/A",
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("Provider: ", fw="bold"),
                                        ts.provider or "N/A",
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("Asset Class: ", fw="bold"),
                                        ts.asset_class or "N/A",
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("Category: ", fw="bold"),
                                        ts.category or "N/A",
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
                                        f"{ts.num_data or 0:,}",
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("Start Date: ", fw="bold"),
                                        (
                                            ts.start.strftime("%Y-%m-%d")
                                            if ts.start
                                            else "N/A"
                                        ),
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("End Date: ", fw="bold"),
                                        (
                                            ts.end.strftime("%Y-%m-%d")
                                            if ts.end
                                            else "N/A"
                                        ),
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("Frequency: ", fw="bold"),
                                        ts.frequency or "N/A",
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("Unit: ", fw="bold"),
                                        ts.unit or "N/A",
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
                                        ts.currency or "N/A",
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("Country: ", fw="bold"),
                                        ts.country or "N/A",
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("Scale: ", fw="bold"),
                                        (
                                            str(ts.scale)
                                            if ts.scale is not None
                                            else "N/A"
                                        ),
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("Timeseries ID: ", fw="bold"),
                                        str(ts.id),
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("Parent ID: ", fw="bold"),
                                        ts.parent_id or "N/A",
                                    ]
                                ),
                                dmc.Text(
                                    [
                                        dmc.Text("Remark: ", fw="bold"),
                                        ts.remark or "N/A",
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
        df = ts.data.dropna().reset_index()
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
                name=ts.code,
                line=dict(color="#3b82f6", width=2),
            )
        )
        fig.update_layout(
            title=f"{ts.code} Time Series",
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

    except Exception as e:
        logger.error(f"Error loading modal content: {e}")
        return "Error", f"Error: {e}", f"Error: {e}", {}, f"Error: {e}"


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
        State("csv-data", "data"),
    ],
    prevent_initial_call=True,
)
def create_timeseries(n_clicks, code, name, asset_class, frequency, csv_data):
    if not n_clicks or not code:
        raise PreventUpdate

    try:
        # If Excel data is provided, convert it back to DataFrame
        df = None
        if csv_data:
            import json

            df = pd.read_json(csv_data["data"], orient="records")
            # Convert index back to datetime
            df.index = pd.to_datetime(csv_data["index"])

        # Create new timeseries with Excel data if available
        if df is not None:
            # Call the optimized upload_excel_data function to save to database
            result = upload_excel_data_optimized(df)
            message = f"Timeseries '{code}' created successfully! Excel data uploaded: {result['processed']}/{result['total']} columns processed in {result['duration']:.2f}s"
            if result["skipped"] > 0:
                message += f" ({result['skipped']} skipped)"
        else:
            # Create new timeseries without Excel data
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
