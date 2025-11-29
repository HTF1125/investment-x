"""Insights Terminal - Next Gen Research Dashboard."""

from dash import html, dcc, Input, Output, State, callback, no_update as NO_UPDATE, ALL
import dash
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from ix.web.pages.insights.components import (
    create_all_modals,
    create_upload_button,
    create_upload_dropzone,
)

# Page size for grid rendering
GRID_PAGE_SIZE = 8

# Register page
dash.register_page(
    __name__, path="/insights", title="Research Terminal", name="Insights"
)

# Import callbacks to register them
from ix.web.pages.insights.callbacks import *  # noqa: F403, F401


# ============================================================================
# Components: Sidebar (Navigator)
# ============================================================================
def create_nav_item(icon: str, label: str, active: bool = False, count: str = None):
    return html.Div(
        [
            dmc.Group(
                [
                    DashIconify(icon=icon, width=18),
                    html.Span(label),
                ],
                gap="sm",
                style={"flex": 1},
            ),
            (
                dmc.Badge(
                    count,
                    size="xs",
                    variant="filled",
                    color="gray",
                    style={"opacity": 0.7},
                )
                if count
                else None
            ),
        ],
        className=f"nav-item {'active' if active else ''}",
    )


def create_sidebar() -> html.Div:
    return html.Div(
        [
            # Logo / Title Area
            dmc.Group(
                [
                    dmc.ThemeIcon(
                        DashIconify(icon="carbon:terminal", width=20),
                        size="lg",
                        radius="md",
                        variant="gradient",
                        gradient={"from": "blue", "to": "cyan"},
                    ),
                    dmc.Text(
                        "TERMINAL", size="lg", fw=700, style={"letterSpacing": "-0.5px"}
                    ),
                ],
                mb="xl",
            ),
            # Main Navigation
            html.Div("COLLECTIONS", className="section-header"),
            create_nav_item("carbon:copy", "All Insights", active=True),
            create_nav_item("carbon:star", "Favorites"),
            create_nav_item("carbon:time", "Recent"),
            create_nav_item("carbon:trash-can", "Trash"),
            dmc.Space(h="xl"),
            # Smart Filters
            html.Div("SMART FILTERS", className="section-header"),
            create_nav_item("carbon:chart-line", "Macro Strategy"),
            create_nav_item("carbon:earth", "Global Markets"),
            create_nav_item("carbon:chemistry", "Quant Research"),
            dmc.Space(h="xl"),
            # Sources / Publishers
            html.Div("SOURCES", className="section-header"),
            html.Div(id="insight-sources-list"),  # Populated by callback
        ],
        className="terminal-sidebar",
    )


# ============================================================================
# Components: Command Bar
# ============================================================================
def create_command_bar() -> html.Div:
    return html.Div(
        [
            dmc.Group(
                [
                    # Search Input
                    dmc.TextInput(
                        id="terminal-search",
                        placeholder="Search insights, issuers, or tags... (Ctrl+K)",
                        leftSection=DashIconify(
                            icon="carbon:search", width=20, color="#94a3b8"
                        ),
                        rightSection=dmc.Kbd("Ctrl + K"),
                        className="command-input",
                        style={"flex": 1, "maxWidth": "600px"},
                        size="md",
                        radius="md",
                    ),
                    # Action Buttons
                    dmc.Group(
                        [
                            create_upload_button(),
                        ],
                        gap="sm",
                    ),
                ],
                justify="space-between",
            )
        ],
        className="command-bar-container",
    )


