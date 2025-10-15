"""
Modern Insights Page - Redesigned with beautiful UI and enhanced UX
"""

from dash import html, dcc
import dash
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from ix.web.pages.insights.callbacks_minimal import *
from ix.web.pages.insights.summary_modal import summary_modal
from ix.web.pages.insights import sources

# Register Page
dash.register_page(__name__, path="/insights", title="Insights", name="Insights")


# Main Layout with Modern Design
layout = dmc.Container(
    [
        # Modern Page Header
        html.Div(
            [
                dmc.Group(
                    [
                        html.Div(
                            [
                                dmc.Title(
                                    "💡 Insights & Research",
                                    order=1,
                                    style={
                                        "background": "linear-gradient(135deg, #60a5fa 0%, #3b82f6 50%, #2563eb 100%)",
                                        "WebkitBackgroundClip": "text",
                                        "WebkitTextFillColor": "transparent",
                                        "fontSize": "2.5rem",
                                        "fontWeight": "800",
                                        "marginBottom": "8px",
                                    },
                                ),
                                dmc.Text(
                                    "Centralized market research and institutional insights",
                                    c="dimmed",
                                    size="lg",
                                ),
                            ]
                        ),
                        dmc.Badge(
                            "Beta",
                            color="blue",
                            variant="light",
                            size="lg",
                            radius="md",
                        ),
                    ],
                    justify="space-between",
                    align="flex-start",
                    style={"marginBottom": "32px"},
                ),
            ]
        ),
        # Stats Cards Row
        html.Div(
            [
                dmc.Grid(
                    [
                        dmc.GridCol(
                            dmc.Paper(
                                [
                                    dmc.Group(
                                        [
                                            dmc.ThemeIcon(
                                                DashIconify(
                                                    icon="material-symbols:description",
                                                    width=28,
                                                ),
                                                size=60,
                                                radius="md",
                                                variant="light",
                                                color="blue",
                                            ),
                                            html.Div(
                                                [
                                                    dmc.Text(
                                                        "Total Insights",
                                                        size="sm",
                                                        c="dimmed",
                                                        fw=500,
                                                    ),
                                                    dmc.Title(
                                                        "0",
                                                        order=2,
                                                        id="total-insights-stat",
                                                        style={
                                                            "marginTop": "4px",
                                                            "color": "#3b82f6",
                                                        },
                                                    ),
                                                ]
                                            ),
                                        ],
                                        gap="md",
                                    ),
                                ],
                                p="lg",
                                radius="lg",
                                shadow="sm",
                                withBorder=True,
                                style={"height": "100%"},
                            ),
                            span={"base": 12, "sm": 6, "md": 4},
                        ),
                        dmc.GridCol(
                            dmc.Paper(
                                [
                                    dmc.Group(
                                        [
                                            dmc.ThemeIcon(
                                                DashIconify(
                                                    icon="material-symbols:trending-up",
                                                    width=28,
                                                ),
                                                size=60,
                                                radius="md",
                                                variant="light",
                                                color="green",
                                            ),
                                            html.Div(
                                                [
                                                    dmc.Text(
                                                        "This Week",
                                                        size="sm",
                                                        c="dimmed",
                                                        fw=500,
                                                    ),
                                                    dmc.Title(
                                                        "0",
                                                        order=2,
                                                        id="weekly-insights-stat",
                                                        style={
                                                            "marginTop": "4px",
                                                            "color": "#10b981",
                                                        },
                                                    ),
                                                ]
                                            ),
                                        ],
                                        gap="md",
                                    ),
                                ],
                                p="lg",
                                radius="lg",
                                shadow="sm",
                                withBorder=True,
                                style={"height": "100%"},
                            ),
                            span={"base": 12, "sm": 6, "md": 4},
                        ),
                        dmc.GridCol(
                            dmc.Paper(
                                [
                                    dmc.Group(
                                        [
                                            dmc.ThemeIcon(
                                                DashIconify(
                                                    icon="material-symbols:source",
                                                    width=28,
                                                ),
                                                size=60,
                                                radius="md",
                                                variant="light",
                                                color="violet",
                                            ),
                                            html.Div(
                                                [
                                                    dmc.Text(
                                                        "Sources",
                                                        size="sm",
                                                        c="dimmed",
                                                        fw=500,
                                                    ),
                                                    dmc.Title(
                                                        "0",
                                                        order=2,
                                                        id="sources-stat",
                                                        style={
                                                            "marginTop": "4px",
                                                            "color": "#8b5cf6",
                                                        },
                                                    ),
                                                ]
                                            ),
                                        ],
                                        gap="md",
                                    ),
                                ],
                                p="lg",
                                radius="lg",
                                shadow="sm",
                                withBorder=True,
                                style={"height": "100%"},
                            ),
                            span={"base": 12, "sm": 6, "md": 4},
                        ),
                    ],
                    gutter="lg",
                    style={"marginBottom": "32px"},
                )
            ]
        ),
        # Upload Section - Modern Design
        dmc.Paper(
            [
                dmc.Group(
                    [
                        DashIconify(
                            icon="material-symbols:cloud-upload",
                            width=24,
                            color="#3b82f6",
                        ),
                        dmc.Title("Upload Research Document", order=4),
                    ],
                    gap="sm",
                    style={"marginBottom": "16px"},
                ),
                dcc.Upload(
                    dmc.Paper(
                        [
                            dmc.Center(
                                [
                                    DashIconify(
                                        icon="material-symbols:upload-file",
                                        width=48,
                                        color="#3b82f6",
                                    ),
                                ],
                                style={"marginBottom": "12px"},
                            ),
                            dmc.Text(
                                "Drag and drop PDF files here",
                                size="lg",
                                fw=500,
                                ta="center",
                            ),
                            dmc.Text(
                                "or click to browse",
                                size="sm",
                                c="dimmed",
                                ta="center",
                                style={"marginTop": "4px"},
                            ),
                            dmc.Group(
                                [
                                    dmc.Badge(
                                        "PDF Only", color="blue", variant="light"
                                    ),
                                    dmc.Badge(
                                        "Max 10MB", color="blue", variant="light"
                                    ),
                                ],
                                justify="center",
                                style={"marginTop": "12px"},
                            ),
                        ],
                        p="xl",
                        radius="md",
                        withBorder=True,
                        style={
                            "border": "2px dashed var(--mantine-color-blue-6)",
                            "cursor": "pointer",
                            "transition": "all 0.3s ease",
                            "backgroundColor": "rgba(59, 130, 246, 0.05)",
                        },
                        className="upload-zone-hover",
                    ),
                    id="upload-pdf",
                    multiple=False,
                    accept=".pdf",
                ),
                html.Div(id="output-pdf-upload", style={"marginTop": "16px"}),
            ],
            p="xl",
            radius="lg",
            shadow="sm",
            withBorder=True,
            style={"marginBottom": "32px"},
        ),
        # Search and Filter Section - Modern Design
        dmc.Paper(
            [
                dmc.Title(
                    "🔍 Search & Filter", order=4, style={"marginBottom": "20px"}
                ),
                dmc.Grid(
                    [
                        # Search Input
                        dmc.GridCol(
                            dmc.TextInput(
                                id="insights-search",
                                placeholder="Search insights by title, issuer, or content...",
                                leftSection=DashIconify(
                                    icon="material-symbols:search", width=20
                                ),
                                size="md",
                                radius="md",
                                style={"marginBottom": "16px"},
                            ),
                            span=12,
                        ),
                        # Filter Controls
                        dmc.GridCol(
                            dmc.Button(
                                "Search",
                                id="search-button",
                                leftSection=DashIconify(
                                    icon="material-symbols:search", width=18
                                ),
                                variant="filled",
                                color="blue",
                                size="md",
                                fullWidth=True,
                            ),
                            span={"base": 12, "sm": 6, "md": 2},
                        ),
                        dmc.GridCol(
                            dmc.Select(
                                id="sort-dropdown",
                                placeholder="Sort by",
                                data=[
                                    {"label": "Date (Newest)", "value": "date_desc"},
                                    {"label": "Date (Oldest)", "value": "date_asc"},
                                    {"label": "Name (A-Z)", "value": "name_asc"},
                                    {"label": "Name (Z-A)", "value": "name_desc"},
                                ],
                                leftSection=DashIconify(
                                    icon="material-symbols:sort", width=18
                                ),
                                size="md",
                                radius="md",
                            ),
                            span={"base": 12, "sm": 6, "md": 3},
                        ),
                        dmc.GridCol(
                            dmc.Select(
                                id="issuer-filter",
                                placeholder="All issuers",
                                data=[
                                    {"label": "All Issuers", "value": "all"},
                                    {"label": "Goldman Sachs", "value": "gs"},
                                    {"label": "JP Morgan", "value": "jpm"},
                                    {"label": "Morgan Stanley", "value": "ms"},
                                    {"label": "Federal Reserve", "value": "fed"},
                                ],
                                leftSection=DashIconify(
                                    icon="material-symbols:business", width=18
                                ),
                                size="md",
                                radius="md",
                            ),
                            span={"base": 12, "sm": 6, "md": 3},
                        ),
                        dmc.GridCol(
                            html.Div(
                                [
                                    dmc.Text(
                                        "Date Range",
                                        size="sm",
                                        fw=500,
                                        style={"marginBottom": "8px"},
                                    ),
                                    dmc.DatePicker(
                                        id="date-range-filter",
                                        type="range",
                                        size="md",
                                    ),
                                ]
                            ),
                            span={"base": 12, "sm": 6, "md": 4},
                        ),
                    ],
                    gutter="md",
                ),
            ],
            p="xl",
            radius="lg",
            shadow="sm",
            withBorder=True,
            style={"marginBottom": "32px"},
        ),
        # Insights Grid Section
        dmc.Paper(
            [
                dmc.Group(
                    [
                        dmc.Title("📄 Recent Insights", order=4),
                        dmc.Group(
                            [
                                dmc.Button(
                                    "Refresh",
                                    id="load-more-insights",
                                    leftSection=DashIconify(
                                        icon="material-symbols:refresh", width=18
                                    ),
                                    variant="light",
                                    color="blue",
                                    size="sm",
                                ),
                            ]
                        ),
                    ],
                    justify="space-between",
                    style={"marginBottom": "24px"},
                ),
                dmc.ScrollArea(
                    [
                        html.Div(id="insights-container-wrapper"),
                        html.Div(id="insights-container"),
                    ],
                    h=600,
                    type="auto",
                ),
            ],
            p="xl",
            radius="lg",
            shadow="sm",
            withBorder=True,
            style={"marginBottom": "32px"},
        ),
        # Sources Section
        sources.layout,
        # Modal for Summary
        summary_modal,
        # Data Stores
        dcc.Store(id="insights-data", data=[]),
        dcc.Store(id="total-insights-loaded", data=0),
        dcc.Store(id="search-query", data=""),
        dcc.Store(id="filter-state", data={}),
    ],
    size="xl",
    px="md",
    style={
        "paddingTop": "32px",
        "paddingBottom": "40px",
        "minHeight": "100vh",
    },
)
