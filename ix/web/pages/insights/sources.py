"""
Enhanced Insight Sources Component
Modern design with improved layout, better organization, and enhanced functionality.
"""

import json
from ix.db import InsightSource
from dash import html, dcc, callback_context, Output, Input, State, ALL, callback
from dash.exceptions import PreventUpdate
from datetime import datetime
import dash_bootstrap_components as dbc

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


def _format_last_visited(last_visited_str: str) -> str:
    """Format last visited timestamp for display."""
    if not last_visited_str:
        return "Never"

    try:
        # Parse the ISO format timestamp
        dt = datetime.fromisoformat(last_visited_str.replace("Z", "+00:00"))
        now = datetime.now()
        diff = now - dt.replace(tzinfo=None)

        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "Just now"
    except:
        return "Unknown"


def _get_frequency_color(frequency: str) -> str:
    """Get color based on frequency."""
    frequency_colors = {
        "daily": COLORS["success"],
        "weekly": COLORS["primary"],
        "monthly": COLORS["warning"],
        "quarterly": COLORS["secondary"],
        "yearly": COLORS["danger"],
    }
    return frequency_colors.get(frequency.lower(), COLORS["secondary"])


def _get_frequency_icon(frequency: str) -> str:
    """Get icon based on frequency."""
    frequency_icons = {
        "daily": "fas fa-calendar-day",
        "weekly": "fas fa-calendar-week",
        "monthly": "fas fa-calendar-alt",
        "quarterly": "fas fa-calendar-check",
        "yearly": "fas fa-calendar",
    }
    return frequency_icons.get(frequency.lower(), "fas fa-calendar")


