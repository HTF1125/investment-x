"""Enhanced professional header component for Insights browser."""

from dash import html, dcc
import dash_mantine_components as dmc
from dash_iconify import DashIconify


def create_header() -> html.Div:
    """Create an enhanced professional insights browser header with sticky search."""
    return html.Div(
        [
            # Enhanced sticky search bar with better styling
            html.Div(
                dmc.Container(
                    dmc.Group(
                        [
                            # Search input with enhanced styling
                            dmc.TextInput(
                                id="insights-search",
                                placeholder="Search reports by title, issuer, date, or keywords...",
                                leftSection=DashIconify(icon="carbon:search", width=20, color="#64748b"),
                                rightSection=dmc.ActionIcon(
                                    DashIconify(icon="carbon:close", width=16),
                                    variant="subtle",
                                    color="gray",
                                    id="clear-search",
                                    size="sm",
                                ),
                                size="md",
                                radius="md",
                                style={
                                    "flex": 1,
                                    "maxWidth": "600px",
                                },
                            ),
                            # Action buttons group
                            dmc.Group(
                                [
                                    dcc.Upload(
                                        dmc.Button(
                                            "Upload PDF",
                                            leftSection=DashIconify(icon="carbon:upload", width=16),
                                            variant="gradient",
                                            gradient={"from": "blue", "to": "cyan"},
                                            size="md",
                                            radius="md",
                                        ),
                                        id="upload-pdf",
                                        multiple=True,
                                        accept=".pdf",
                                        style={
                                            "display": "inline-block",
                                            "textDecoration": "none",
                                        },
                                    ),
                                    dmc.Button(
                                        "Search",
                                        id="search-button",
                                        leftSection=DashIconify(icon="carbon:search", width=16),
                                        variant="filled",
                                        color="blue",
                                        size="md",
                                        radius="md",
                                    ),
                                    dmc.Button(
                                        "No Summary",
                                        id="filter-no-summary",
                                        leftSection=DashIconify(icon="carbon:document-blank", width=16),
                                        variant="subtle",
                                        color="orange",
                                        size="md",
                                        radius="md",
                                    ),
                                ],
                                gap="sm",
                            ),
                        ],
                        gap="md",
                        align="center",
                        justify="space-between",
                        wrap="wrap",
                    ),
                    size="xl",
                    px="xl",
                    py="md",
                    style={
                        "backgroundColor": "#0f172a",
                    },
                ),
                style={
                    "position": "sticky",
                    "top": "0",
                    "zIndex": "100",
                    "backgroundColor": "#0f172a",
                    "borderBottom": "2px solid #334155",
                    "boxShadow": "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                },
                className="insights-search-header",
            ),
        ],
    )