# ============================================================================
# Main Feed Area
# ============================================================================
def create_feed_area() -> html.Div:
    return html.Div(
        [
            # Upload Zone (Hidden by default, toggled by button)
            create_upload_dropzone(),
            # Upload progress and results
            dcc.Loading(
                id="upload-processing-loader",
                type="circle",
                children=html.Div(id="output-pdf-upload"),
                parent_style={"marginTop": "12px"},
            ),
            # Content Grid
            html.Div(
                id="insights-grid-container",
                className="insight-grid",
                style={"marginTop": "20px"},
            ),
            # Load more button
            dmc.Center(
                dmc.Button(
                    "Load more",
                    id="load-more-insights",
                    variant="light",
                    leftSection=DashIconify(icon="carbon:chevron-down", width=16),
                    size="sm",
                ),
                style={"marginTop": "12px"},
                id="load-more-container",
            ),
            # Pagination (Hidden but functional for infinite scroll logic if needed)
            html.Div(
                dmc.Pagination(
                    id="insights-pagination",
                    total=1,
                    value=1,
                    style={"display": "none"},
                ),
            ),
        ],
        className="terminal-feed",
        id="feed-scroll-container",
    )


# ============================================================================
# Main Layout Construction
# ============================================================================
layout = html.Div(
    [
        # Store Components
        dcc.Store(id="insights-data", data=[]),
        dcc.Store(id="selected-insight-id", data=None),
        dcc.Store(id="current-page", data=1),
        dcc.Store(id="filter-config", data={"search": "", "no_summary": False}),
        dcc.Store(id="view-mode", data="grid"),  # 'grid' or 'list'
        dcc.Store(id="publishers-refresh-token", data=None),
        dcc.Interval(
            id="publishers-refresh-interval", interval=60 * 1000, n_intervals=0
        ),
        dcc.Store(id="total-count", data=0),  # Required for callbacks
        # Modals (Hidden)
        *create_all_modals(),
        # Layout Structure
        html.Div(
            [
                # Left Sidebar
                create_sidebar(),
                # Main Content Area (Column)
                html.Div(
                    [
                        create_command_bar(),
                        html.Div(
                            [
                                create_feed_area(),
                            ],
                            id="terminal-main-split",
                            className="terminal-grid",
                        ),
                    ],
                    style={
                        "display": "flex",
                        "flexDirection": "column",
                        "height": "100vh",
                        "overflow": "hidden",
                    },
                ),
            ],
            className="terminal-grid-outer",  # Renamed for clarity
            style={
                "display": "grid",
                "gridTemplateColumns": "260px 1fr",
                "height": "100vh",
                "overflow": "hidden",
            },
        ),
        # Hidden components for callback compatibility
        html.Div(id="insights-table-container", style={"display": "none"}),
        html.Div(id="row-click-handler", style={"display": "none"}),
        html.Div(id="dragdrop-handler", style={"display": "none"}),
        # Dummy div for keyboard shortcut callback
        html.Div(id="keyboard-shortcut-listener", style={"display": "none"}),
    ],
    className="insights-page-container",
)


# ============================================================================
# New Layout Callbacks
# ============================================================================