# Completely Redesigned Sources Layout - Modern & Clean
layout = html.Div(
    [
        # Compact Header
        html.Div(
            [
                html.Div(
                    [
                        html.I(className="fas fa-rss", style={"color": "#3b82f6", "fontSize": "14px", "marginRight": "8px"}),
                        html.Span("🔗 Sources", style={"color": "#ffffff", "fontSize": "14px", "fontWeight": "600"}),
                        html.Button(
                            [html.I(className="fas fa-plus", style={"fontSize": "10px"})],
                            id="add-source-btn",
                            style={
                                "backgroundColor": "#10b981",
                                "border": "none",
                                "borderRadius": "4px",
                                "color": "#ffffff",
                                "padding": "4px 6px",
                                "cursor": "pointer",
                                "display": "flex",
                                "alignItems": "center",
                                "minWidth": "20px",
                                "height": "20px",
                                "marginLeft": "8px",
                            },
                            title="Add source",
                            n_clicks=0,
                        ),
                    ],
                    style={"display": "flex", "alignItems": "center"},
                ),
            ],
            style={
                "background": "linear-gradient(135deg, #1e293b 0%, #334155 100%)",
                "padding": "8px 12px",
                "borderRadius": "8px 8px 0 0",
                "border": "1px solid #475569",
                "borderBottom": "none",
            },
        ),
        # Compact Sources Container
        html.Div(
            id="sources-container",
            style={
                "backgroundColor": "#0f172a",
                "border": "1px solid #475569",
                "borderTop": "none",
                "borderRadius": "0 0 8px 8px",
                "minHeight": "150px",
                "maxHeight": "250px",
                "overflowY": "auto",
                "overflowX": "hidden",
            },
        ),
        # Auto-refresh (hidden)
        dcc.Interval(
            id="interval-refresh",
            interval=30 * 1000,
            n_intervals=0,
        ),
        # Add/Edit Source Modal
        dbc.Modal(
            [
                dbc.ModalHeader(
                    [
                        html.H4(
                            "Add Source",
                            id="source-modal-title",
                            style={"color": "#ffffff", "margin": "0"},
                        ),
                    ],
                    style={
                        "backgroundColor": "#1e293b",
                        "borderBottom": "1px solid #475569",
                    },
                ),
                dbc.ModalBody(
                    [
                        # Source Name
                        html.Div(
                            [
                                html.Label(
                                    "Source Name",
                                    style={
                                        "color": "#ffffff",
                                        "fontWeight": "600",
                                        "marginBottom": "8px",
                                        "display": "block",
                                    },
                                ),
                                dbc.Input(
                                    id="source-name-input",
                                    placeholder="e.g. Bloomberg Terminal",
                                    style={
                                        "backgroundColor": "#0f172a",
                                        "border": "1px solid #475569",
                                        "color": "#ffffff",
                                        "borderRadius": "6px",
                                    },
                                ),
                            ],
                            style={"marginBottom": "16px"},
                        ),
                        # Source URL
                        html.Div(
                            [
                                html.Label(
                                    "Source URL",
                                    style={
                                        "color": "#ffffff",
                                        "fontWeight": "600",
                                        "marginBottom": "8px",
                                        "display": "block",
                                    },
                                ),
                                dbc.Input(
                                    id="source-url-input",
                                    placeholder="https://example.com",
                                    type="url",
                                    style={
                                        "backgroundColor": "#0f172a",
                                        "border": "1px solid #475569",
                                        "color": "#ffffff",
                                        "borderRadius": "6px",
                                    },
                                ),
                            ],
                            style={"marginBottom": "16px"},
                        ),
                        # Frequency
                        html.Div(
                            [
                                html.Label(
                                    "Update Frequency",
                                    style={
                                        "color": "#ffffff",
                                        "fontWeight": "600",
                                        "marginBottom": "8px",
                                        "display": "block",
                                    },
                                ),
                                dbc.Select(
                                    id="source-frequency-select",
                                    options=[
                                        {"label": "Daily", "value": "Daily"},
                                        {"label": "Weekly", "value": "Weekly"},
                                        {"label": "Monthly", "value": "Monthly"},
                                        {"label": "Quarterly", "value": "Quarterly"},
                                        {"label": "Yearly", "value": "Yearly"},
                                        {
                                            "label": "Unclassified",
                                            "value": "Unclassified",
                                        },
                                    ],
                                    value="Daily",
                                    style={
                                        "backgroundColor": "#0f172a",
                                        "border": "1px solid #475569",
                                        "color": "#ffffff",
                                        "borderRadius": "6px",
                                    },
                                ),
                            ],
                            style={"marginBottom": "16px"},
                        ),
                        # Remark
                        html.Div(
                            [
                                html.Label(
                                    "Remark (Optional)",
                                    style={
                                        "color": "#ffffff",
                                        "fontWeight": "600",
                                        "marginBottom": "8px",
                                        "display": "block",
                                    },
                                ),
                                dbc.Textarea(
                                    id="source-remark-input",
                                    placeholder="Additional notes about this source...",
                                    rows=3,
                                    style={
                                        "backgroundColor": "#0f172a",
                                        "border": "1px solid #475569",
                                        "color": "#ffffff",
                                        "borderRadius": "6px",
                                        "resize": "vertical",
                                    },
                                ),
                            ],
                        ),
                    ],
                    style={
                        "backgroundColor": "#0f172a",
                        "padding": "24px",
                    },
                ),
                dbc.ModalFooter(
                    [
                        dbc.Button(
                            "Cancel",
                            id="source-modal-cancel",
                            color="secondary",
                            size="sm",
                            style={"marginRight": "8px"},
                            n_clicks=0,
                        ),
                        dbc.Button(
                            "Save Source",
                            id="source-modal-save",
                            color="success",
                            size="sm",
                            n_clicks=0,
                        ),
                    ],
                    style={
                        "backgroundColor": "#1e293b",
                        "borderTop": "1px solid #475569",
                    },
                ),
            ],
            id="source-modal",
            is_open=False,
            centered=True,
            size="md",
        ),
        # Hidden stores for modal state
        dcc.Store(id="source-edit-id", data=None),
    ],
    style={
        "marginBottom": "20px",
        "boxShadow": "0 4px 20px rgba(0, 0, 0, 0.4)",
    },
)


