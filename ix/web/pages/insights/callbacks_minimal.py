"""
Enhanced Insights Callbacks
Advanced implementation with database connectivity, PDF processing, and modern UX.
Incorporates features from wx implementation with improved design.
"""

import json
import base64
from datetime import datetime

# from bson import ObjectId  # Removed - MongoDB-specific
from typing import Any, Dict, List, Tuple, Optional

import dash
import dash_bootstrap_components as dbc
import dash_mantine_components as dmc
from dash import html, dcc, callback, Input, Output, State, no_update, ALL
from dash.exceptions import PreventUpdate

from uuid import uuid4

from ix.db.client import (
    get_insights,
    get_publishers,
    create_publisher,
    touch_publisher,
    set_insight_summary,
    update_insight_metadata,
)
from ix.db.conn import Session
from ix.db.models import Insights

# from ix.db.boto import Boto  # Removed - old db module
from ix.misc.terminal import get_logger
from ix.misc import PDFSummarizer, Settings
from .insight_card import create_insight_card

# Configure logging
logger = get_logger(__name__)


def _format_last_visited(last_visited: Optional[str]) -> str:
    """Format last visited timestamps into human readable text."""

    if not last_visited:
        return "Never"

    try:
        normalized = last_visited.replace("Z", "+00:00")
        timestamp = datetime.fromisoformat(normalized)
    except ValueError:
        return last_visited

    if timestamp.tzinfo is not None:
        now = datetime.now(tz=timestamp.tzinfo)
    else:
        now = datetime.now()

    delta = now - timestamp

    if delta.days > 0:
        return f"{delta.days}d ago"
    hours = delta.seconds // 3600
    if hours > 0:
        return f"{hours}h ago"
    minutes = delta.seconds // 60
    if minutes > 0:
        return f"{minutes}m ago"
    return "Just now"


def _build_publishers_list(publishers: List[dict]) -> List[html.Div]:
    """Render the publisher list for the sidebar."""

    rows = []
    for publisher in publishers:
        name = publisher.get("name") or "Unnamed"
        url = publisher.get("url") or "#"
        frequency = publisher.get("frequency") or "Unclassified"
        last_seen = _format_last_visited(publisher.get("last_visited"))
        publisher_id = publisher.get("id") or str(uuid4())

        badge = dmc.Badge(
            frequency,
            color="violet",
            variant="light",
            radius="sm",
            size="xs",
        )

        timestamp = dmc.Text(
            f"Last visited {last_seen}",
            size="xs",
            c="gray.5",
        )

        button_kwargs: Dict[str, Any] = {
            "id": {"type": "publisher-visit", "index": publisher_id},
            "n_clicks": 0,
            "variant": "light",
            "color": "blue",
            "size": "xs",
            "radius": "sm",
        }

        if not url or url == "#":
            button_kwargs["disabled"] = True

        visit_button = dmc.Button("Visit", **button_kwargs)

        if url and url != "#":
            visit_control: Any = html.A(
                visit_button,
                href=url,
                target="_blank",
                rel="noopener noreferrer",
                style={"textDecoration": "none"},
            )
        else:
            visit_control = visit_button

        rows.append(
            dmc.Card(
                [
                    dmc.Stack(
                        [
                            dmc.Group(
                                [
                                    dmc.Text(name, fw=600, size="sm", c="gray.0"),
                                    badge,
                                ],
                                gap="xs",
                            ),
                            dmc.Group(
                                [timestamp, visit_control],
                                justify="space-between",
                            ),
                        ],
                        gap="xs",
                    )
                ],
                withBorder=True,
                radius="md",
                shadow="sm",
                padding="md",
                style={"backgroundColor": "#0f172a"},
            )
        )

    return rows


@callback(
    Output("insight-sources-list", "children"),
    Output("issuer-filter", "data"),
    Input("publishers-refresh-interval", "n_intervals"),
    Input("publishers-refresh-token", "data"),
)
def refresh_publishers_list(_: int, __: Optional[str]):
    """Refresh publishers sidebar and issuer filter options."""

    default_options = [{"label": "All Issuers", "value": "all"}]

    try:
        publishers = get_publishers()
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Failed to load publishers")
        alert = dmc.Alert(
            [
                dmc.Text("Unable to load publishers", fw=600),
                dmc.Text(str(exc), size="sm", c="gray.5"),
            ],
            color="red",
            variant="filled",
        )
        return alert, default_options

    if not publishers:
        empty_state = dmc.Text(
            "No publishers configured yet.",
            size="sm",
            c="gray.5",
            ta="center",
        )
        return empty_state, default_options

    rows = _build_publishers_list(publishers)
    options = default_options + [
        {
            "label": publisher.get("name") or "Unnamed",
            "value": publisher.get("name") or "Unnamed",
        }
        for publisher in publishers
        if publisher.get("name")
    ]

    return rows, options


