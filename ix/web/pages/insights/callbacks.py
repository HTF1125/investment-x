"""
Enhanced Insights Callbacks
Updated callbacks to support the new modern design and additional features.
"""

import json
import base64
from datetime import datetime, date
from typing import Any, List, Tuple, Optional

import dash
import dash_mantine_components as dmc
from dash import html, callback, Input, Output, State, ALL, no_update, dcc
from dash.exceptions import PreventUpdate

from ix.db.client import (
    get_insights,
    get_insight_by_id,
    delete_insight,
    update_insight_summary,
)
from ix.db.conn import Session
from ix.db.models import Insights
from ix import dbb
from ix.misc.terminal import get_logger
from ix.misc import PDFSummarizer, Settings
from .insight_card import InsightCard

# Configure logging
logger = get_logger(__name__)

# Modern Color Scheme
COLORS = {
    "primary": "#3b82f6",
    "secondary": "#64748b",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "dark": "#1e293b",
    "light": "#f8fafc",
    "background": "#0f172a",
    "surface": "#1e293b",
    "surface_light": "#334155",
    "text_primary": "#f1f5f9",
    "text_secondary": "#94a3b8",
    "border": "#475569",
}


def remove_deleted_insight(current_data: List[str], insight_id: str) -> List[str]:
    """Removes the deleted insight from the current data list."""
    updated_insights = []
    for insight_json in current_data:
        insight = json.loads(insight_json)
        if str(insight.get("id")) != insight_id:
            updated_insights.append(insight_json)
    return updated_insights


def delete_insight_backend(insight: dict) -> None:
    """Attempts deletion in the backend for a given insight."""
    try:
        delete_insight(str(insight.get("id")))
    except Exception as e:
        logger.error(f"Error deleting insight with id {insight.get('id')}: {e}")


def calculate_insights_stats(insights_data: List[str]) -> dict:
    """Calculate statistics for the insights dashboard."""
    if not insights_data:
        return {
            "total": 0,
            "this_month": 0,
            "top_issuer": "N/A",
            "avg_summary_length": 0,
        }

    total = len(insights_data)
    this_month = 0
    issuer_counts = {}
    total_summary_length = 0
    summary_count = 0

    current_month = datetime.now().month
    current_year = datetime.now().year

    for insight_json in insights_data:
        insight = json.loads(insight_json)

        # Count this month's insights
        published_date = insight.get("published_date", "")
        if published_date:
            try:
                date_obj = datetime.strptime(published_date[:10], "%Y-%m-%d")
                if date_obj.month == current_month and date_obj.year == current_year:
                    this_month += 1
            except:
                pass

        # Count issuers
        issuer = insight.get("issuer", "Unknown")
        issuer_counts[issuer] = issuer_counts.get(issuer, 0) + 1

        # Calculate average summary length
        summary = insight.get("summary", "")
        if summary:
            total_summary_length += len(summary)
            summary_count += 1

    top_issuer = (
        max(issuer_counts.items(), key=lambda x: x[1])[0] if issuer_counts else "N/A"
    )
    avg_summary_length = (
        total_summary_length // summary_count if summary_count > 0 else 0
    )

    return {
        "total": total,
        "this_month": this_month,
        "top_issuer": top_issuer,
        "avg_summary_length": avg_summary_length,
    }


