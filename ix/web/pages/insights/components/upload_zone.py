"""Drag-and-drop PDF upload zone component with collapsible dropdown."""

from dash import html, dcc
import dash_mantine_components as dmc
from dash_iconify import DashIconify


def create_upload_zone() -> html.Div:
    """Create a collapsible drag-and-drop upload zone for PDF files."""
    return html.Div(
        [
            # Toggle button to show/hide upload zone
            dmc.Button(
                "Upload PDF",
                id="toggle-upload-zone",
                variant="subtle",
                color="blue",
                size="md",
                radius="md",
                leftSection=DashIconify(icon="carbon:upload", width=18),
                rightSection=DashIconify(icon="carbon:chevron-down", width=16),
                style={
                    "marginBottom": "12px",
                },
            ),
            # Collapsible upload zone (hidden by default)
            html.Div(
                dcc.Upload(
                    html.Div(
                        [
                            dmc.Stack(
                                [
                                    dmc.ThemeIcon(
                                        DashIconify(icon="carbon:cloud-upload", width=48),
                                        size="xl",
                                        radius="xl",
                                        variant="light",
                                        color="blue",
                                        style={"marginBottom": "8px"},
                                    ),
                                    dmc.Text(
                                        "Drag and drop PDF files here",
                                        size="lg",
                                        fw="600",
                                        c="gray.3",
                                        style={"marginBottom": "4px"},
                                    ),
                                    dmc.Text(
                                        "or click to browse",
                                        size="sm",
                                        c="gray.6",
                                    ),
                                    dmc.Text(
                                        "Supports multiple files • PDF format only",
                                        size="xs",
                                        c="gray.7",
                                        style={"marginTop": "8px"},
                                    ),
                                ],
                                align="center",
                                gap="xs",
                            ),
                        ],
                        style={
                            "padding": "40px 40px",
                            "textAlign": "center",
                            "width": "100%",
                            "minHeight": "150px",
                            "display": "flex",
                            "alignItems": "center",
                            "justifyContent": "center",
                        },
                        className="upload-zone-content",
                    ),
                    id="upload-pdf-dragdrop",
                    multiple=True,
                    accept=".pdf",
                    style={
                        "width": "100%",
                        "height": "100%",
                        "border": "2px dashed #475569",
                        "borderRadius": "12px",
                        "backgroundColor": "#1e293b",
                        "cursor": "pointer",
                        "transition": "all 0.3s ease",
                    },
                    className="pdf-upload-zone",
                ),
                id="upload-zone-container",
                style={
                    "marginBottom": "24px",
                    "flexShrink": 0,
                    "display": "none",  # Hidden by default
                },
            ),
        ],
        style={
            "marginBottom": "16px",
        },
    )