@callback(
    Output("add-publisher-modal", "is_open"),
    Input("add-publisher-button", "n_clicks"),
    Input("close-add-publisher-modal", "n_clicks"),
    Input("cancel-add-publisher", "n_clicks"),
    State("add-publisher-modal", "is_open"),
    prevent_initial_call=True,
)
def toggle_add_publisher_modal(add_clicks, close_clicks, cancel_clicks, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    if trigger == "add-publisher-button":
        return True

    return False


@callback(
    Output("publisher-name-input", "value"),
    Output("publisher-url-input", "value"),
    Output("publisher-frequency-input", "value"),
    Output("add-publisher-feedback", "children"),
    Output("publishers-refresh-token", "data"),
    Output("add-publisher-modal", "is_open", allow_duplicate=True),
    Input("submit-add-publisher", "n_clicks"),
    State("publisher-name-input", "value"),
    State("publisher-url-input", "value"),
    State("publisher-frequency-input", "value"),
    prevent_initial_call=True,
)
def handle_add_publisher_submission(n_clicks, name, url, frequency):
    if not n_clicks:
        raise PreventUpdate

    try:
        created = create_publisher(
            name=name or "",
            url=url or "",
            frequency=frequency,
        )
    except ValueError as exc:
        alert = dbc.Alert(str(exc), color="danger")
        return no_update, no_update, no_update, alert, no_update, True
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Unexpected error while creating publisher")
        alert = dbc.Alert("Failed to add publisher. Please try again.", color="danger")
        return no_update, no_update, no_update, alert, no_update, True

    success_alert = dbc.Alert(
        [
            html.Div("Publisher added successfully.", style={"fontWeight": "600"}),
            html.Small(f"Name: {created.get('name')}", className="d-block mt-1"),
        ],
        color="success",
        className="mt-2",
    )

    refresh_token = str(uuid4())

    return "", "", frequency or "Unclassified", success_alert, refresh_token, False


@callback(
    Output("publishers-refresh-token", "data", allow_duplicate=True),
    Input({"type": "publisher-visit", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def handle_publisher_visit(n_clicks_list):
    if not any(n_clicks_list or []):
        raise PreventUpdate

    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    try:
        triggered_id = json.loads(ctx.triggered[0]["prop_id"].split(".")[0])
        publisher_id = triggered_id.get("index")
    except Exception:
        raise PreventUpdate

    if not publisher_id:
        raise PreventUpdate

    try:
        touch_publisher(publisher_id)
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Failed to update publisher last visited")
        raise PreventUpdate from exc

    return str(uuid4())


def create_insight_card(insight_data):
    """Create an insight card with proper styling"""
    # Status color mapping
    status_colors = {
        "completed": "#10b981",
        "processing": "#f59e0b",
        "new": "#3b82f6",
        "failed": "#ef4444",
    }

    status = insight_data.get("status", "new").lower()

    insight_id = str(insight_data.get("id", ""))
    summary_text = insight_data.get("summary", "") or ""
    is_editing = bool(insight_data.get("editing"))
    draft_summary = insight_data.get("draft_summary", summary_text)
    draft_title = insight_data.get(
        "draft_title", insight_data.get("name") or "Untitled"
    )
    draft_issuer = insight_data.get(
        "draft_issuer", insight_data.get("issuer") or "Unknown"
    )
    published_date_value = insight_data.get("published_date") or ""
    draft_date = insight_data.get(
        "draft_date", published_date_value[:10] if published_date_value else ""
    )

    summary_preview = (
        summary_text[:200] + "..." if len(summary_text) > 200 else summary_text
    )
    if not summary_preview:
        summary_preview = "No summary available."

    edit_button_style = {
        "backgroundColor": "transparent",
        "border": "1px solid #3b82f6",
        "borderRadius": "6px",
        "color": "#3b82f6",
        "padding": "6px 12px",
        "fontSize": "12px",
        "cursor": "pointer",
        "marginRight": "8px",
        "display": "flex",
        "alignItems": "center",
    }
    if is_editing:
        edit_button_style["display"] = "none"

    summary_view = html.Div(
        summary_preview,
        style={
            "color": "#e2e8f0",
            "fontSize": "14px",
            "lineHeight": "1.5",
            "margin": "0 0 15px 0",
            "display": "none" if is_editing else "block",
        },
    )

    summary_editor = html.Div(
        [
            html.Div(
                [
                    html.Label(
                        "Title",
                        style={
                            "color": "#94a3b8",
                            "fontSize": "12px",
                            "marginBottom": "4px",
                            "display": "block",
                        },
                    ),
                    dcc.Input(
                        value=draft_title,
                        id={"type": "inline-title-input", "index": insight_id},
                        type="text",
                        style={
                            "width": "100%",
                            "backgroundColor": "#0f172a",
                            "color": "#e2e8f0",
                            "border": "1px solid #3b82f6",
                            "borderRadius": "6px",
                            "padding": "8px",
                            "marginBottom": "12px",
                        },
                        placeholder="Enter insight title",
                    ),
                ]
            ),
            html.Div(
                [
                    html.Label(
                        "Source / Issuer",
                        style={
                            "color": "#94a3b8",
                            "fontSize": "12px",
                            "marginBottom": "4px",
                            "display": "block",
                        },
                    ),
                    dcc.Input(
                        value=draft_issuer,
                        id={"type": "inline-issuer-input", "index": insight_id},
                        type="text",
                        style={
                            "width": "100%",
                            "backgroundColor": "#0f172a",
                            "color": "#e2e8f0",
                            "border": "1px solid #3b82f6",
                            "borderRadius": "6px",
                            "padding": "8px",
                            "marginBottom": "12px",
                        },
                        placeholder="Enter insight source",
                    ),
                ]
            ),
            html.Div(
                [
                    html.Label(
                        "Published Date",
                        style={
                            "color": "#94a3b8",
                            "fontSize": "12px",
                            "marginBottom": "4px",
                            "display": "block",
                        },
                    ),
                    dcc.Input(
                        value=draft_date,
                        id={"type": "inline-date-input", "index": insight_id},
                        type="text",
                        style={
                            "width": "100%",
                            "backgroundColor": "#0f172a",
                            "color": "#e2e8f0",
                            "border": "1px solid #3b82f6",
                            "borderRadius": "6px",
                            "padding": "8px",
                            "marginBottom": "12px",
                        },
                        placeholder="YYYY-MM-DD",
                    ),
                ]
            ),
            dcc.Textarea(
                value=draft_summary,
                id={"type": "inline-summary-editor", "index": insight_id},
                style={
                    "width": "100%",
                    "minHeight": "140px",
                    "backgroundColor": "#0f172a",
                    "color": "#e2e8f0",
                    "border": "1px solid #3b82f6",
                    "borderRadius": "6px",
                    "padding": "10px",
                    "fontSize": "14px",
                    "lineHeight": "1.6",
                    "fontFamily": "inherit",
                },
                placeholder="Write or paste the insight summary here...",
                spellCheck=True,
            ),
            html.Div(
                [
                    html.Button(
                        [
                            html.I(
                                className="fas fa-save",
                                style={"marginRight": "6px"},
                            ),
                            "Save Changes",
                        ],
                        id={"type": "inline-summary-save", "index": insight_id},
                        n_clicks=0,
                        style={
                            "backgroundColor": "#3b82f6",
                            "border": "none",
                            "borderRadius": "6px",
                            "color": "#ffffff",
                            "padding": "6px 14px",
                            "fontSize": "12px",
                            "cursor": "pointer",
                            "marginRight": "8px",
                            "display": "flex",
                            "alignItems": "center",
                        },
                    ),
                    html.Button(
                        [
                            html.I(
                                className="fas fa-times",
                                style={"marginRight": "6px"},
                            ),
                            "Cancel",
                        ],
                        id={"type": "inline-summary-cancel", "index": insight_id},
                        n_clicks=0,
                        style={
                            "backgroundColor": "transparent",
                            "border": "1px solid #475569",
                            "borderRadius": "6px",
                            "color": "#94a3b8",
                            "padding": "6px 14px",
                            "fontSize": "12px",
                            "cursor": "pointer",
                            "display": "flex",
                            "alignItems": "center",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "marginTop": "12px",
                },
            ),
        ],
        style={"display": "block" if is_editing else "none"},
    )

    return html.Div(
        [
            html.Div(
                [
                    html.Div(
                        [
                            html.H5(
                                insight_data.get("name", "Untitled"),
                                style={
                                    "color": "#ffffff",
                                    "margin": "0 0 8px 0",
                                    "fontSize": "1.1rem",
                                },
                            ),
                            html.P(
                                insight_data.get("issuer", "Unknown"),
                                style={
                                    "color": "#94a3b8",
                                    "margin": "0 0 8px 0",
                                    "fontSize": "14px",
                                    "fontWeight": "500",
                                },
                            ),
                            html.P(
                                (
                                    insight_data.get("published_date", "")[:10]
                                    if insight_data.get("published_date")
                                    else "No date"
                                ),
                                style={
                                    "color": "#64748b",
                                    "margin": "0",
                                    "fontSize": "12px",
                                },
                            ),
                        ],
                        style={"flex": "1"},
                    ),
                    html.Div(
                        status.title(),
                        style={
                            "backgroundColor": status_colors.get(status, "#64748b"),
                            "color": "#ffffff",
                            "padding": "4px 12px",
                            "borderRadius": "20px",
                            "fontSize": "12px",
                            "fontWeight": "bold",
                        },
                    ),
                ],
                style={
                    "display": "flex",
                    "justifyContent": "space-between",
                    "alignItems": "flex-start",
                    "marginBottom": "12px",
                },
            ),
            summary_view,
            summary_editor,
            html.Div(
                [
                    html.Button(
                        [
                            html.I(
                                className="fas fa-eye", style={"marginRight": "6px"}
                            ),
                            "View Details",
                        ],
                        id={
                            "type": "insight-card-clickable",
                            "index": str(insight_data.get("id", "")),
                        },
                        n_clicks=0,
                        style={
                            "backgroundColor": "#3b82f6",
                            "border": "none",
                            "borderRadius": "6px",
                            "color": "#ffffff",
                            "padding": "6px 12px",
                            "fontSize": "12px",
                            "cursor": "pointer",
                            "marginRight": "8px",
                            "display": "flex",
                            "alignItems": "center",
                        },
                    ),
                    html.Button(
                        [
                            html.I(
                                className="fas fa-edit",
                                style={"marginRight": "6px"},
                            ),
                            "Edit",
                        ],
                        id={
                            "type": "edit-summary-button",
                            "index": str(insight_data.get("id", "")),
                        },
                        n_clicks=0,
                        style=edit_button_style,
                    ),
                    html.A(
                        [
                            html.I(
                                className="fas fa-download",
                                style={"marginRight": "6px"},
                            ),
                            "Download",
                        ],
                        href=f"/api/download-pdf/{insight_data.get('id')}",
                        target="_blank",
                        style={
                            "backgroundColor": "transparent",
                            "border": "1px solid #475569",
                            "borderRadius": "6px",
                            "color": "#ffffff",
                            "padding": "6px 12px",
                            "fontSize": "12px",
                            "cursor": "pointer",
                            "marginRight": "8px",
                            "display": "flex",
                            "alignItems": "center",
                            "textDecoration": "none",
                        },
                    ),
                    html.Button(
                        [
                            html.I(
                                className="fas fa-trash", style={"marginRight": "6px"}
                            ),
                            "Delete",
                        ],
                        id={
                            "type": "delete-insight-button",
                            "index": str(insight_data.get("id", "")),
                        },
                        n_clicks=0,
                        style={
                            "backgroundColor": "transparent",
                            "border": "1px solid #ef4444",
                            "borderRadius": "6px",
                            "color": "#ef4444",
                            "padding": "6px 12px",
                            "fontSize": "12px",
                            "cursor": "pointer",
                            "display": "flex",
                            "alignItems": "center",
                        },
                    ),
                ],
                style={"display": "flex", "gap": "8px"},
            ),
        ],
        style={
            "backgroundColor": "#1e293b",
            "border": "1px solid #475569",
            "borderRadius": "12px",
            "padding": "20px",
            "marginBottom": "15px",
            "boxShadow": "0 4px 12px rgba(0, 0, 0, 0.3)",
            "transition": "all 0.3s ease",
        },
    )


# Initial insights loading callback
@callback(
    [
        Output("insights-container", "children"),
        Output("insights-data", "data"),
    ],
    Input("insights-container", "id"),  # Triggers on page load
)
def load_initial_insights(container_id):
    """Load initial insights from database on page load"""
    try:
        # Get insights from database
        insights = get_insights()

        if not insights:
            # No insights found
            return (
                html.Div(
                    [
                        html.I(
                            className="fas fa-search fa-3x",
                            style={"color": "#64748b", "marginBottom": "20px"},
                        ),
                        html.H4(
                            "No Insights Found",
                            style={"color": "#ffffff", "marginBottom": "10px"},
                        ),
                        html.P(
                            "Upload some documents to get started with AI-powered insights.",
                            style={"color": "#94a3b8"},
                        ),
                    ],
                    style={
                        "textAlign": "center",
                        "padding": "60px 20px",
                        "backgroundColor": "#1e293b",
                        "borderRadius": "12px",
                        "border": "1px solid #475569",
                    },
                ),
                [],
            )

        # Create insight cards
        insight_cards = []

        for insight in insights:
            # Handle both dict and object format
            if isinstance(insight, dict):
                insight_data = {
                    "id": str(insight.get("id", "")),
                    "name": insight.get("name") or "Untitled",
                    "issuer": insight.get("issuer") or "Unknown",
                    "published_date": (
                        str(insight.get("published_date"))
                        if insight.get("published_date")
                        else ""
                    ),
                    "status": insight.get("status") or "new",
                    "summary": insight.get("summary") or "",
                    "editing": False,
                }
            else:
                # Legacy object format - extract attributes immediately
                insight_data = {
                    "id": str(insight.id),
                    "name": insight.name or "Untitled",
                    "issuer": insight.issuer or "Unknown",
                    "published_date": (
                        str(insight.published_date) if insight.published_date else ""
                    ),
                    "status": insight.status or "new",
                    "summary": insight.summary or "",
                    "editing": False,
                }

            # Create card
            card = create_insight_card(insight_data)
            insight_cards.append(card)

        # Serialize insights data for the store (limit to first 10)
        insights_to_serialize = insights[:10]
        serialized_insights = []
        for insight in insights_to_serialize:
            if isinstance(insight, dict):
                from datetime import date, datetime

                # Create a copy and convert date/datetime objects to strings
                insight_copy = insight.copy()
                for key, value in insight_copy.items():
                    if isinstance(value, (date, datetime)):
                        insight_copy[key] = (
                            value.isoformat()
                            if hasattr(value, "isoformat")
                            else str(value)
                        )
                insight_copy["editing"] = False

                serialized_insights.append(json.dumps(insight_copy))
            else:
                serialized_insights.append(
                    json.dumps(
                        {
                            "id": str(insight.id),
                            "name": insight.name or "Untitled",
                            "issuer": insight.issuer or "Unknown",
                            "published_date": (
                                str(insight.published_date)
                                if insight.published_date
                                else ""
                            ),
                            "status": insight.status or "new",
                            "summary": insight.summary or "",
                            "editing": False,
                        }
                    )
                )

        # Limit to first 10 insights for initial load
        if len(insight_cards) > 10:
            insight_cards = insight_cards[:10]

        return (
            html.Div(insight_cards),
            serialized_insights,
        )

    except Exception as e:
        logger.error(f"Error loading insights: {e}")

        # Return error state
        return (
            html.Div(
                [
                    html.I(
                        className="fas fa-exclamation-triangle fa-3x",
                        style={"color": "#ef4444", "marginBottom": "20px"},
                    ),
                    html.H4(
                        "Error Loading Insights",
                        style={"color": "#ffffff", "marginBottom": "10px"},
                    ),
                    html.P(
                        f"Failed to load insights: {str(e)}", style={"color": "#94a3b8"}
                    ),
                    html.Button(
                        "Retry",
                        id="retry-insights",
                        style={
                            "backgroundColor": "#3b82f6",
                            "border": "none",
                            "borderRadius": "8px",
                            "color": "#ffffff",
                            "padding": "10px 20px",
                            "cursor": "pointer",
                            "marginTop": "15px",
                        },
                    ),
                ],
                style={
                    "textAlign": "center",
                    "padding": "60px 20px",
                    "backgroundColor": "#1e293b",
                    "borderRadius": "12px",
                    "border": "1px solid #475569",
                },
            ),
            [],
        )


# Load more insights callback
@callback(
    Output("insights-container", "children", allow_duplicate=True),
    Output("insights-data", "data", allow_duplicate=True),
    Input("load-more-insights", "n_clicks"),
    State("insights-container", "children"),
    State("insights-data", "data"),
    prevent_initial_call=True,
)
def load_more_insights(n_clicks, current_children, insights_store):
    """Load more insights when button is clicked"""
    if not n_clicks:
        raise PreventUpdate

    try:
        # Ensure current_children is a list
        if current_children is None:
            current_children = []
        elif not isinstance(current_children, list):
            current_children = [current_children] if current_children else []

        # Get more insights from database (skip already loaded)
        skip_count = len(current_children)
        more_insights = get_insights(skip=skip_count, limit=5)

        if not more_insights:
            # No more insights to load
            no_more_message = html.Div(
                [
                    html.I(
                        className="fas fa-check-circle",
                        style={"color": "#10b981", "marginRight": "8px"},
                    ),
                    "No more insights to load.",
                ],
                style={
                    "backgroundColor": "rgba(16, 185, 129, 0.1)",
                    "border": "1px solid rgba(16, 185, 129, 0.3)",
                    "borderRadius": "8px",
                    "padding": "15px",
                    "color": "#6ee7b7",
                    "textAlign": "center",
                    "marginTop": "15px",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                },
            )
            return current_children + [no_more_message], no_update

        # Create cards for new insights
        new_cards = []
        for insight in more_insights:
            if isinstance(insight, dict):
                insight_data = {
                    "id": str(insight.get("id", "")),
                    "name": insight.get("name") or "Untitled",
                    "issuer": insight.get("issuer") or "Unknown",
                    "published_date": (
                        str(insight.get("published_date"))
                        if insight.get("published_date")
                        else ""
                    ),
                    "status": insight.get("status") or "new",
                    "summary": insight.get("summary") or "",
                    "editing": False,
                }
            else:
                insight_data = {
                    "id": str(insight.id),
                    "name": insight.name or "Untitled",
                    "issuer": insight.issuer or "Unknown",
                    "published_date": (
                        str(insight.published_date) if insight.published_date else ""
                    ),
                    "status": insight.status or "new",
                    "summary": insight.summary or "",
                    "editing": False,
                }

            card = create_insight_card(insight_data)
            new_cards.append(card)

        serialized_store = list(insights_store) if insights_store else []

        for insight in more_insights:
            if isinstance(insight, dict):
                serialized_store.append(
                    json.dumps(
                        {
                            "id": str(insight.get("id", "")),
                            "name": insight.get("name") or "Untitled",
                            "issuer": insight.get("issuer") or "Unknown",
                            "published_date": (
                                str(insight.get("published_date"))
                                if insight.get("published_date")
                                else ""
                            ),
                            "status": insight.get("status") or "new",
                            "summary": insight.get("summary") or "",
                            "editing": False,
                        }
                    )
                )
            else:
                serialized_store.append(
                    json.dumps(
                        {
                            "id": str(insight.id),
                            "name": insight.name or "Untitled",
                            "issuer": insight.issuer or "Unknown",
                            "published_date": (
                                str(insight.published_date)
                                if insight.published_date
                                else ""
                            ),
                            "status": insight.status or "new",
                            "summary": insight.summary or "",
                            "editing": False,
                        }
                    )
                )

        return current_children + new_cards, serialized_store

    except Exception as e:
        logger.error(f"Error loading more insights: {e}")

        error_message = html.Div(
            f"Error loading more insights: {str(e)}",
            style={
                "backgroundColor": "rgba(239, 68, 68, 0.1)",
                "border": "1px solid rgba(239, 68, 68, 0.3)",
                "borderRadius": "8px",
                "padding": "15px",
                "color": "#fca5a5",
                "textAlign": "center",
                "marginTop": "15px",
            },
        )
        return current_children + [error_message], no_update


# Search functionality
@callback(
    Output("insights-container", "children", allow_duplicate=True),
    Output("insights-data", "data", allow_duplicate=True),
    [
        Input("search-button", "n_clicks"),
        Input("insights-search", "n_submit"),
    ],
    [
        State("insights-search", "value"),
        State("sort-dropdown", "value"),
        State("issuer-filter", "value"),
        State("date-range-filter", "start_date"),
        State("date-range-filter", "end_date"),
    ],
    prevent_initial_call=True,
)
def search_insights(
    search_clicks,
    search_submit,
    search_value,
    sort_value,
    issuer_value,
    start_date,
    end_date,
):
    """Search and filter insights"""
    try:
        # Get all insights first (the get_insights function only supports search parameter)
        if search_value:
            insights = get_insights(search=search_value)
        else:
            insights = get_insights()

        # Apply additional filters manually since get_insights doesn't support them
        if issuer_value and issuer_value != "all":
            insights = [
                insight
                for insight in insights
                if isinstance(insight, dict)
                and issuer_value.lower() in (insight.get("issuer", "") or "").lower()
                or not isinstance(insight, dict)
                and issuer_value.lower() in (insight.issuer or "").lower()
            ]

        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
                insights = [
                    insight
                    for insight in insights
                    if (
                        isinstance(insight, dict)
                        and insight.get("published_date")
                        and insight.get("published_date") >= start_date_obj
                    )
                    or (
                        not isinstance(insight, dict)
                        and insight.published_date
                        and insight.published_date >= start_date_obj
                    )
                ]
            except (ValueError, TypeError):
                pass

        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d").date()
                insights = [
                    insight
                    for insight in insights
                    if (
                        isinstance(insight, dict)
                        and insight.get("published_date")
                        and insight.get("published_date") <= end_date_obj
                    )
                    or (
                        not isinstance(insight, dict)
                        and insight.published_date
                        and insight.published_date <= end_date_obj
                    )
                ]
            except (ValueError, TypeError):
                pass

        if not insights:
            no_results = html.Div(
                [
                    html.I(
                        className="fas fa-search fa-2x",
                        style={"color": "#64748b", "marginBottom": "15px"},
                    ),
                    html.H5(
                        "No Results Found",
                        style={"color": "#ffffff", "marginBottom": "8px"},
                    ),
                    html.P(
                        "Try adjusting your search criteria.",
                        style={"color": "#94a3b8"},
                    ),
                ],
                style={
                    "textAlign": "center",
                    "padding": "40px 20px",
                    "backgroundColor": "#1e293b",
                    "borderRadius": "12px",
                    "border": "1px solid #475569",
                },
            )
            return no_results, []

        # Sort insights if sort value is provided
        if sort_value:

            def get_published_date(x):
                if isinstance(x, dict):
                    return x.get("published_date", "")
                return getattr(x, "published_date", "")

            def get_name(x):
                if isinstance(x, dict):
                    return x.get("name", "").lower()
                return getattr(x, "name", "").lower()

            if sort_value == "date_desc":
                insights = sorted(insights, key=get_published_date, reverse=True)
            elif sort_value == "date_asc":
                insights = sorted(insights, key=get_published_date)
            elif sort_value == "name_asc":
                insights = sorted(insights, key=get_name)
            elif sort_value == "name_desc":
                insights = sorted(insights, key=get_name, reverse=True)

        # Create cards
        insight_cards = []
        serialized_store = []
        for insight in insights:
            if isinstance(insight, dict):
                insight_data = {
                    "id": str(insight.get("id", "")),
                    "name": insight.get("name") or "Untitled",
                    "issuer": insight.get("issuer") or "Unknown",
                    "published_date": (
                        str(insight.get("published_date"))
                        if insight.get("published_date")
                        else ""
                    ),
                    "status": insight.get("status") or "new",
                    "summary": insight.get("summary") or "",
                    "editing": False,
                }
            else:
                insight_data = {
                    "id": str(insight.id),
                    "name": insight.name or "Untitled",
                    "issuer": insight.issuer or "Unknown",
                    "published_date": (
                        str(insight.published_date) if insight.published_date else ""
                    ),
                    "status": insight.status or "new",
                    "summary": insight.summary or "",
                    "editing": False,
                }

            card = create_insight_card(insight_data)
            insight_cards.append(card)
            serialized_store.append(json.dumps(insight_data))

        return html.Div(insight_cards), serialized_store

    except Exception as e:
        logger.error(f"Error searching insights: {e}")

        return (
            html.Div(
                f"Search error: {str(e)}",
                style={
                    "backgroundColor": "rgba(239, 68, 68, 0.1)",
                    "border": "1px solid rgba(239, 68, 68, 0.3)",
                    "borderRadius": "8px",
                    "padding": "15px",
                    "color": "#fca5a5",
                    "textAlign": "center",
                },
            ),
            no_update,
        )


# Clear search callback
@callback(
    [
        Output("insights-search", "value"),
        Output("sort-dropdown", "value"),
        Output("issuer-filter", "value"),
        Output("date-range-filter", "start_date"),
        Output("date-range-filter", "end_date"),
    ],
    Input("clear-search", "n_clicks"),
    prevent_initial_call=True,
)
def clear_search_inputs(_):
    """Clear all search inputs when the clear icon is clicked."""
    return "", None, None, None, None


# Enhanced PDF upload callback with full processing
@callback(
    Output("output-pdf-upload", "children", allow_duplicate=True),
    Output("upload-pdf", "contents"),
    Input("upload-pdf", "contents"),
    State("upload-pdf", "filename"),
    State("upload-pdf", "last_modified"),
    prevent_initial_call=True,
)
def handle_enhanced_upload(
    contents: Optional[Any], filename: Optional[Any], last_modified: Optional[Any]
) -> Tuple[Any, Optional[str]]:
    """
    Enhanced PDF upload processing with validation, content extraction, and AI summarization.
    Supports single or multiple file uploads.
    """
    if contents is None or filename is None:
        raise PreventUpdate

    contents_list = contents if isinstance(contents, list) else [contents]
    filenames_list = filename if isinstance(filename, list) else [filename]
    modified_list = (
        last_modified
        if isinstance(last_modified, list)
        else [last_modified] * len(contents_list)
    )

    def _error_message(message: str) -> Tuple[html.Div, bool]:
        return (
            html.Div(
                [
                    html.I(
                        className="fas fa-exclamation-triangle",
                        style={"color": "#ef4444", "marginRight": "8px"},
                    ),
                    message,
                ],
                style={
                    "backgroundColor": "rgba(239, 68, 68, 0.1)",
                    "border": "1px solid rgba(239, 68, 68, 0.3)",
                    "borderRadius": "8px",
                    "padding": "15px",
                    "color": "#fca5a5",
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "center",
                },
            ),
            False,
        )

    def _process_single_file(
        content_item: str, file_name: str, modified_item: Optional[float]
    ) -> Tuple[html.Div, bool]:
        try:
            if modified_item is None:
                raise ValueError("Missing last modified timestamp for upload.")

            content_type, content_string = content_item.split(",", 1)
            decoded = base64.b64decode(content_string)

            if not isinstance(file_name, str) or not file_name.lower().endswith(".pdf"):
                return _error_message(f"{file_name}: Only PDF files are allowed.")

            if not decoded.startswith(b"%PDF-"):
                return _error_message(f"{file_name}: Invalid PDF file format.")

            try:
                published_date_str, issuer, name = file_name.rsplit("_", 2)
                name = name.rsplit(".", 1)[0]
                published_date = datetime.strptime(published_date_str, "%Y%m%d").date()
            except ValueError:
                return _error_message(
                    f"{file_name}: Filename must follow 'YYYYMMDD_issuer_title.pdf'."
                )

            with Session() as session:
                insight = Insights(
                    published_date=published_date,
                    issuer=issuer,
                    name=name,
                    status="processing",
                    pdf_content=decoded,
                )
                session.add(insight)
                session.flush()

                try:
                    if (
                        hasattr(Settings, "openai_secret_key")
                        and Settings.openai_secret_key
                    ):
                        summarizer = PDFSummarizer(Settings.openai_secret_key)
                        summary_text = summarizer.process_insights(decoded)
                        insight.summary = summary_text
                        insight.status = "completed"
                    else:
                        insight.summary = None
                        insight.status = "completed"
                except Exception as summary_exc:
                    logger.error(f"Error generating summary: {summary_exc}")
                    insight.summary = f"Summary generation failed: {str(summary_exc)}"
                    insight.status = "failed"

                insight_id = str(insight.id)

            success_card = html.Div(
                [
                    html.Div(
                        [
                            html.I(
                                className="fas fa-check-circle",
                                style={
                                    "color": "#10b981",
                                    "fontSize": "24px",
                                    "marginBottom": "8px",
                                },
                            ),
                            html.H5(
                                f"✅ {file_name} uploaded successfully!",
                                style={"color": "#10b981", "margin": "0 0 12px 0"},
                            ),
                        ],
                        style={"textAlign": "center", "marginBottom": "16px"},
                    ),
                    html.Div(
                        [
                            html.P(
                                [html.Strong("📄 Name: "), name],
                                style={"margin": "4px 0"},
                            ),
                            html.P(
                                [html.Strong("🏢 Issuer: "), issuer],
                                style={"margin": "4px 0"},
                            ),
                            html.P(
                                [
                                    html.Strong("📅 Published: "),
                                    published_date.strftime("%B %d, %Y"),
                                ],
                                style={"margin": "4px 0"},
                            ),
                            html.P(
                                [
                                    html.Strong("📁 File size: "),
                                    f"{len(decoded) / 1024:.2f} KB",
                                ],
                                style={"margin": "4px 0"},
                            ),
                            html.P(
                                [
                                    html.Strong("🆔 Insight ID: "),
                                    html.Code(
                                        insight_id,
                                        style={
                                            "backgroundColor": "#374151",
                                            "padding": "2px 6px",
                                            "borderRadius": "4px",
                                        },
                                    ),
                                ],
                                style={"margin": "4px 0"},
                            ),
                        ],
                        style={
                            "backgroundColor": "rgba(16, 185, 129, 0.05)",
                            "padding": "12px",
                            "borderRadius": "8px",
                            "border": "1px solid rgba(16, 185, 129, 0.2)",
                        },
                    ),
                ],
                style={
                    "backgroundColor": "rgba(16, 185, 129, 0.1)",
                    "border": "1px solid rgba(16, 185, 129, 0.3)",
                    "borderRadius": "12px",
                    "padding": "20px",
                    "color": "#6ee7b7",
                },
            )

            return success_card, True

        except Exception as exc:
            logger.exception("Error processing PDF upload")
            error_card = html.Div(
                [
                    html.I(
                        className="fas fa-exclamation-triangle",
                        style={
                            "color": "#ef4444",
                            "fontSize": "24px",
                            "marginBottom": "8px",
                        },
                    ),
                    html.H5(
                        f"❌ Error processing {file_name}",
                        style={"color": "#ef4444", "margin": "0 0 12px 0"},
                    ),
                    html.P(
                        str(exc),
                        style={
                            "margin": "0",
                            "fontFamily": "monospace",
                            "fontSize": "14px",
                        },
                    ),
                ],
                style={
                    "backgroundColor": "rgba(239, 68, 68, 0.1)",
                    "border": "1px solid rgba(239, 68, 68, 0.3)",
                    "borderRadius": "12px",
                    "padding": "20px",
                    "color": "#fca5a5",
                    "textAlign": "center",
                },
            )

            return error_card, False

    results = [
        _process_single_file(content_item, file_name, modified_item)
        for content_item, file_name, modified_item in zip(
            contents_list, filenames_list, modified_list
        )
    ]

    message_cards = [card for card, _ in results]
    total_files = len(results)
    success_count = sum(1 for _, is_successful in results if is_successful)
    failure_count = total_files - success_count

    progress_value = int((success_count / total_files) * 100) if total_files > 0 else 0
    if failure_count == 0:
        progress_color = "teal"
        status_text = "All uploads completed successfully."
    elif success_count == 0:
        progress_color = "red"
        status_text = "Uploads failed. Please review the errors below."
    else:
        progress_color = "yellow"
        status_text = "Uploads partially completed. See details below."

    summary_panel = dmc.Paper(
        [
            dmc.Group(
                [
                    DashIconify(icon="carbon:time", width=24, color="#38bdf8"),
                    dmc.Stack(
                        [
                            dmc.Text(
                                "Processing complete", fw=600, size="sm", c="gray.1"
                            ),
                            dmc.Text(
                                f"{status_text} ({success_count}/{total_files} successful)",
                                size="xs",
                                c="gray.5",
                            ),
                        ],
                        gap=0,
                    ),
                ],
                gap="md",
            ),
            dmc.Progress(
                value=progress_value, color=progress_color, size="sm", mt="sm"
            ),
        ],
        radius="md",
        withBorder=True,
        shadow="sm",
        padding="md",
        style={"backgroundColor": "#0f172a"},
    )

    return (
        html.Div(
            [
                summary_panel,
                html.Div(message_cards, style={"display": "grid", "gap": "16px"}),
            ],
            style={"display": "grid", "gap": "20px"},
        ),
        None,
    )


# Delete insight callback
@callback(
    Output("insights-container", "children", allow_duplicate=True),
    Input({"type": "delete-insight-button", "index": ALL}, "n_clicks"),
    State("insights-container", "children"),
    prevent_initial_call=True,
)
def delete_insight(n_clicks_list, current_children):
    """Handle insight deletion"""
    if not any(n_clicks_list):
        raise PreventUpdate

    try:
        # Find which button was clicked
        ctx = dash.callback_context
        if not ctx.triggered:
            raise PreventUpdate

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        insight_id = json.loads(button_id)["index"]

        # Delete from database using SQLAlchemy
        from ix.db.conn import Session
        from ix.db.models import Insights

        with Session() as session:
            insight_to_delete = (
                session.query(Insights).filter(Insights.id == insight_id).first()
            )
            if insight_to_delete:
                session.delete(insight_to_delete)
                session.commit()

        # Show success message
        success_message = html.Div(
            [
                html.I(
                    className="fas fa-check-circle",
                    style={"color": "#10b981", "marginRight": "8px"},
                ),
                "Insight deleted successfully.",
            ],
            style={
                "backgroundColor": "rgba(16, 185, 129, 0.1)",
                "border": "1px solid rgba(16, 185, 129, 0.3)",
                "borderRadius": "8px",
                "padding": "15px",
                "color": "#6ee7b7",
                "textAlign": "center",
                "marginBottom": "15px",
                "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
            },
        )

        # Reload insights
        insights = get_insights()
        insight_cards = []

        for insight in insights:
            insight_data = {
                "id": str(insight.id),
                "name": insight.name or "Untitled",
                "issuer": insight.issuer or "Unknown",
                "published_date": (
                    str(insight.published_date) if insight.published_date else ""
                ),
                "status": insight.status or "new",
                "summary": insight.summary or "",
                "editing": False,
            }

            card = create_insight_card(insight_data)
            insight_cards.append(card)

        return [success_message] + insight_cards

    except Exception as e:
        logger.error(f"Error deleting insight: {e}")

        error_message = html.Div(
            f"Delete failed: {str(e)}",
            style={
                "backgroundColor": "rgba(239, 68, 68, 0.1)",
                "border": "1px solid rgba(239, 68, 68, 0.3)",
                "borderRadius": "8px",
                "padding": "15px",
                "color": "#fca5a5",
                "textAlign": "center",
                "marginBottom": "15px",
            },
        )

        return [error_message] + (current_children if current_children else [])


# Modal display callback for enhanced summary viewing
@callback(
    Output("insight-modal", "is_open"),
    Output("modal-body-content", "children"),
    Input({"type": "insight-card-clickable", "index": ALL}, "n_clicks"),
    Input("close-modal", "n_clicks"),
    State("insight-modal", "is_open"),
    State("insights-data", "data"),
    prevent_initial_call=True,
)
def display_enhanced_modal(
    n_clicks_list: List[Optional[int]],
    close_n: Optional[int],
    is_open: bool,
    insights_data: List[str],
) -> Tuple[bool, Any]:
    """
    Enhanced modal display with improved summary viewing.
    Shows detailed insight summary with better formatting.
    """
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    triggered = ctx.triggered[0]

    # Handle close modal
    if "close-modal" in triggered["prop_id"]:
        return False, no_update

    # Handle card click to open modal
    if not any(n_clicks_list):
        raise PreventUpdate

    try:
        triggered_id = json.loads(triggered["prop_id"].split(".")[0])
        insight_id = triggered_id["index"]
    except Exception:
        return is_open, no_update

    # Get insight details from insights_data store (following wx pattern)
    insight_data = None
    for insight_json in insights_data or []:
        try:
            parsed_insight = json.loads(insight_json)
            if str(parsed_insight.get("id")) == str(insight_id):
                insight_data = parsed_insight
                break
        except Exception:
            continue

    # Fallback to database query if not found in store
    if not insight_data:
        try:
            from ix.db.conn import Session
            from ix.db.models import Insights

            with Session() as session:
                insight = (
                    session.query(Insights).filter(Insights.id == insight_id).first()
                )
                if not insight:
                    return False, html.Div(
                        "Insight not found.",
                        style={
                            "color": "#ef4444",
                            "textAlign": "center",
                            "padding": "20px",
                        },
                    )
                # Extract attributes while in session
                insight_data = {
                    "id": str(insight.id),
                    "name": insight.name or "Untitled",
                    "issuer": insight.issuer or "Unknown",
                    "published_date": (
                        str(insight.published_date) if insight.published_date else ""
                    ),
                    "summary": insight.summary or "No summary available.",
                    "status": insight.status or "new",
                    "editing": False,
                }
        except Exception as e:
            logger.error(f"Error fetching insight {insight_id}: {e}")
            return False, html.Div(
                "Error loading insight.",
                style={"color": "#ef4444", "textAlign": "center", "padding": "20px"},
            )

    # Format summary content with enhanced styling
    summary_content = html.Div(
        [
            # Header with insight details
            html.Div(
                [
                    html.H4(
                        insight_data.get("name", "Untitled"),
                        style={
                            "color": "#ffffff",
                            "marginBottom": "8px",
                            "borderBottom": "2px solid #3b82f6",
                            "paddingBottom": "8px",
                        },
                    ),
                    html.Div(
                        [
                            html.Span(
                                f"📅 {insight_data.get('published_date', 'Unknown Date')}",
                                style={
                                    "color": "#94a3b8",
                                    "marginRight": "16px",
                                    "fontSize": "14px",
                                },
                            ),
                            html.Span(
                                f"🏢 {insight_data.get('issuer', 'Unknown Issuer')}",
                                style={
                                    "color": "#3b82f6",
                                    "fontSize": "14px",
                                    "fontWeight": "500",
                                },
                            ),
                        ],
                        style={"marginBottom": "20px"},
                    ),
                ]
            ),
            # Summary content
            html.Div(
                [
                    html.H6(
                        "📋 Summary",
                        style={
                            "color": "#ffffff",
                            "marginBottom": "12px",
                            "fontSize": "16px",
                            "fontWeight": "600",
                        },
                    ),
                    html.Div(
                        insight_data.get("summary", "No summary available."),
                        style={
                            "color": "#e2e8f0",
                            "lineHeight": "1.7",
                            "fontSize": "15px",
                            "backgroundColor": "#1e293b",
                            "padding": "16px",
                            "borderRadius": "8px",
                            "border": "1px solid #475569",
                            "whiteSpace": "pre-wrap",
                        },
                    ),
                ]
            ),
            # Metadata section
            html.Div(
                [
                    html.Hr(style={"borderColor": "#475569", "margin": "20px 0"}),
                    html.H6(
                        "📊 Metadata",
                        style={
                            "color": "#ffffff",
                            "marginBottom": "12px",
                            "fontSize": "14px",
                            "fontWeight": "600",
                        },
                    ),
                    html.Div(
                        [
                            html.P(
                                [
                                    html.Strong("Status: "),
                                    html.Span(
                                        insight_data.get("status", "unknown").title(),
                                        style={
                                            "color": (
                                                "#10b981"
                                                if insight_data.get("status")
                                                == "completed"
                                                else (
                                                    "#f59e0b"
                                                    if insight_data.get("status")
                                                    == "processing"
                                                    else (
                                                        "#ef4444"
                                                        if insight_data.get("status")
                                                        == "failed"
                                                        else "#3b82f6"
                                                    )
                                                )
                                            ),
                                            "fontWeight": "500",
                                        },
                                    ),
                                ],
                                style={"margin": "4px 0", "fontSize": "13px"},
                            ),
                            html.P(
                                [
                                    html.Strong("Document ID: "),
                                    html.Code(
                                        str(insight_data.get("id", "unknown")),
                                        style={
                                            "backgroundColor": "#374151",
                                            "padding": "2px 6px",
                                            "borderRadius": "4px",
                                            "fontSize": "12px",
                                        },
                                    ),
                                ],
                                style={"margin": "4px 0", "fontSize": "13px"},
                            ),
                        ]
                    ),
                ]
            ),
        ]
    )

    return True, summary_content


@callback(
    Output("insights-data", "data", allow_duplicate=True),
    Output("insights-container", "children", allow_duplicate=True),
    Output("summary-edit-context", "data"),
    Input({"type": "edit-summary-button", "index": ALL}, "n_clicks"),
    Input({"type": "inline-summary-save", "index": ALL}, "n_clicks"),
    Input({"type": "inline-summary-cancel", "index": ALL}, "n_clicks"),
    State("insights-data", "data"),
    State({"type": "inline-summary-editor", "index": ALL}, "value"),
    State({"type": "inline-title-input", "index": ALL}, "value"),
    State({"type": "inline-issuer-input", "index": ALL}, "value"),
    State({"type": "inline-date-input", "index": ALL}, "value"),
    prevent_initial_call=True,
)
def handle_inline_summary_actions(
    _edit_clicks: List[Optional[int]],
    _save_clicks: List[Optional[int]],
    _cancel_clicks: List[Optional[int]],
    insights_data: Optional[List[str]],
    _editor_values: List[Optional[str]],
    _title_values: List[Optional[str]],
    _issuer_values: List[Optional[str]],
    _date_values: List[Optional[str]],
):
    """Handle inline summary editing actions (edit, save, cancel)."""

    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate

    triggered = ctx.triggered[0]
    triggered_prop = triggered["prop_id"]
    triggered_raw_id = triggered_prop.split(".")[0]

    if not triggered_raw_id:
        raise PreventUpdate

    try:
        triggered_id = json.loads(triggered_raw_id)
    except Exception:
        raise PreventUpdate

    action_type = triggered_id.get("type")
    insight_id = str(triggered_id.get("index"))

    if not insight_id:
        raise PreventUpdate

    # Deserialize insight records from the store
    records: List[Dict[str, Any]] = []
    target_record: Optional[Dict[str, Any]] = None

    for record in insights_data or []:
        try:
            parsed = json.loads(record) if isinstance(record, str) else dict(record)
        except Exception:
            continue

        parsed.setdefault("editing", False)
        if str(parsed.get("id")) == insight_id:
            target_record = parsed
        records.append(parsed)

    # Fallback to database lookup if record missing from store
    if target_record is None:
        try:
            with Session() as session:
                insight = (
                    session.query(Insights).filter(Insights.id == insight_id).first()
                )
                if insight:
                    target_record = {
                        "id": str(insight.id),
                        "name": insight.name or "Untitled",
                        "issuer": insight.issuer or "Unknown",
                        "published_date": (
                            str(insight.published_date)
                            if insight.published_date
                            else ""
                        ),
                        "status": insight.status or "new",
                        "summary": insight.summary or "",
                        "editing": False,
                    }
                    records.append(target_record)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error(f"Failed to load insight {insight_id} for editing: {exc}")
            raise PreventUpdate

    if target_record is None:
        raise PreventUpdate

    editor_state_map: Dict[str, Optional[str]] = {}
    title_state_map: Dict[str, Optional[str]] = {}
    issuer_state_map: Dict[str, Optional[str]] = {}
    date_state_map: Dict[str, Optional[str]] = {}
    for state_key, value in ctx.states.items():
        if not state_key.endswith(".value"):
            continue
        try:
            state_id = json.loads(state_key.split(".")[0])
        except Exception:
            continue
        index_key = str(state_id.get("index"))
        state_type = state_id.get("type")
        if state_type == "inline-summary-editor":
            editor_state_map[index_key] = value
        elif state_type == "inline-title-input":
            title_state_map[index_key] = value
        elif state_type == "inline-issuer-input":
            issuer_state_map[index_key] = value
        elif state_type == "inline-date-input":
            date_state_map[index_key] = value

    # Dash may not include component states in ctx.states (e.g., after recent renders);
    # fall back to the raw State inputs to ensure we capture the latest values.
    if _title_values is not None:
        for idx, value in enumerate(_title_values or []):
            if idx < len(records):
                record_id = str(records[idx].get("id"))
                if record_id and record_id not in title_state_map:
                    title_state_map[record_id] = value

    if _issuer_values is not None:
        for idx, value in enumerate(_issuer_values or []):
            if idx < len(records):
                record_id = str(records[idx].get("id"))
                if record_id and record_id not in issuer_state_map:
                    issuer_state_map[record_id] = value

    if _date_values is not None:
        for idx, value in enumerate(_date_values or []):
            if idx < len(records):
                record_id = str(records[idx].get("id"))
                if record_id and record_id not in date_state_map:
                    date_state_map[record_id] = value

    if _editor_values is not None:
        for idx, value in enumerate(_editor_values or []):
            if idx < len(records):
                record_id = str(records[idx].get("id"))
                if record_id and record_id not in editor_state_map:
                    editor_state_map[record_id] = value

    summary_edit_context: Optional[Dict[str, Any]] = None

    if action_type == "edit-summary-button":
        for record in records:
            if str(record.get("id")) == insight_id:
                record["editing"] = True
                record["draft_summary"] = record.get("summary", "") or ""
                record["draft_title"] = record.get("name") or ""
                record["draft_issuer"] = record.get("issuer") or ""
                existing_date = record.get("published_date") or ""
                record["draft_date"] = (
                    existing_date[:10]
                    if isinstance(existing_date, str) and existing_date
                    else ""
                )
                summary_edit_context = {
                    "id": insight_id,
                    "name": record.get("name") or "Untitled insight",
                }
            else:
                record["editing"] = False
                record.pop("draft_summary", None)
                record.pop("draft_title", None)
                record.pop("draft_issuer", None)
                record.pop("draft_date", None)

    elif action_type == "inline-summary-cancel":
        for record in records:
            record["editing"] = False
            record.pop("draft_summary", None)
            record.pop("draft_title", None)
            record.pop("draft_issuer", None)
            record.pop("draft_date", None)

    elif action_type == "inline-summary-save":
        new_summary = (editor_state_map.get(insight_id) or "").strip()
        new_title = title_state_map.get(
            insight_id,
            target_record.get("draft_title", target_record.get("name", "")),
        )
        new_issuer = issuer_state_map.get(
            insight_id,
            target_record.get("draft_issuer", target_record.get("issuer", "")),
        )
        new_date = date_state_map.get(
            insight_id,
            target_record.get("draft_date", target_record.get("published_date", "")),
        )

        existing_name = target_record.get("name", "")
        existing_issuer = target_record.get("issuer", "")
        existing_date = target_record.get("published_date", "")

        new_title = (new_title or existing_name or "").strip()
        new_issuer = (new_issuer or existing_issuer or "").strip()
        new_date = (
            new_date or (existing_date[:10] if isinstance(existing_date, str) else "")
        ).strip()

        metadata_error: Optional[str] = None
        updated_metadata: Optional[Dict[str, Optional[str]]] = None

        try:
            updated_metadata = update_insight_metadata(
                id=insight_id,
                name=new_title,
                issuer=new_issuer,
                published_date=new_date if new_date else None,
            )
            updated_record = set_insight_summary(insight_id, new_summary)
        except Exception as exc:
            metadata_error = str(exc)
            logger.error(f"Failed to update insight {insight_id}: {metadata_error}")
            for record in records:
                if str(record.get("id")) == insight_id:
                    record["editing"] = True
                    record["draft_summary"] = new_summary or target_record.get(
                        "summary", ""
                    )
                    record["draft_title"] = new_title or target_record.get(
                        "draft_title", target_record.get("name", "")
                    )
                    record["draft_issuer"] = new_issuer or target_record.get(
                        "draft_issuer", target_record.get("issuer", "")
                    )
                    record["draft_date"] = new_date or target_record.get(
                        "draft_date", target_record.get("published_date", "")
                    )
            summary_edit_context = {
                "id": insight_id,
                "name": target_record.get("name") or "Untitled insight",
                "error": metadata_error,
            }
        else:
            updated_summary = updated_record.get("summary", new_summary)
            updated_status = updated_record.get("status")
            updated_name = (
                updated_metadata.get("name") if updated_metadata else new_title
            ) or existing_name
            updated_issuer = (
                updated_metadata.get("issuer") if updated_metadata else new_issuer
            ) or existing_issuer
            updated_date = (
                updated_metadata.get("published_date") if updated_metadata else new_date
            ) or existing_date

            for record in records:
                if str(record.get("id")) == insight_id:
                    record["summary"] = updated_summary
                    record["name"] = updated_name or ""
                    record["issuer"] = updated_issuer or ""
                    record["published_date"] = updated_date or ""
                    if updated_status:
                        record["status"] = updated_status
                    record["editing"] = False
                    record.pop("draft_summary", None)
                    record.pop("draft_title", None)
                    record.pop("draft_issuer", None)
                    record.pop("draft_date", None)
                else:
                    record["editing"] = False
                    record.pop("draft_summary", None)
                    record.pop("draft_title", None)
                    record.pop("draft_issuer", None)
                    record.pop("draft_date", None)

    else:
        raise PreventUpdate

    # Serialize updated records back into the store
    serialized_updates: List[str] = []
    rendered_cards: List[Any] = []

    for record in records:
        rendered_cards.append(create_insight_card(record))
        record_copy = record.copy()
        if not record_copy.get("editing"):
            record_copy.pop("draft_summary", None)
            record_copy.pop("draft_title", None)
            record_copy.pop("draft_issuer", None)
            record_copy.pop("draft_date", None)
        serialized_updates.append(json.dumps(record_copy))

    return serialized_updates, html.Div(rendered_cards), summary_edit_context