@callback(
    Output("sources-container", "children"),
    [
        Input({"type": "visit-btn", "index": ALL}, "n_clicks"),
        Input({"type": "delete-source-btn", "index": ALL}, "n_clicks"),
        Input("interval-refresh", "n_intervals"),
        Input("source-modal-save", "n_clicks"),
    ],
    prevent_initial_call=False,
)
def update_sources(visit_clicks, delete_clicks, n_intervals, save_clicks):
    """Enhanced callback to update sources with modern design."""
    ctx = callback_context
    if ctx.triggered:
        trigger_prop = ctx.triggered[0]["prop_id"]

        # Handle button clicks
        if trigger_prop.startswith("{"):
            try:
                json_str = trigger_prop.split(".")[0].replace("'", '"')
                triggered_id = json.loads(json_str)
                source_id = triggered_id["index"]
                button_type = triggered_id["type"]

                if button_type == "visit-btn":
                    # Update last_visited when link is clicked
                    insight_source = InsightSource.find_one({"id": source_id}).run()
                    if insight_source:
                        new_time = datetime.now()
                        insight_source.set({"last_visited": new_time})

                elif button_type == "delete-source-btn":
                    # Delete the source
                    insight_source = InsightSource.find_one({"id": source_id}).run()
                    if insight_source:
                        insight_source.delete()

            except Exception as e:
                print(f"Error handling button click: {e}")

    # Fetch sources sorted by last_visited in descending order (most recent first)
    sources = InsightSource.find({}).sort("-last_visited").run()

    if not sources:
        return html.Div(
            [
                html.Div(
                    [
                        html.I(
                            className="fas fa-rss",
                            style={
                                "color": "#475569",
                                "fontSize": "32px",
                                "marginBottom": "12px",
                            },
                        ),
                        html.Div(
                            "No sources configured",
                            style={
                                "color": "#94a3b8",
                                "fontSize": "14px",
                                "fontWeight": "500",
                                "marginBottom": "4px",
                            },
                        ),
                        html.Div(
                            "Add sources to track financial data providers",
                            style={
                                "color": "#64748b",
                                "fontSize": "12px",
                                "fontWeight": "400",
                            },
                        ),
                    ],
                    style={
                        "textAlign": "center",
                        "padding": "40px 20px",
                        "display": "flex",
                        "flexDirection": "column",
                        "alignItems": "center",
                        "justifyContent": "center",
                    },
                )
            ],
        )

    children = []
    for source in sources:
        source_dict = source.model_dump()
        source_dict["_id"] = str(source.id)

        # Format last visited
        last_visited = source_dict.get("last_visited", "")
        if isinstance(last_visited, datetime):
            last_visited = last_visited.replace(microsecond=0).isoformat(" ")

        last_visited_display = _format_last_visited(last_visited)
        frequency = source_dict.get("frequency", "Unclassified")
        frequency_color = _get_frequency_color(frequency)

        # Create sleek, minimal source item
        source_item = html.Div(
            [
                # Main content row
                html.Div(
                    [
                        # Left: Source info
                        html.Div(
                            [
                                html.Div(
                                    source_dict.get("name", "Unnamed Source"),
                                    style={
                                        "color": "#ffffff",
                                        "fontSize": "12px",
                                        "fontWeight": "600",
                                        "marginBottom": "2px",
                                        "lineHeight": "1.2",
                                    },
                                ),
                                html.Div(
                                    [
                                        # Frequency pill
                                        html.Span(
                                            frequency.title(),
                                            style={
                                                "backgroundColor": frequency_color,
                                                "color": "#ffffff",
                                                "padding": "1px 6px",
                                                "borderRadius": "8px",
                                                "fontSize": "9px",
                                                "fontWeight": "600",
                                                "textTransform": "uppercase",
                                                "letterSpacing": "0.3px",
                                                "marginRight": "6px",
                                            },
                                        ),
                                        # Last visited
                                        html.Span(
                                            last_visited_display,
                                            style={
                                                "color": "#64748b",
                                                "fontSize": "10px",
                                                "fontWeight": "500",
                                            },
                                        ),
                                    ],
                                ),
                            ],
                            style={"flex": "1"},
                        ),
                        # Right: Action buttons
                        html.Div(
                            [
                                # Visit button - opens in new tab and tracks visits
                                dbc.Button(
                                    [
                                        html.I(
                                            className="fas fa-external-link-alt",
                                            style={"fontSize": "11px"},
                                        ),
                                    ],
                                    href=source_dict.get("url", "#"),
                                    external_link=True,
                                    target="_blank",
                                    id={
                                        "type": "visit-btn",
                                        "index": source_dict["_id"],
                                    },
                                    n_clicks=0,
                                    style={
                                        "backgroundColor": "#3b82f6",
                                        "border": "none",
                                        "borderRadius": "6px",
                                        "color": "#ffffff",
                                        "padding": "6px 8px",
                                        "cursor": "pointer",
                                        "transition": "all 0.2s ease",
                                        "display": "flex",
                                        "alignItems": "center",
                                        "justifyContent": "center",
                                        "minWidth": "28px",
                                        "height": "28px",
                                        "marginRight": "4px",
                                        "textDecoration": "none",
                                    },
                                    title=f"Visit {source_dict.get('name', 'source')}",
                                ),
                                # Edit button
                                html.Button(
                                    [
                                        html.I(
                                            className="fas fa-edit",
                                            style={"fontSize": "11px"},
                                        ),
                                    ],
                                    id={
                                        "type": "edit-source-btn",
                                        "index": source_dict["_id"],
                                    },
                                    n_clicks=0,
                                    style={
                                        "backgroundColor": "#f59e0b",
                                        "border": "none",
                                        "borderRadius": "6px",
                                        "color": "#ffffff",
                                        "padding": "6px 8px",
                                        "cursor": "pointer",
                                        "transition": "all 0.2s ease",
                                        "display": "flex",
                                        "alignItems": "center",
                                        "justifyContent": "center",
                                        "minWidth": "28px",
                                        "height": "28px",
                                        "marginRight": "4px",
                                    },
                                    title=f"Edit {source_dict.get('name', 'source')}",
                                ),
                                # Delete button
                                html.Button(
                                    [
                                        html.I(
                                            className="fas fa-trash",
                                            style={"fontSize": "11px"},
                                        ),
                                    ],
                                    id={
                                        "type": "delete-source-btn",
                                        "index": source_dict["_id"],
                                    },
                                    n_clicks=0,
                                    style={
                                        "backgroundColor": "#ef4444",
                                        "border": "none",
                                        "borderRadius": "6px",
                                        "color": "#ffffff",
                                        "padding": "6px 8px",
                                        "cursor": "pointer",
                                        "transition": "all 0.2s ease",
                                        "display": "flex",
                                        "alignItems": "center",
                                        "justifyContent": "center",
                                        "minWidth": "28px",
                                        "height": "28px",
                                    },
                                    title=f"Delete {source_dict.get('name', 'source')}",
                                ),
                            ],
                            style={
                                "display": "flex",
                                "alignItems": "center",
                                "gap": "2px",
                            },
                        ),
                    ],
                    style={
                        "display": "flex",
                        "alignItems": "center",
                        "justifyContent": "space-between",
                        "gap": "12px",
                    },
                ),
            ],
            style={
                "padding": "8px 12px",
                "borderBottom": "1px solid #1e293b",
                "transition": "all 0.2s ease",
                "cursor": "pointer",
            },
            className="source-item-hover",
        )

        children.append(source_item)

    return children


