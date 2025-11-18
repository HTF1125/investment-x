"""
Investment Insights Hub - Completely Redesigned
Modern, clean interface for browsing research and market insights
"""

from dash import html, dcc
import dash
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from ix.web.pages.insights.callbacks_minimal import *
from ix.web.pages.insights.pdf_viewer_callbacks import *
from ix.web.pages.insights.summary_modal import summary_modal
from ix.web.pages.insights.edit_summary_modal import edit_summary_modal
from ix.web.pages.insights.add_publisher_modal import add_publisher_modal
from ix.web.pages.insights.pdf_viewer import create_pdf_viewer
from ix.web.pages.insights import sources

# Register Page
dash.register_page(__name__, path="/insights", title="Insights", name="Insights")

# Modern color palette
COLORS = {
    "primary": "#2563eb",
    "secondary": "#7c3aed",
    "accent": "#0891b2",
    "success": "#059669",
    "warning": "#d97706",
    "danger": "#dc2626",
}


# Main Layout - Completely Redesigned
layout = dmc.Container(
    [
        # Hero Header with Gradient
        html.Div(
            [
                dmc.Stack(
                    [
                        # Title with icon
                        dmc.Group(
                            [
                                dmc.ThemeIcon(
                                    DashIconify(icon="ph:books-fill", width=40),
                                    size=70,
                                    radius="xl",
                                    variant="gradient",
                                    gradient={"from": "blue", "to": "cyan", "deg": 45},
                                ),
                                html.Div(
                                    [
                                        dmc.Title(
                                            "Investment Insights Hub",
                                            order=1,
                                            style={
                                                "fontSize": "2.8rem",
                                                "fontWeight": "800",
                                                "marginBottom": "8px",
                                                "letterSpacing": "-0.02em",
                                            },
                                        ),
                                        dmc.Text(
                                            "AI-powered research aggregation from top institutional sources",
                                            size="lg",
                                            c="gray",
                                            fw="normal",
                                        ),
                                    ]
                                ),
                            ],
                            gap="xl",
                            align="center",
                        ),
                    ],
                    gap="md",
                ),
            ],
            style={
                "marginBottom": "40px",
                "paddingBottom": "24px",
                "borderBottom": "1px solid #ccc",
            },
        ),
        # Upload & Quick Actions Section
        dmc.Grid(
            [
                # Upload Zone
                dmc.GridCol(
                    dmc.Card(
                        [
                            dmc.Stack(
                                [
                                    dmc.Group(
                                        [
                                            DashIconify(
                                                icon="carbon:cloud-upload",
                                                width=28,
                                                color="blue",
                                            ),
                                            dmc.Title(
                                                "Upload Research", order=4, c="blue.6"
                                            ),
                                        ],
                                        gap="sm",
                                    ),
                                    dcc.Upload(
                                        dmc.Center(
                                            [
                                                dmc.Stack(
                                                    [
                                                        dmc.ThemeIcon(
                                                            DashIconify(
                                                                icon="carbon:document-add",
                                                                width=36,
                                                            ),
                                                            size=80,
                                                            radius="xl",
                                                            variant="light",
                                                            color="blue",
                                                        ),
                                                        dmc.Text(
                                                            "Drop PDF file here or click to upload",
                                                            size="md",
                                                            fw="normal",
                                                            ta="center",
                                                        ),
                                                        dmc.Text(
                                                            "Format: YYYYMMDD_issuer_title.pdf",
                                                            size="sm",
                                                            c="gray",
                                                            ta="center",
                                                        ),
                                                        dmc.Group(
                                                            [
                                                                dmc.Badge(
                                                                    "PDF",
                                                                    color="blue",
                                                                    variant="dot",
                                                                ),
                                                                dmc.Badge(
                                                                    "Max 10MB",
                                                                    color="cyan",
                                                                    variant="dot",
                                                                ),
                                                                dmc.Badge(
                                                                    "Auto AI Summary",
                                                                    color="grape",
                                                                    variant="dot",
                                                                ),
                                                            ],
                                                            justify="center",
                                                            gap="xs",
                                                        ),
                                                    ],
                                                    align="center",
                                                    gap="md",
                                                ),
                                            ],
                                            style={
                                                "border": "2px dashed #3b82f6",
                                                "borderRadius": "12px",
                                                "padding": "32px",
                                                "cursor": "pointer",
                                                "transition": "all 0.3s ease",
                                                "background": "rgba(59, 130, 246, 0.03)",
                                                "minHeight": "200px",
                                            },
                                        ),
                                        id="upload-pdf",
                                        multiple=True,
                                        accept=".pdf",
                                    ),
                                    dcc.Loading(
                                        id="upload-processing-loader",
                                        type="circle",
                                        overlay_style={"backgroundColor": "rgba(15, 23, 42, 0.65)"},
                                        children=html.Div(id="output-pdf-upload"),
                                    ),
                                ],
                                gap="md",
                            ),
                        ],
                        padding="xl",
                        radius="lg",
                        withBorder=True,
                        shadow="sm",
                    ),
                    span={"base": 12, "md": 6},
                ),
                # Insight Sources
                dmc.GridCol(
                    dmc.Stack(
                        [
                            dmc.Card(
                                [
                                    dmc.Stack(
                                        [
                                            # Header with title and add button
                                            html.Div(
                                                [
                                                    dmc.Group(
                                                        [
                                                            DashIconify(
                                                                icon="carbon:rss",
                                                                width=20,
                                                            ),
                                                            dmc.Text(
                                                                "Publishers",
                                                                size="sm",
                                                                fw="bold",
                                                            ),
                                                        ],
                                                        gap="xs",
                                                        style={"flex": 1},
                                                    ),
                                                    dmc.ActionIcon(
                                                        DashIconify(
                                                            icon="carbon:add",
                                                            width=18,
                                                        ),
                                                        id="add-publisher-button",
                                                        variant="light",
                                                        color="blue",
                                                        size="md",
                                                        radius="md",
                                                    ),
                                                ],
                                                style={
                                                    "display": "flex",
                                                    "justifyContent": "space-between",
                                                    "alignItems": "center",
                                                    "marginBottom": "12px",
                                                },
                                            ),
                                            # Publishers list
                                            html.Div(
                                                id="insight-sources-list",
                                                children=[
                                                    dmc.Text(
                                                        "Loading sources...",
                                                        size="sm",
                                                        c="gray",
                                                        ta="center",
                                                    ),
                                                ],
                                                style={
                                                    "maxHeight": "300px",
                                                    "overflowY": "auto",
                                                    "overflowX": "hidden",
                                                },
                                            ),
                                        ],
                                        gap="sm",
                                    ),
                                ],
                                padding="md",
                                radius="lg",
                                withBorder=True,
                                shadow="sm",
                            ),
                        ],
                        gap="md",
                    ),
                    span={"base": 12, "md": 6},
                ),
            ],
            gutter="lg",
            style={"marginBottom": "32px"},
        ),
        # Main content area - either insights list or PDF viewer
        html.Div(
            [
                # Insights Feed - Completely Redesigned (default view)
                dmc.Card(
                    [
                        dmc.Stack(
                            [
                                dmc.TextInput(
                                    id="insights-search",
                                    placeholder="Search by title, issuer, date (YYYY-MM-DD), or keywords...",
                                    leftSection=DashIconify(
                                        icon="carbon:search", width=20
                                    ),
                                    rightSection=dmc.ActionIcon(
                                        DashIconify(icon="carbon:close", width=16),
                                        variant="subtle",
                                        color="gray",
                                        id="clear-search",
                                    ),
                                    size="lg",
                                    radius="md",
                                ),
                                dmc.Group(
                                    [
                                        dmc.ChipGroup(
                                            [
                                                dmc.Chip(
                                                    "All",
                                                    value="all",
                                                    variant="filled",
                                                    size="sm",
                                                ),
                                                dmc.Chip(
                                                    "Last 7 Days",
                                                    value="7d",
                                                    variant="filled",
                                                    size="sm",
                                                ),
                                                dmc.Chip(
                                                    "Last 30 Days",
                                                    value="30d",
                                                    variant="filled",
                                                    size="sm",
                                                ),
                                                dmc.Chip(
                                                    "Last 3 Months",
                                                    value="3m",
                                                    variant="filled",
                                                    size="sm",
                                                ),
                                            ],
                                            id="time-filter-chips",
                                            value="all",
                                        ),
                                        dmc.Button(
                                            "Search",
                                            id="search-button",
                                            leftSection=DashIconify(
                                                icon="carbon:search", width=16
                                            ),
                                            variant="gradient",
                                            gradient={
                                                "from": "blue",
                                                "to": "cyan",
                                                "deg": 90,
                                            },
                                            size="sm",
                                        ),
                                    ],
                                    justify="space-between",
                                    align="center",
                                ),
                                dmc.Accordion(
                                    [
                                        dmc.AccordionItem(
                                            [
                                                dmc.AccordionControl(
                                                    "Advanced Filters",
                                                    icon=DashIconify(
                                                        icon="carbon:filter", width=20
                                                    ),
                                                ),
                                                dmc.AccordionPanel(
                                                    dmc.Grid(
                                                        [
                                                            dmc.GridCol(
                                                                html.Div(
                                                                    [
                                                                        dmc.Text(
                                                                            "Sort By",
                                                                            size="sm",
                                                                            fw="normal",
                                                                            style={
                                                                                "marginBottom": "4px"
                                                                            },
                                                                        ),
                                                                        dmc.Select(
                                                                            id="sort-dropdown",
                                                                            placeholder="Select sort order",
                                                                            data=[
                                                                                {
                                                                                    "label": "📅 Newest First",
                                                                                    "value": "date_desc",
                                                                                },
                                                                                {
                                                                                    "label": "📅 Oldest First",
                                                                                    "value": "date_asc",
                                                                                },
                                                                                {
                                                                                    "label": "🔤 Name (A-Z)",
                                                                                    "value": "name_asc",
                                                                                },
                                                                                {
                                                                                    "label": "🔤 Name (Z-A)",
                                                                                    "value": "name_desc",
                                                                                },
                                                                            ],
                                                                            size="sm",
                                                                        ),
                                                                    ]
                                                                ),
                                                                span={
                                                                    "base": 12,
                                                                    "sm": 6,
                                                                    "md": 4,
                                                                },
                                                            ),
                                                            dmc.GridCol(
                                                                html.Div(
                                                                    [
                                                                        dmc.Text(
                                                                            "Issuer",
                                                                            size="sm",
                                                                            fw="normal",
                                                                            style={
                                                                                "marginBottom": "4px"
                                                                            },
                                                                        ),
                                                                        dmc.Select(
                                                                            id="issuer-filter",
                                                                            placeholder="All publishers",
                                                                            data=[
                                                                                {
                                                                                    "label": "All Issuers",
                                                                                    "value": "all",
                                                                                },
                                                                            ],
                                                                            size="sm",
                                                                        ),
                                                                    ]
                                                                ),
                                                                span={
                                                                    "base": 12,
                                                                    "sm": 6,
                                                                    "md": 4,
                                                                },
                                                            ),
                                                            dmc.GridCol(
                                                                html.Div(
                                                                    [
                                                                        dmc.Text(
                                                                            "Date Range",
                                                                            size="sm",
                                                                            fw="normal",
                                                                            style={
                                                                                "marginBottom": "4px"
                                                                            },
                                                                        ),
                                                                        dmc.DatePicker(
                                                                            id="date-range-filter",
                                                                            type="range",
                                                                            size="sm",
                                                                        ),
                                                                    ]
                                                                ),
                                                                span={
                                                                    "base": 12,
                                                                    "sm": 6,
                                                                    "md": 4,
                                                                },
                                                            ),
                                                        ],
                                                        gutter="md",
                                                    ),
                                                ),
                                            ],
                                            value="filters",
                                        ),
                                    ],
                                    variant="separated",
                                ),
                                dmc.Group(
                                    [
                                        dmc.Group(
                                            [
                                                DashIconify(
                                                    icon="carbon:document-multiple-02",
                                                    width=24,
                                                    color="blue",
                                                ),
                                                dmc.Title(
                                                    "Research Library",
                                                    order=3,
                                                    c="blue.7",
                                                ),
                                            ],
                                            gap="sm",
                                        ),
                                        dmc.Group(
                                            [
                                                dmc.Badge(
                                                    id="insights-count-badge",
                                                    children="0 documents",
                                                    size="lg",
                                                    variant="light",
                                                    color="blue",
                                                    leftSection=DashIconify(
                                                        icon="carbon:document", width=14
                                                    ),
                                                ),
                                                dmc.Button(
                                                    "No Summary Only",
                                                    id="filter-no-summary",
                                                    leftSection=DashIconify(
                                                        icon="carbon:document-blank", width=16
                                                    ),
                                                    variant="light",
                                                    color="orange",
                                                    size="sm",
                                                    radius="md",
                                                ),
                                                dmc.Button(
                                                    "Load More",
                                                    id="load-more-insights",
                                                    leftSection=DashIconify(
                                                        icon="carbon:add", width=16
                                                    ),
                                                    variant="light",
                                                    color="blue",
                                                    size="sm",
                                                    radius="md",
                                                ),
                                            ],
                                            gap="sm",
                                        ),
                                    ],
                                    justify="space-between",
                                    align="center",
                                ),
                                dmc.Stack(
                                    [
                                        html.Div(id="insights-container-wrapper"),
                                        html.Div(
                                            id="insights-container",
                                            style={
                                                "minHeight": "400px",
                                            },
                                        ),
                                    ],
                                    gap="md",
                                ),
                            ],
                            gap="lg",
                        ),
                    ],
                    padding="xl",
                    radius="lg",
                    withBorder=True,
                    shadow="md",
                    style={
                        "marginBottom": "32px",
                        "background": "linear-gradient(to bottom, #1e293b 0%, #0f172a 100%)",
                    },
                ),
                # PDF Viewer Container (hidden by default)
                html.Div(
                    id="pdf-viewer-container",
                    style={"display": "none"},
                ),
            ],
            id="main-content-area",
        ),
        # Modal for Summary
        summary_modal,
        # Edit Summary Modal
        edit_summary_modal,
        # Add Publisher Modal
        add_publisher_modal,
        # Data Stores
        dcc.Store(id="insights-data", data=[]),
        dcc.Store(id="total-insights-loaded", data=0),
        dcc.Store(id="search-query", data=""),
        dcc.Store(id="filter-state", data={}),
        dcc.Store(id="no-summary-filter", data=False),  # Track if "no summary only" filter is active
        dcc.Store(
            id="current-view", data="insights-list"
        ),  # "insights-list" or "pdf-viewer"
        dcc.Store(
            id="current-insight", data=None
        ),  # Store current insight data for PDF viewer
        dcc.Store(id="summary-edit-context", data=None),
        dcc.Store(id="publishers-refresh-token"),
        dcc.Interval(
            id="publishers-refresh-interval",
            interval=60 * 1000,
            n_intervals=0,
        ),
    ],
    size="xl",
    px="md",
    style={
        "paddingTop": "32px",
        "paddingBottom": "40px",
        "minHeight": "100vh",
    },
)