# Callback to render GRID content (replacing the old Table render)
@callback(
    Output("insights-grid-container", "children"),
    Input("insights-data", "data"),
    Input("current-page", "data"),
    State("view-mode", "data"),
    State("token-store", "data"),
)
def render_grid_feed(insights_data, current_page, view_mode, token_data):
    if not insights_data:
        return html.Div(
            dmc.Text("No insights found.", c="dimmed", ta="center"),
            style={"padding": "40px"},
        )

    from ix.web.pages.insights.utils.data_utils import deserialize_insights

    all_insights = deserialize_insights(insights_data)
    is_admin = bool(
        token_data and isinstance(token_data, dict) and token_data.get("is_admin")
    )

    # Determine how many to show (paged)
    try:
        page = int(current_page or 1)
    except Exception:
        page = 1
    end_idx = page * GRID_PAGE_SIZE
    insights_to_render = all_insights[:end_idx]

    cards = []
    for insight in insights_to_render:
        insight_id = str(insight.get("id"))
        summary_text = insight.get("summary") or "No summary available."
        hash_text = insight.get("hash") or ""

        # Create Card Component
        card = html.Div(
            [
                html.Div(
                    [
                        dmc.Badge(
                            insight.get("issuer", "Unknown"),
                            size="sm",
                            radius="sm",
                            variant="light",
                            color="blue",
                            style={
                                "whiteSpace": "normal",
                                "lineHeight": 1.2,
                                "maxWidth": "100%",
                            },
                        ),
                        dmc.Text(insight.get("published_date"), size="xs", c="dimmed"),
                    ],
                    className="card-meta",
                ),
                html.Div(insight.get("name"), className="card-title"),
                # Hash tag (full) under title when present
                (
                    dmc.Badge(
                        f"#{hash_text}",
                        size="xs",
                        variant="light",
                        color="cyan",
                        style={
                            "fontFamily": "monospace",
                            "wordBreak": "break-all",
                            "marginBottom": "6px",
                        },
                    )
                    if hash_text
                    else None
                ),
                # Short preview only (avoid long card)
                dmc.Text(
                    (
                        (summary_text[:180] + "...")
                        if len(summary_text) > 180
                        else summary_text
                    ),
                    size="sm",
                    c="dimmed",
                    style={"lineHeight": "1.6", "marginBottom": "8px"},
                ),
                html.Div(
                    [
                        dmc.Group(
                            [
                                dmc.Badge(
                                    "Macro", size="xs", variant="outline", color="gray"
                                ),
                                dmc.Anchor(
                                    dmc.Button(
                                        "View PDF",
                                        leftSection=DashIconify(
                                            icon="carbon:document-pdf", width=14
                                        ),
                                        variant="light",
                                        color="blue",
                                        size="xs",
                                    ),
                                    href=f"/api/download-pdf/{insight_id}",
                                    target="_blank",
                                    style={"textDecoration": "none"},
                                    className="pdf-link",
                                ),
                            ]
                            + (
                                [
                                    dmc.ActionIcon(
                                        DashIconify(icon="mdi:trash-outline", width=16),
                                        color="red",
                                        variant="light",
                                        id={
                                            "type": "delete-insight-button",
                                            "index": insight_id,
                                        },
                                        title="Delete (admin only)",
                                        className="stop-prop",
                                    )
                                ]
                                if is_admin
                                else []
                            ),
                            gap="xs",
                        )
                    ],
                    className="card-tags",
                ),
            ],
            className="insight-card",
            id={"type": "insight-card", "index": insight_id},
            **{"data-insight-id": insight_id, "style": {"cursor": "pointer"}},
        )
        cards.append(card)

    return cards


# Clientside callback for keyboard shortcuts (Ctrl+K)
dash.clientside_callback(
    """
    function(trigger) {
        // Remove existing listener if any (to avoid duplicates on hot reload)
        if (window.ctrlKListener) {
            document.removeEventListener('keydown', window.ctrlKListener);
        }

        window.ctrlKListener = function(e) {
            // Check for Ctrl+K or Cmd+K
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const searchInput = document.getElementById('terminal-search');
                if (searchInput) {
                    searchInput.focus();
                }
            }
        };

        document.addEventListener('keydown', window.ctrlKListener);
        return window.dash_clientside.no_update;
    }
    """,
    Output("keyboard-shortcut-listener", "children"),  # Dummy output
    Input("terminal-search", "id"),  # Trigger on load
)

# Prevent card click bubbling when clicking PDF links
dash.clientside_callback(
    """
    function(children) {
        setTimeout(function() {
            const links = document.querySelectorAll('.pdf-link');
            const blockers = document.querySelectorAll('.stop-prop');
            links.forEach(function(link) {
                if (link.dataset.stopBound === 'true') return;
                link.dataset.stopBound = 'true';
                link.addEventListener('click', function(e) {
                    e.stopPropagation();
                });
            });
            blockers.forEach(function(el) {
                if (el.dataset.stopBound === 'true') return;
                el.dataset.stopBound = 'true';
                el.addEventListener('click', function(e) {
                    e.stopPropagation();
                });
            });
        }, 0);
        return window.dash_clientside.no_update;
    }
    """,
    Output("keyboard-shortcut-listener", "title"),
    Input("insights-grid-container", "children"),
)