# ----------------------------------------------------------------------
# Enhanced Combined Callback: Fetch, Delete, and Filter Insights
# ----------------------------------------------------------------------
@callback(
    Output("insights-data", "data"),
    Output("total-insights-loaded", "data"),
    Output("search-query", "data"),
    Output("filter-state", "data"),
    Input("load-more-insights", "n_clicks"),
    Input("search-button", "n_clicks"),
    Input("insights-search", "n_submit"),
    Input("sort-dropdown", "value"),
    Input("issuer-filter", "value"),
    Input("date-range-filter", "start_date"),
    Input("date-range-filter", "end_date"),
    Input({"type": "delete-insight-button", "index": ALL}, "n_clicks"),
    State("insights-data", "data"),
    State("total-insights-loaded", "data"),
    State("search-query", "data"),
    State("filter-state", "data"),
    State("insights-search", "value"),
)
def enhanced_fetch_delete_filter_callback(
    load_clicks: Optional[int],
    search_clicks: Optional[int],
    search_submit: Optional[int],
    sort_value: str,
    issuer_filter: List[str],
    start_date: Optional[str],
    end_date: Optional[str],
    delete_clicks: List[Optional[int]],
    current_data: List[str],
    total_loaded: int,
    search_query: str,
    filter_state: dict,
    search_value: Optional[str],
):
    """
    Enhanced callback that handles fetching, deleting, and filtering insights.
    """
    ctx = dash.callback_context
    if ctx.triggered:
        triggered_prop = ctx.triggered[0]["prop_id"]
    else:
        triggered_prop = "initial"

    # ----- Deletion Branch -----
    if "delete-insight-button" in triggered_prop:
        try:
            triggered_id = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
            insight_id = str(triggered_id["index"])
        except Exception:
            raise PreventUpdate

        # Remove the insight from the current data
        updated_insights = remove_deleted_insight(current_data, insight_id)

        # Find the insight to delete in the current data
        for insight_json in current_data:
            insight = json.loads(insight_json)
            if str(insight.get("id")) == insight_id:
                delete_insight_backend(insight)
                break

        new_total = total_loaded - 1 if total_loaded > 0 else 0
        return updated_insights, new_total, no_update, no_update

    # ----- Fetch/Load/Search/Filter Branch -----
    if (
        triggered_prop.startswith("search-button")
        or triggered_prop.startswith("insights-search")
        or triggered_prop.startswith("sort-dropdown")
        or triggered_prop.startswith("issuer-filter")
        or triggered_prop.startswith("date-range-filter")
        or triggered_prop == "initial"
    ):
        search_query = search_value or ""
        skip = 0

        # Update filter state
        new_filter_state = {
            "sort": sort_value,
            "issuer_filter": issuer_filter or [],
            "start_date": start_date,
            "end_date": end_date,
        }

    elif triggered_prop.startswith("load-more-insights"):
        skip = total_loaded or 0
        new_filter_state = filter_state or {}
    else:
        skip = 0
        new_filter_state = filter_state or {}

    limit = 10
    new_insights = get_insights(search=search_query, skip=skip, limit=limit)

    if not new_insights:
        if triggered_prop.startswith("load-more-insights"):
            raise PreventUpdate
        new_serialized: List[str] = []
    else:
        new_serialized = [insight.model_dump_json() for insight in new_insights]

    if (
        triggered_prop.startswith("search-button")
        or triggered_prop.startswith("insights-search")
        or triggered_prop.startswith("sort-dropdown")
        or triggered_prop.startswith("issuer-filter")
        or triggered_prop.startswith("date-range-filter")
        or triggered_prop == "initial"
    ):
        updated_data = new_serialized
        new_total = len(new_serialized)
    else:
        updated_data = current_data + new_serialized
        new_total = total_loaded + len(new_insights)

    return updated_data, new_total, search_query, new_filter_state


