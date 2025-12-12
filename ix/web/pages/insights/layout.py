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
                                # Open Drive Button
                                html.A(
                                    dmc.Button(
                                        "Drive Folder",
                                        leftSection=DashIconify(icon="logos:google-drive", width=16),
                                        variant="light",
                                        color="blue",
                                        size="sm",
                                        radius="md",
                                    ),
                                    href="https://drive.google.com/drive/folders/1jkpxtpaZophtkx5Lhvb-TAF9BuKY_pPa",
                                    target="_blank",
                                    style={"textDecoration": "none"},
                                ),
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
            # Content Table (Replaces Grid)
            html.Div(
                id="insights-table-container",
                style={"marginTop": "20px"},
            ),
            # Pagination
            html.Div(
                dmc.Pagination(
                    id="insights-pagination",
                    total=1,
                    value=1,
                    color="gray",
                    size="md",
                    withEdges=True,
                ),
                style={"marginTop": "20px", "display": "flex", "justifyContent": "center"},
            ),
        ],
        className="terminal-feed",
        id="feed-scroll-container",
        style={"maxWidth": "1200px", "margin": "0 auto", "padding": "0 20px"} # Centered container
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
        dcc.Store(id="view-mode", data="list"),  # Force list/table mode
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
                # Main Content Area (Full Width)
                html.Div(
                    [
                        dmc.Paper(
                            [
                                # Library Header
                                dmc.Group(
                                    [
                                        dmc.Group(
                                            [
                                                dmc.ThemeIcon(
                                                    DashIconify(icon="carbon:catalog", width=20),
                                                    size="lg",
                                                    radius="md",
                                                    variant="light",
                                                    color="blue",
                                                ),
                                                dmc.Stack(
                                                    [
                                                        dmc.Text("Research Library", size="lg", fw=700, c="gray.2", lh=1),
                                                        dmc.Text("Global Equity & Macro Insights", size="xs", c="dimmed"),
                                                    ],
                                                    gap="2px",
                                                ),
                                            ],
                                            gap="md",
                                        ),
                                        dmc.Badge(
                                            id="insights-count-badge", # Connected to callback
                                            children="0 documents",
                                            variant="outline",
                                            color="gray",
                                            size="sm",
                                        )
                                    ],
                                    justify="space-between",
                                    align="center",
                                    mb="xl",
                                    pb="lg",
                                    style={"borderBottom": "1px solid #334155"}
                                ),

                                # Toolbar
                                create_command_bar(),

                                # Feed Content
                                create_feed_area(),
                            ],
                            p="xl",
                            radius="lg",
                            style={
                                "backgroundColor": "#0f172a",
                                "border": "1px solid #1e293b",
                                "minHeight": "800px",
                                "boxShadow": "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)"
                            }
                        ),
                    ],
                    style={
                        "padding": "30px",
                        "maxWidth": "1600px",
                        "margin": "0 auto",
                        "width": "100%",
                        "minHeight": "100vh",
                    },
                ),
            ],
            className="terminal-layout-outer",
            style={
                "backgroundColor": "#0f172a",
                "minHeight": "100vh",
            },
        ),
        # Hidden components for callback compatibility
        html.Div(id="row-click-handler", style={"display": "none"}),
        html.Div(id="dragdrop-handler", style={"display": "none"}),
        # Dummy div for keyboard shortcut callback
        html.Div(id="keyboard-shortcut-listener", style={"display": "none"}),
        # Hidden grid container to satisfy callbacks that might output to it (if any remain)
        html.Div(id="insights-grid-container", style={"display": "none"}),
        html.Div(id="load-more-container", style={"display": "none"}), # Hide load more button
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
        url = insight.get("url")

        # Create Card Component
        card = html.A(
            html.Div(
                [
                    # Icon and Issuer Header
                    dmc.Group(
                        [
                            DashIconify(icon="vscode-icons:file-type-pdf2", width=32),
                            dmc.Badge(
                                insight.get("issuer", "Unknown"),
                                size="sm",
                                radius="sm",
                                variant="light",
                                color="gray",
                            ),
                        ],
                        justify="space-between",
                        mb="md",
                    ),

                    # File Name
                    dmc.Text(
                        insight.get("name"),
                        fw=600,
                        size="md",
                        c="bright",
                        style={
                            "lineHeight": "1.4",
                            "height": "44px", # Fixed height for 2 lines
                            "overflow": "hidden",
                            "display": "-webkit-box",
                            "-webkitLineClamp": "2",
                            "-webkitBoxOrient": "vertical",
                            "marginBottom": "12px",
                        }
                    ),

                    # Footer: Date
                    dmc.Group(
                        [
                            dmc.Text(
                                str(insight.get("published_date") or ""),
                                size="xs",
                                c="dimmed",
                                style={"fontFamily": "monospace"}
                            ),
                            DashIconify(icon="carbon:arrow-up-right", width=14, color="#64748b"),
                        ],
                        justify="space-between",
                        align="center",
                        mt="auto", # Push to bottom
                    )
                ],
                style={
                    "padding": "20px",
                    "height": "100%",
                    "display": "flex",
                    "flexDirection": "column",
                    "backgroundColor": "#1e293b",
                    "borderRadius": "12px",
                    "border": "1px solid #334155",
                    "transition": "all 0.2s ease",
                },
                className="file-card-inner", # For CSS hover effects if needed
            ),
            href=url,
            target="_blank",
            style={
                "textDecoration": "none",
                "color": "inherit",
                "display": "block",
                "height": "180px", # Fixed card height
            },
            className="insight-card-link",
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