# Modal control callbacks
@callback(
    [
        Output("source-modal", "is_open"),
        Output("source-modal-title", "children"),
        Output("source-name-input", "value"),
        Output("source-url-input", "value"),
        Output("source-frequency-select", "value"),
        Output("source-remark-input", "value"),
        Output("source-edit-id", "data"),
    ],
    [
        Input("add-source-btn", "n_clicks"),
        Input({"type": "edit-source-btn", "index": ALL}, "n_clicks"),
        Input("source-modal-cancel", "n_clicks"),
        Input("source-modal-save", "n_clicks"),
    ],
    [
        State("source-modal", "is_open"),
        State("source-name-input", "value"),
        State("source-url-input", "value"),
        State("source-frequency-select", "value"),
        State("source-remark-input", "value"),
        State("source-edit-id", "data"),
    ],
    prevent_initial_call=True,
)
def toggle_source_modal(
    add_clicks,
    edit_clicks,
    cancel_clicks,
    save_clicks,
    is_open,
    name_value,
    url_value,
    frequency_value,
    remark_value,
    edit_id,
):
    """Handle opening/closing and populating the source modal"""
    ctx = callback_context
    if not ctx.triggered:
        raise PreventUpdate

    trigger_prop = ctx.triggered[0]["prop_id"]
    trigger_value = ctx.triggered[0]["value"]

    # Check if this is a real user interaction (not initial load)
    if trigger_prop.endswith(".n_clicks"):
        # For n_clicks, only proceed if value is greater than 0
        if trigger_value is None or trigger_value <= 0:
            raise PreventUpdate

    # Handle add source button
    if "add-source-btn" in trigger_prop:
        return (
            True,
            "Add New Source",
            "",
            "",
            "Daily",
            "",
            None,
        )

    # Handle edit source button
    if "edit-source-btn" in trigger_prop:
        try:
            json_str = trigger_prop.split(".")[0].replace("'", '"')
            triggered_id = json.loads(json_str)
            source_id = triggered_id["index"]

            # Get source data
            source = InsightSource.find_one({"id": source_id}).run()
            if source:
                return (
                    True,
                    "Edit Source",
                    source.name,
                    source.url,
                    source.frequency,
                    source.remark or "",
                    str(source.id),
                )
        except Exception as e:
            print(f"Error loading source for edit: {e}")

    # Handle cancel or save
    if "source-modal-cancel" in trigger_prop:
        return (
            False,
            "Add New Source",
            "",
            "",
            "Daily",
            "",
            None,
        )

    if "source-modal-save" in trigger_prop:
        try:
            # Validate inputs
            if not name_value or not url_value:
                return (
                    is_open,
                    "Add New Source" if not edit_id else "Edit Source",
                    name_value or "",
                    url_value or "",
                    frequency_value or "Daily",
                    remark_value or "",
                    edit_id,
                )

            if edit_id:
                # Update existing source
                source = InsightSource.find_one({"id": edit_id}).run()
                if source:
                    source.set(
                        {
                            "name": name_value,
                            "url": url_value,
                            "frequency": frequency_value,
                            "remark": remark_value,
                        }
                    )
            else:
                # Create new source
                InsightSource(
                    name=name_value,
                    url=url_value,
                    frequency=frequency_value,
                    remark=remark_value,
                    last_visited=datetime.now(),
                ).create()

            # Close modal and clear form
            return (
                False,
                "Add New Source",
                "",
                "",
                "Daily",
                "",
                None,
            )

        except Exception as e:
            print(f"Error saving source: {e}")

    raise PreventUpdate