# ----------------------------------------------------------------------
# Enhanced Callback: Update Insight Cards with Modern Design
# ----------------------------------------------------------------------
@callback(
    Output("insights-container-wrapper", "children"),
    Input("insights-data", "data"),
)
def update_insights_cards(insights_data: List[str]) -> Any:
    """Updates the UI cards with enhanced modern design."""
    if not insights_data:
        return dbc.Alert(
            [
                html.Div(
                    [
                        html.I(
                            className="fas fa-search fa-2x mb-3",
                            style={"color": COLORS["text_secondary"]},
                        ),
                        html.H5(
                            "No Insights Found",
                            style={
                                "color": COLORS["text_primary"],
                                "fontWeight": "600",
                            },
                        ),
                        html.P(
                            "Try adjusting your search criteria or upload a new document",
                            style={
                                "color": COLORS["text_secondary"],
                                "fontSize": "0.9rem",
                            },
                        ),
                    ],
                    className="text-center py-4",
                )
            ],
            color="info",
            style={
                "border": f"1px solid {COLORS['border']}",
                "borderRadius": "12px",
                "backgroundColor": COLORS["surface"],
            },
        )

    try:
        cards = [InsightCard().layout(json.loads(insight)) for insight in insights_data]
        return [dbc.Row(dbc.Col(card, width=12)) for card in cards]
    except Exception as e:
        return dbc.Alert(
            [
                html.Div(
                    [
                        html.I(
                            className="fas fa-exclamation-triangle fa-2x mb-3",
                            style={"color": COLORS["danger"]},
                        ),
                        html.H5(
                            "Error Processing Insights",
                            style={
                                "color": COLORS["text_primary"],
                                "fontWeight": "600",
                            },
                        ),
                        html.P(
                            f"An error occurred: {str(e)}",
                            style={
                                "color": COLORS["text_secondary"],
                                "fontSize": "0.9rem",
                            },
                        ),
                    ],
                    className="text-center py-4",
                )
            ],
            color="danger",
            style={
                "border": f"1px solid {COLORS['danger']}",
                "borderRadius": "12px",
                "backgroundColor": COLORS["surface"],
            },
        )


# ----------------------------------------------------------------------
# Enhanced Callback: Update Statistics Dashboard
# ----------------------------------------------------------------------
@callback(
    [
        Output("total-insights-count", "children"),
        Output("this-month-count", "children"),
        Output("top-issuer", "children"),
        Output("avg-summary-length", "children"),
    ],
    Input("insights-data", "data"),
)
def update_stats_dashboard(insights_data: List[str]):
    """Update the statistics dashboard with current insights data."""
    stats = calculate_insights_stats(insights_data)

    return (
        stats["total"],
        stats["this_month"],
        stats["top_issuer"],
        f"{stats['avg_summary_length']:,} chars",
    )