# Increment page when clicking "Load more"
@callback(
    Output("current-page", "data", allow_duplicate=True),
    Input("load-more-insights", "n_clicks"),
    State("current-page", "data"),
    State("insights-data", "data"),
    prevent_initial_call=True,
)
def handle_load_more(n_clicks, current_page, insights_data):
    if not n_clicks:
        raise dash.exceptions.PreventUpdate
    from ix.web.pages.insights.utils.data_utils import deserialize_insights

    total = len(deserialize_insights(insights_data) or [])
    total_pages = max(1, (total + GRID_PAGE_SIZE - 1) // GRID_PAGE_SIZE)
    new_page = min((current_page or 1) + 1, total_pages)
    return new_page


# Hide load more when all items loaded
@callback(
    Output("load-more-container", "style"),
    Input("insights-data", "data"),
    Input("current-page", "data"),
)
def update_load_more_visibility(insights_data, current_page):
    from ix.web.pages.insights.utils.data_utils import deserialize_insights

    total = len(deserialize_insights(insights_data) or [])
    total_pages = max(1, (total + GRID_PAGE_SIZE - 1) // GRID_PAGE_SIZE)
    page = int(current_page or 1)
    if page >= total_pages or total == 0:
        return {"display": "none"}
    return {"marginTop": "12px"}


# Open modal summary when clicking a card
@callback(
    Output("insight-modal", "is_open", allow_duplicate=True),
    Output("modal-body-content", "children", allow_duplicate=True),
    Input({"type": "insight-card", "index": ALL}, "n_clicks"),
    State("insights-data", "data"),
    prevent_initial_call=True,
)
def open_summary_modal(n_clicks_list, insights_data):
    if not n_clicks_list or not any(n_clicks_list):
        raise dash.exceptions.PreventUpdate
    ctx = dash.callback_context
    if not ctx.triggered:
        raise dash.exceptions.PreventUpdate
    import json

    card_id = ctx.triggered[0]["prop_id"].split(".")[0]
    selected = json.loads(card_id).get("index")
    from ix.web.pages.insights.utils.data_utils import deserialize_insights

    all_insights = deserialize_insights(insights_data) or []
    insight = next((i for i in all_insights if str(i.get("id")) == str(selected)), None)
    if not insight:
        raise dash.exceptions.PreventUpdate
    title = insight.get("name") or "Untitled report"
    issuer = insight.get("issuer") or "Unknown"
    published = insight.get("published_date") or "-"
    hash_text = insight.get("hash") or ""
    summary = insight.get("summary") or "No summary available."
    body = html.Div(
        [
            dmc.Group(
                [
                    dmc.Text(title, fw=700, fz="lg"),
                    dmc.Group(
                        [
                            dmc.Text(f"{issuer} • {published}", c="dimmed", fz="sm"),
                            (
                                dmc.Badge(
                                    f"#{hash_text}",
                                    size="xs",
                                    variant="light",
                                    color="cyan",
                                )
                                if hash_text
                                else None
                            ),
                        ],
                        gap="xs",
                    ),
                ],
                justify="space-between",
                align="flex-start",
                mb="md",
            ),
            dcc.Markdown(summary, className="reading-body"),
        ]
    )
    return True, body


# (Removed bottom reading panel callbacks; modal is the only summary view)


# Close summary modal via X button
@callback(
    Output("insight-modal", "is_open", allow_duplicate=True),
    Input("close-modal", "n_clicks"),
    State("insight-modal", "is_open"),
    prevent_initial_call=True,
)
def close_summary_modal(n, is_open):
    if not n:
        raise dash.exceptions.PreventUpdate
    return False
