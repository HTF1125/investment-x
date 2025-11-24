"""Insights Page - Production-Ready Layout with Optimized Structure."""

from dash import html, dcc
import dash
import dash_mantine_components as dmc
from dash_iconify import DashIconify

# Register page
dash.register_page(__name__, path="/insights", title="Research Insights", name="Insights")

# Import callbacks to register them
from ix.web.pages.insights.callbacks import *  # noqa: F403, F401

# Import components
from ix.web.pages.insights.components import create_header, create_all_modals, create_upload_zone


# ============================================================================
# Constants
# ============================================================================
PAGE_SIZE = 20
TABLE_MAX_HEIGHT = "calc(100vh - 350px)"


# ============================================================================
# UI Components
# ============================================================================
def create_stat_card() -> dmc.Paper:
    """Create statistics card showing total document count."""
    return dmc.Paper(
        dmc.Group(
            [
                dmc.ThemeIcon(
                    DashIconify(icon="carbon:document", width=20),
                    size="lg",
                    radius="md",
                    variant="light",
                    color="blue",
                ),
                dmc.Stack(
                    [
                        dmc.Text(
                            id="insights-count-badge",
                            children="Loading reports...",
                            size="md",
                            fw="700",
                            c="gray.3",
                        ),
                        dmc.Text(
                            "Browse and manage your research documents",
                            size="xs",
                            c="gray.6",
                        ),
                    ],
                    gap="2px",
                ),
            ],
            gap="md",
            align="center",
        ),
        p="md",
        radius="md",
        withBorder=True,
        style={
            "backgroundColor": "#1e293b",
            "borderColor": "#334155",
        },
        mb="lg",
    )


def create_table_section() -> dmc.Paper:
    """Create scrollable table section with pagination."""
    return dmc.Paper(
        dmc.Stack(
            [
                html.Div(
                    html.Div(
                        id="insights-table-container",
                        style={"minHeight": "400px"},
                    ),
                    style={
                        "overflowY": "auto",
                        "overflowX": "auto",
                        "maxHeight": TABLE_MAX_HEIGHT,
                        "scrollBehavior": "smooth",
                    },
                    className="insights-table-scroll-container",
                ),
                dmc.Center(
                    dmc.Pagination(
                        id="insights-pagination",
                        total=1,
                        value=1,
                        size="md",
                        radius="md",
                        withEdges=True,
                        siblings=2,
                        boundaries=1,
                        style={"marginTop": "20px"},
                    ),
                ),
            ],
            gap="md",
        ),
        p="md",
        radius="lg",
        withBorder=True,
        style={
            "backgroundColor": "#0f172a",
            "borderColor": "#475569",
            "boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
        },
    )


def create_main_content() -> html.Div:
    """Create main content area with table and upload zone."""
    return html.Div(
        dmc.Container(
            dmc.Stack(
                [
                    create_stat_card(),
                    create_upload_zone(),
                    create_table_section(),
                ],
                gap="md",
            ),
            size="xl",
            px="xl",
            style={
                "flex": 1,
                "display": "flex",
                "flexDirection": "column",
                "minHeight": 0,
                "overflow": "hidden",
            },
        ),
        style={
            "flex": 1,
            "display": "flex",
            "flexDirection": "column",
            "minHeight": 0,
            "overflow": "hidden",
        },
    )


# ============================================================================
# Main Layout
# ============================================================================
layout = html.Div(
    [
        # Sticky Header
        create_header(),
        # Main Content
        create_main_content(),
        # Upload Loading Overlay
        dcc.Loading(
            id="upload-processing-loader",
            type="circle",
            overlay_style={"backgroundColor": "rgba(15, 23, 42, 0.85)"},
            children=html.Div(id="output-pdf-upload"),
        ),
        # Modals
        *create_all_modals(),
        # Data Stores - Minimal and Efficient
        dcc.Store(id="insights-data", data=[]),
        dcc.Store(id="current-page", data=1),
        dcc.Store(id="filter-config", data={"search": "", "no_summary": False}),
        dcc.Store(id="row-click-handler", data={}),  # Handles row clicks
        dcc.Store(id="dragdrop-handler", data={}),  # Handles drag-drop visual feedback
    ],
    style={
        "height": "100vh",
        "display": "flex",
        "flexDirection": "column",
        "backgroundColor": "#0f172a",
        "overflow": "hidden",
        "padding": 0,
        "margin": 0,
    },
    className="insights-page-container",
)