# ----------------------------------------------------------------------
# Enhanced Callback: PDF Upload Processing with Progress
# ----------------------------------------------------------------------
@callback(
    [
        Output("output-pdf-upload", "children"),
        Output("upload-pdf", "contents"),
        Output("upload-progress", "children"),
    ],
    Input("upload-pdf", "contents"),
    State("upload-pdf", "filename"),
    State("upload-pdf", "last_modified"),
    prevent_initial_call=True,
)
def enhanced_process_pdf_upload(
    content: Optional[str], filename: Optional[str], last_modified: Optional[float]
) -> Tuple[Any, Optional[str], Any]:
    """
    Enhanced PDF upload processing with progress indicators and better error handling.
    """
    if content is None or filename is None or last_modified is None:
        raise PreventUpdate

    # Show progress indicator
    progress_bar = dbc.Progress(
        value=0,
        color="primary",
        className="mb-3",
        style={"height": "8px", "borderRadius": "4px"},
    )

    try:
        content_type, content_string = content.split(",")
        decoded = base64.b64decode(content_string)

        # Validate file format
        if not filename.lower().endswith(".pdf"):
            return (
                dbc.Alert(
                    [
                        html.I(className="fas fa-exclamation-triangle me-2"),
                        "Only PDF files are allowed.",
                    ],
                    color="danger",
                    className="mt-3",
                ),
                None,
                None,
            )

        if not decoded.startswith(b"%PDF-"):
            return (
                dbc.Alert(
                    [
                        html.I(className="fas fa-exclamation-triangle me-2"),
                        "Invalid PDF file format.",
                    ],
                    color="danger",
                    className="mt-3",
                ),
                None,
                None,
            )

        # Parse filename - try to extract metadata, but allow upload even if format is incorrect
        needs_metadata = False
        published_date = None
        issuer = None
        name = None

        try:
            published_date_str, issuer, name = filename.rsplit("_", 2)
            name = name.rsplit(".", 1)[0]
            published_date = datetime.strptime(published_date_str, "%Y%m%d").date()
        except ValueError:
            # Filename format is incorrect - use defaults and extract what we can
            needs_metadata = True
            # Try to extract name from filename (remove .pdf extension)
            name = filename.rsplit(".", 1)[0] if "." in filename else filename
            # Use default values from model (today's date, "Unnamed")
            published_date = date.today()
            issuer = "Unnamed"

        with Session() as session:
            insight = Insights(
                published_date=published_date,
                issuer=issuer or "Unnamed",
                name=name or "Unnamed",
                status="processing",
                pdf_content=decoded,
            )
            session.add(insight)
            session.flush()

            summary_text = None
            if getattr(Settings, "openai_secret_key", None):
                summarizer = PDFSummarizer(Settings.openai_secret_key)
                summary_text = summarizer.process_insights(decoded)
                insight.summary = summary_text
                insight.status = "completed"
            else:
                insight.summary = None
                insight.status = "completed"

            insight_id = str(insight.id)

        # Success message
        success_alert = dbc.Alert(
            [
                html.Div(
                    [
                        html.I(
                            className="fas fa-check-circle fa-2x mb-3",
                            style={"color": COLORS["success"]},
                        ),
                        html.H5(
                            "Upload Successful!",
                            style={
                                "color": COLORS["text_primary"],
                                "fontWeight": "600",
                            },
                        ),
                        html.P(
                            f"File '{filename}' has been processed and added to your insights.",
                            style={
                                "color": COLORS["text_secondary"],
                                "fontSize": "0.9rem",
                            },
                        ),
                        html.Hr(style={"borderColor": COLORS["border"]}),
                        html.Div(
                            [
                                html.Small(
                                    [
                                        html.Strong("Published Date: "),
                                        published_date.strftime("%B %d, %Y") if published_date else "Not set",
                                    ],
                                    className="d-block mb-1",
                                ),
                                html.Small(
                                    [
                                        html.Strong("Issuer: "),
                                        issuer or "Unnamed",
                                    ],
                                    className="d-block mb-1",
                                ),
                                html.Small(
                                    [
                                        html.Strong("Document: "),
                                        name or "Unnamed",
                                    ],
                                    className="d-block mb-1",
                                ),
                                html.Small(
                                    [
                                        html.Strong("File Size: "),
                                        f"{len(decoded) / 1024:.2f} KB",
                                    ],
                                    className="d-block mb-1",
                                ),
                                html.Small(
                                    [
                                        html.Strong("Insight ID: "),
                                        insight_id,
                                    ],
                                    className="d-block mb-1",
                                ),
                            ],
                            style={
                                "backgroundColor": COLORS["background"],
                                "padding": "12px",
                                "borderRadius": "6px",
                                "border": f"1px solid {COLORS['border']}",
                            },
                        ),
                    ],
                    className="text-center",
                )
            ],
            color="success",
            className="mt-3",
            style={
                "border": f"1px solid {COLORS['success']}",
                "borderRadius": "12px",
                "backgroundColor": COLORS["surface"],
            },
        )

        # Add warning if metadata needs to be edited
        if needs_metadata:
            warning_alert = dbc.Alert(
                [
                    html.I(className="fas fa-exclamation-circle me-2"),
                    html.Strong("Note: "),
                    f"The filename '{filename}' doesn't match the expected format. ",
                    "The file has been uploaded with default values. ",
                    "You can edit the metadata (date, issuer, name) later by clicking the edit button on the insight card.",
                ],
                color="warning",
                className="mt-3",
            )
            return html.Div([success_alert, warning_alert]), None, None

        return success_alert, None, None

    except Exception as e:
        logger.exception("Error processing PDF upload")
        return (
            dbc.Alert(
                [
                    html.Div(
                        [
                            html.I(
                                className="fas fa-exclamation-triangle fa-2x mb-3",
                                style={"color": COLORS["danger"]},
                            ),
                            html.H5(
                                "Upload Failed",
                                style={
                                    "color": COLORS["text_primary"],
                                    "fontWeight": "600",
                                },
                            ),
                            html.P(
                                f"An error occurred: {str(e)}",
                                style={
                                    "color": COLORS["text_secondary"],
                                    "fontSize": "0.9rem",
                                },
                            ),
                        ],
                        className="text-center",
                    )
                ],
                color="danger",
                className="mt-3",
                style={
                    "border": f"1px solid {COLORS['danger']}",
                    "borderRadius": "12px",
                    "backgroundColor": COLORS["surface"],
                },
            ),
            None,
            None,
        )


