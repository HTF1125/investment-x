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
        # Compact Page Header
        dmc.Group(
            [
                dmc.Group(
                    [
                        DashIconify(
                            icon="material-symbols:lightbulb",
                            width=28,
                            style={"color": "#60a5fa"},
                        ),
                        dmc.Title(
                            "Insights & Research",
                            order=2,
                            style={
                                "background": "linear-gradient(135deg, #60a5fa 0%, #3b82f6 50%, #2563eb 100%)",
                                "WebkitBackgroundClip": "text",
                                "WebkitTextFillColor": "transparent",
                                "fontWeight": "700",
                            },
                        ),
                    ],
                    gap="sm",
                ),
                dmc.Badge("Beta", color="blue", variant="light", size="sm"),
            ],
            justify="space-between",
            style={"marginBottom": "16px"},
        ),
        # Compact Stats Cards Row
        dmc.Grid(
            [
                dmc.GridCol(
                    dmc.Paper(
                        dmc.Group(
                            [
                                dmc.ThemeIcon(
                                    DashIconify(
                                        icon="material-symbols:description", width=20
                                    ),
                                    size=40,
                                    radius="md",
                                    variant="light",
                                    color="blue",
                                ),
                                html.Div(
                                    [
                                        dmc.Text(
                                            "Total", size="xs", c="dimmed", fw=500
                                        ),
                                        dmc.Title(
                                            "0",
                                            order=3,
                                            id="total-insights-stat",
                                            style={"color": "#3b82f6"},
                                        ),
                                    ]
                                ),
                            ],
                            gap="sm",
                        ),
                        p="md",
                        radius="md",
                        shadow="sm",
                        withBorder=True,
                        className="stats-card-hover",
                    ),
                    span={"base": 12, "sm": 4, "md": 4},
                ),
                dmc.GridCol(
                    dmc.Paper(
                        dmc.Group(
                            [
                                dmc.ThemeIcon(
                                    DashIconify(
                                        icon="material-symbols:trending-up", width=20
                                    ),
                                    size=40,
                                    radius="md",
                                    variant="light",
                                    color="green",
                                ),
                                html.Div(
                                    [
                                        dmc.Text(
                                            "This Week", size="xs", c="dimmed", fw=500
                                        ),
                                        dmc.Title(
                                            "0",
                                            order=3,
                                            id="weekly-insights-stat",
                                            style={"color": "#10b981"},
                                        ),
                                    ]
                                ),
                            ],
                            gap="sm",
                        ),
                        p="md",
                        radius="md",
                        shadow="sm",
                        withBorder=True,
                        className="stats-card-hover",
                    ),
                    span={"base": 12, "sm": 4, "md": 4},
                ),
                dmc.GridCol(
                    dmc.Paper(
                        dmc.Group(
                            [
                                dmc.ThemeIcon(
                                    DashIconify(
                                        icon="material-symbols:source", width=20
                                    ),
                                    size=40,
                                    radius="md",
                                    variant="light",
                                    color="violet",
                                ),
                                html.Div(
                                    [
                                        dmc.Text(
                                            "Sources", size="xs", c="dimmed", fw=500
                                        ),
                                        dmc.Title(
                                            "0",
                                            order=3,
                                            id="sources-stat",
                                            style={"color": "#8b5cf6"},
                                        ),
                                    ]
                                ),
                            ],
                            gap="sm",
                        ),
                        p="md",
                        radius="md",
                        shadow="sm",
                        withBorder=True,
                        className="stats-card-hover",
                    ),
                    span={"base": 12, "sm": 4, "md": 4},
                ),
            ],
            gutter="sm",
            style={"marginBottom": "12px"},
        ),
        # Two Column Layout: Upload & Search on Left, Insights & Sources on Right
        dmc.Grid(
            [
                # Left Column: Upload & Search
                dmc.GridCol(
                    [
                        # Compact Upload Section
                        dmc.Paper(
                            [
                                dmc.Group(
                                    [
                                        DashIconify(
                                            icon="material-symbols:cloud-upload",
                                            width=18,
                                            color="#3b82f6",
                                        ),
                                        dmc.Text("Upload", size="sm", fw=600),
                                    ],
                                    gap="xs",
                                    style={"marginBottom": "8px"},
                                ),
                                dcc.Upload(
                                    dmc.Paper(
                                        [
                                            dmc.Center(
                                                DashIconify(
                                                    icon="material-symbols:upload-file",
                                                    width=32,
                                                    color="#3b82f6",
                                                ),
                                                style={"marginBottom": "6px"},
                                            ),
                                            dmc.Text(
                                                "Drop PDF or click",
                                                size="xs",
                                                fw=500,
                                                ta="center",
                                            ),
                                            dmc.Group(
                                                [
                                                    dmc.Badge(
                                                        "PDF",
                                                        color="blue",
                                                        variant="light",
                                                        size="xs",
                                                    ),
                                                    dmc.Badge(
                                                        "10MB",
                                                        color="blue",
                                                        variant="light",
                                                        size="xs",
                                                    ),
                                                ],
                                                justify="center",
                                                gap="xs",
                                                style={"marginTop": "6px"},
                                            ),
                                        ],
                                        p="sm",
                                        radius="md",
                                        withBorder=True,
                                        style={
                                            "border": "2px dashed var(--mantine-color-blue-6)",
                                            "cursor": "pointer",
                                            "backgroundColor": "rgba(59, 130, 246, 0.05)",
                                        },
                                        className="upload-zone-hover",
                                    ),
                                    id="upload-pdf",
                                    multiple=False,
                                    accept=".pdf",
                                ),
                                html.Div(
                                    id="output-pdf-upload", style={"marginTop": "8px"}
                                ),
                            ],
                            p="sm",
                            radius="md",
                            shadow="sm",
                            withBorder=True,
                            style={"marginBottom": "12px"},
                        ),
                        # Compact Search Section
                        dmc.Paper(
                            [
                                dmc.Group(
                                    [
                                        DashIconify(
                                            icon="material-symbols:search",
                                            width=18,
                                            color="#3b82f6",
                                        ),
                                        dmc.Text("Search & Filter", size="sm", fw=600),
                                    ],
                                    gap="xs",
                                    style={"marginBottom": "8px"},
                                ),
                                dmc.TextInput(
                                    id="insights-search",
                                    placeholder="Search...",
                                    leftSection=DashIconify(
                                        icon="material-symbols:search", width=16
                                    ),
                                    size="sm",
                                    radius="md",
                                    style={"marginBottom": "8px"},
                                ),
                                dmc.Group(
                                    [
                                        dmc.Button(
                                            "Search",
                                            id="search-button",
                                            variant="filled",
                                            color="blue",
                                            size="xs",
                                            fullWidth=True,
                                        ),
                                    ],
                                    style={"marginBottom": "8px"},
                                ),
                                dmc.Select(
                                    id="sort-dropdown",
                                    placeholder="Sort",
                                    data=[
                                        {"label": "Newest", "value": "date_desc"},
                                        {"label": "Oldest", "value": "date_asc"},
                                        {"label": "A-Z", "value": "name_asc"},
                                        {"label": "Z-A", "value": "name_desc"},
                                    ],
                                    size="xs",
                                    radius="md",
                                    style={"marginBottom": "8px"},
                                ),
                                dmc.Select(
                                    id="issuer-filter",
                                    placeholder="All issuers",
                                    data=[
                                        {"label": "All", "value": "all"},
                                        {"label": "Goldman", "value": "gs"},
                                        {"label": "JPM", "value": "jpm"},
                                        {"label": "MS", "value": "ms"},
                                        {"label": "Fed", "value": "fed"},
                                    ],
                                    size="xs",
                                    radius="md",
                                    style={"marginBottom": "8px"},
                                ),
                                dmc.DatePicker(
                                    id="date-range-filter",
                                    type="range",
                                    size="xs",
                                ),
                            ],
                            p="sm",
                            radius="md",
                            shadow="sm",
                            withBorder=True,
                        ),
                    ],
                    span={"base": 12, "md": 4},
                ),
                # Right Column: Insights & Sources
                dmc.GridCol(
                    [
                        # Compact Insights Section
                        dmc.Paper(
                            [
                                dmc.Group(
                                    [
                                        dmc.Text("📄 Insights", size="sm", fw=600),
                                        dmc.Button(
                                            "↻",
                                            id="load-more-insights",
                                            variant="light",
                                            color="blue",
                                            size="xs",
                                            style={"minWidth": "32px"},
                                        ),
                                    ],
                                    justify="space-between",
                                    style={"marginBottom": "8px"},
                                ),
                                dmc.ScrollArea(
                                    [
                                        html.Div(id="insights-container-wrapper"),
                                        html.Div(id="insights-container"),
                                    ],
                                    h=300,
                                    type="auto",
                                ),
                            ],
                            p="sm",
                            radius="md",
                            shadow="sm",
                            withBorder=True,
                            style={"marginBottom": "12px"},
                        ),
                        # Compact Sources Section
                        sources.layout,
                    ],
                    span={"base": 12, "md": 8},
                ),
            ],
            gutter="sm",
        ),
        # Modal for Summary
        summary_modal,
        # Data Stores
        dcc.Store(id="insights-data", data=[]),
        dcc.Store(id="total-insights-loaded", data=0),
        dcc.Store(id="search-query", data=""),
        dcc.Store(id="filter-state", data={}),
    ],
    size="xl",
    px="sm",
    style={
        "paddingTop": "12px",
        "paddingBottom": "12px",
        "minHeight": "100vh",
    },
)
