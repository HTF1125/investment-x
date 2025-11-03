"""
PDF Viewer Component for Insights
Displays PDFs inline with summaries on the side
"""

from dash import html, dcc
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from typing import Dict, Any, Optional


class PDFViewer:
    """Component for displaying PDFs inline with summaries"""

    def __init__(self):
        self.colors = {
            "primary": "#2563eb",
            "secondary": "#7c3aed",
            "accent": "#0891b2",
            "success": "#059669",
            "warning": "#d97706",
            "danger": "#dc2626",
        }

    def create_pdf_viewer_layout(self, insight: Dict[str, Any]) -> html.Div:
        """Create the main PDF viewer layout with summary sidebar"""

        insight_id = insight.get("id")
        issuer = insight.get("issuer", "Unknown Issuer")
        name = insight.get("name", "Untitled Document")
        published_date = insight.get("published_date", "")
        summary = insight.get("summary", "")

        # Format date
        formatted_date = self._format_date(published_date)

        return html.Div(
            [
                # Header
                dmc.Paper(
                    [
                        dmc.Group(
                            [
                                dmc.Button(
                                    DashIconify(icon="carbon:arrow-left", width=20),
                                    id="back-to-insights",
                                    variant="subtle",
                                    color="gray",
                                    size="sm",
                                ),
                                dmc.Divider(orientation="vertical", size="sm"),
                                dmc.Stack(
                                    [
                                        dmc.Text(name, size="xl", fw="bold", c="blue"),
                                        dmc.Group(
                                            [
                                                dmc.Badge(
                                                    issuer,
                                                    color="blue",
                                                    variant="light",
                                                    size="sm",
                                                ),
                                                dmc.Text(
                                                    formatted_date,
                                                    size="sm",
                                                    c="gray",
                                                ),
                                            ],
                                            gap="sm",
                                        ),
                                    ],
                                    gap="xs",
                                    style={"flex": 1},
                                ),
                                dmc.Group(
                                    [
                                        dmc.Anchor(
                                            dmc.Button(
                                                "Download PDF",
                                                leftSection=DashIconify(
                                                    icon="carbon:download", width=16
                                                ),
                                                variant="light",
                                                color="red",
                                                size="sm",
                                            ),
                                            href=f"/api/download-pdf/{insight_id}",
                                            target="_blank",
                                            style={"textDecoration": "none"},
                                        ),
                                        dmc.ActionIcon(
                                            DashIconify(icon="carbon:close", width=20),
                                            id="close-pdf-viewer",
                                            variant="subtle",
                                            color="gray",
                                            size="md",
                                        ),
                                    ],
                                    gap="xs",
                                ),
                            ],
                            justify="space-between",
                            align="center",
                        )
                    ],
                    p="md",
                    radius="md",
                    style={"marginBottom": "16px"},
                ),
                # Main content area
                dmc.Grid(
                    [
                        # PDF Viewer (left side)
                        dmc.GridCol(
                            [
                                dmc.Paper(
                                    [
                                        dmc.Stack(
                                            [
                                                dmc.Group(
                                                    [
                                                        DashIconify(
                                                            icon="carbon:document-pdf",
                                                            width=20,
                                                            color="red",
                                                        ),
                                                        dmc.Text(
                                                            "Document Preview",
                                                            size="lg",
                                                            fw="bold",
                                                            c="blue",
                                                        ),
                                                    ],
                                                    gap="sm",
                                                ),
                                                dmc.Divider(),
                                                # PDF embed area
                                                html.Div(
                                                    [
                                                        html.Iframe(
                                                            src=f"/api/download-pdf/{insight_id}#toolbar=1&navpanes=1&scrollbar=1",
                                                            style={
                                                                "width": "100%",
                                                                "height": "800px",
                                                                "border": "none",
                                                                "borderRadius": "8px",
                                                                "backgroundColor": "#f8f9fa",
                                                            },
                                                            title=f"PDF Viewer - {name}",
                                                        )
                                                    ],
                                                    style={
                                                        "border": "1px solid #ccc",
                                                        "borderRadius": "8px",
                                                        "overflow": "hidden",
                                                        "backgroundColor": "white",
                                                        "position": "relative",
                                                    },
                                                ),
                                            ],
                                            gap="md",
                                        )
                                    ],
                                    p="lg",
                                    radius="md",
                                    withBorder=True,
                                )
                            ],
                            span={"base": 12, "md": 8},
                        ),
                        # Summary Sidebar (right side)
                        dmc.GridCol(
                            [
                                dmc.Paper(
                                    [
                                        dmc.Stack(
                                            [
                                                dmc.Group(
                                                    [
                                                        DashIconify(
                                                            icon="carbon:notebook",
                                                            width=20,
                                                            color="cyan",
                                                        ),
                                                        dmc.Text(
                                                            "AI Summary",
                                                            size="lg",
                                                            fw="bold",
                                                            c="cyan",
                                                        ),
                                                    ],
                                                    gap="sm",
                                                ),
                                                dmc.Divider(),
                                                # Summary content
                                                dmc.ScrollArea(
                                                    [
                                                        dmc.Stack(
                                                            [
                                                                dmc.Text(
                                                                    (
                                                                        summary
                                                                        if summary
                                                                        else "No AI summary available for this document."
                                                                    ),
                                                                    size="sm",
                                                                    style={
                                                                        "lineHeight": "1.6"
                                                                    },
                                                                    c=(
                                                                        "gray"
                                                                        if not summary
                                                                        else None
                                                                    ),
                                                                ),
                                                                # Action buttons for summary
                                                                dmc.Group(
                                                                    [
                                                                        dmc.Button(
                                                                            "Regenerate Summary",
                                                                            leftSection=DashIconify(
                                                                                icon="carbon:ai",
                                                                                width=16,
                                                                            ),
                                                                            variant="light",
                                                                            color="cyan",
                                                                            size="sm",
                                                                            id={
                                                                                "type": "regenerate-summary",
                                                                                "index": insight_id,
                                                                            },
                                                                            disabled=not insight.get(
                                                                                "has_content",
                                                                                False,
                                                                            ),
                                                                        ),
                                                                        dmc.Button(
                                                                            "Copy Summary",
                                                                            leftSection=DashIconify(
                                                                                icon="carbon:copy",
                                                                                width=16,
                                                                            ),
                                                                            variant="subtle",
                                                                            color="gray",
                                                                            size="sm",
                                                                            id={
                                                                                "type": "copy-summary",
                                                                                "index": insight_id,
                                                                            },
                                                                        ),
                                                                    ],
                                                                    gap="xs",
                                                                    grow=True,
                                                                ),
                                                            ],
                                                            gap="md",
                                                        )
                                                    ],
                                                    style={
                                                        "height": "600px",
                                                        "paddingRight": "8px",
                                                    },
                                                ),
                                                # Document metadata
                                                dmc.Divider(
                                                    label="Document Info",
                                                    labelPosition="center",
                                                ),
                                                dmc.Stack(
                                                    [
                                                        dmc.Group(
                                                            [
                                                                dmc.Text(
                                                                    "Publisher:",
                                                                    size="sm",
                                                                    fw="normal",
                                                                    c="gray",
                                                                    style={
                                                                        "width": "80px"
                                                                    },
                                                                ),
                                                                dmc.Text(
                                                                    issuer, size="sm"
                                                                ),
                                                            ],
                                                            justify="space-between",
                                                        ),
                                                        dmc.Group(
                                                            [
                                                                dmc.Text(
                                                                    "Published:",
                                                                    size="sm",
                                                                    fw="normal",
                                                                    c="gray",
                                                                    style={
                                                                        "width": "80px"
                                                                    },
                                                                ),
                                                                dmc.Text(
                                                                    formatted_date,
                                                                    size="sm",
                                                                ),
                                                            ],
                                                            justify="space-between",
                                                        ),
                                                        dmc.Group(
                                                            [
                                                                dmc.Text(
                                                                    "Status:",
                                                                    size="sm",
                                                                    fw="normal",
                                                                    c="gray",
                                                                    style={
                                                                        "width": "80px"
                                                                    },
                                                                ),
                                                                dmc.Badge(
                                                                    (
                                                                        "Processed"
                                                                        if summary
                                                                        else "Pending"
                                                                    ),
                                                                    color=(
                                                                        "green"
                                                                        if summary
                                                                        else "yellow"
                                                                    ),
                                                                    variant="light",
                                                                    size="sm",
                                                                ),
                                                            ],
                                                            justify="space-between",
                                                        ),
                                                    ],
                                                    gap="sm",
                                                ),
                                            ],
                                            gap="md",
                                        )
                                    ],
                                    p="lg",
                                    radius="md",
                                    withBorder=True,
                                    style={"height": "fit-content"},
                                )
                            ],
                            span={"base": 12, "md": 4},
                        ),
                    ],
                    gutter="md",
                ),
            ],
            style={"padding": "16px"},
        )

    def _format_date(self, date_str: str) -> str:
        """Format date string for display"""
        if not date_str:
            return "Unknown Date"

        try:
            if isinstance(date_str, str) and len(date_str) >= 10:
                from datetime import datetime

                date_obj = datetime.strptime(date_str[:10], "%Y-%m-%d")
                return date_obj.strftime("%b %d, %Y")
            return date_str
        except:
            return date_str


def create_pdf_viewer(insight_data: Dict[str, Any]) -> html.Div:
    """Factory function to create PDF viewer"""
    viewer = PDFViewer()
    return viewer.create_pdf_viewer_layout(insight_data)