# ----------------------------------------------------------------------
# Enhanced Callback: Modal Display with Better UX
# ----------------------------------------------------------------------
@callback(
    [
        Output("insight-modal", "is_open"),
        Output("modal-body-content", "children"),
        Output("modal-last-updated", "children"),
    ],
    [
        Input({"type": "insight-card-clickable", "index": ALL}, "n_clicks"),
        Input("close-modal", "n_clicks"),
    ],
    [
        State("insight-modal", "is_open"),
        State("insights-data", "data"),
    ],
)
def enhanced_display_modal(
    n_clicks_list: List[Optional[int]],
    close_n: Optional[int],
    is_open: bool,
    insights_data: List[str],
) -> Tuple[bool, Any, str]:
    """
    Enhanced modal display with better content formatting and metadata.
    """
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    triggered = ctx.triggered[0]
    if "close-modal" in triggered["prop_id"]:
        return False, no_update, no_update

    if not any(n_clicks_list):
        raise PreventUpdate

    try:
        triggered_id = json.loads(triggered["prop_id"].split(".")[0])
        card_index = triggered_id["index"]
    except Exception:
        return is_open, no_update, no_update

    summary_text = "No summary available."
    insight_metadata = {}

    for insight_json in insights_data:
        insight = json.loads(insight_json)
        if str(insight.get("id")) == str(card_index):
            summary_text = insight.get("summary", "No summary available.")
            insight_metadata = {
                "name": insight.get("name", "Unknown"),
                "issuer": insight.get("issuer", "Unknown"),
                "published_date": insight.get("published_date", "Unknown"),
            }
            break

    # Format the summary with better typography
    formatted_content = html.Div(
        [
            # Metadata header
            html.Div(
                [
                    html.H6(
                        insight_metadata.get("name", "Unknown Document"),
                        style={
                            "color": COLORS["text_primary"],
                            "fontWeight": "600",
                            "marginBottom": "8px",
                        },
                    ),
                    html.Div(
                        [
                            html.Span(
                                f"📅 {insight_metadata.get('published_date', 'Unknown')[:10]}",
                                style={
                                    "color": COLORS["text_secondary"],
                                    "fontSize": "0.85rem",
                                    "marginRight": "16px",
                                },
                            ),
                            html.Span(
                                f"🏢 {insight_metadata.get('issuer', 'Unknown')}",
                                style={
                                    "color": COLORS["primary"],
                                    "fontSize": "0.85rem",
                                    "fontWeight": "500",
                                },
                            ),
                        ],
                        className="mb-3",
                    ),
                    html.Hr(style={"borderColor": COLORS["border"]}),
                ],
                className="mb-4",
            ),
            # Summary content
            html.Div(
                summary_text,
                style={
                    "fontSize": "1rem",
                    "lineHeight": "1.6",
                    "color": COLORS["text_primary"],
                },
            ),
        ]
    )

    # Generate last updated timestamp
    last_updated = datetime.now().strftime("%I:%M %p")

    return True, formatted_content, last_updated
