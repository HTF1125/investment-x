"""Professional insights report browser component."""

from typing import Any, Dict, List
from dash import html
import dash_mantine_components as dmc
from dash_iconify import DashIconify

from ix.web.pages.insights.utils.formatters import format_date, format_date_for_display, truncate_text


def create_table_row(insight_data: Dict[str, Any]) -> html.Tr:
    """Create an enhanced table row for an insight - clickable to view PDF in new window."""
    insight_id = insight_data.get("id", "")
    name = insight_data.get("name", "Untitled Report")
    issuer = insight_data.get("issuer", "Unknown")
    published_date_display = format_date_for_display(insight_data.get("published_date", ""))
    url = insight_data.get("url", "#")

    # Row styling for hover effect
    row_style = {
        "transition": "background-color 0.2s ease",
        "cursor": "pointer",
        "height": "48px",
    }

    return html.Tr(
        [
            # Icon Column
            html.Td(
                DashIconify(icon="vscode-icons:file-type-pdf2", width=20),
                style={"width": "40px", "textAlign": "center", "padding": "0 10px"}
            ),
            # Title Column
            html.Td(
                html.A(
                    dmc.Text(
                        name,
                        size="sm",
                        fw=500,
                        c="blue.4",
                        style={"lineHeight": "1.4"}
                    ),
                    href=url,
                    target="_blank",
                    style={"textDecoration": "none", "display": "block"}
                ),
                style={"padding": "12px", "maxWidth": "500px"}
            ),
            # Issuer Column
            html.Td(
                dmc.Badge(
                    issuer,
                    variant="dot",
                    color="gray",
                    size="sm",
                    radius="sm",
                    style={"textTransform": "none", "backgroundColor": "transparent"}
                ),
                style={"padding": "12px", "whiteSpace": "nowrap"}
            ),
            # Date Column
            html.Td(
                dmc.Text(
                    published_date_display,
                    size="xs",
                    c="dimmed",
                    ff="monospace",
                ),
                style={"padding": "12px", "whiteSpace": "nowrap", "width": "120px"}
            ),
            # Action Column
            html.Td(
                html.A(
                     dmc.ActionIcon(
                        DashIconify(icon="carbon:launch", width=16),
                        variant="subtle",
                        color="gray",
                        size="sm"
                     ),
                     href=url,
                     target="_blank"
                ),
                style={"width": "50px", "textAlign": "center", "padding": "0 10px"}
            )
        ],
        id=f"insight-row-{insight_id}",
        className="insight-table-row",
        style=row_style
    )


def create_insights_table(insights_data: List[Dict[str, Any]]) -> html.Div:
    """Create an enhanced Mantine table from insights data."""
    if not insights_data:
        return html.Div(
            [
                dmc.Stack(
                    [
                        DashIconify(icon="carbon:document-blank", width=60, color="#475569"),
                        dmc.Text("No documents found", size="md", c="gray.6"),
                    ],
                    align="center",
                    gap="sm",
                ),
            ],
            style={
                "padding": "60px 20px",
                "textAlign": "center",
                "backgroundColor": "#1e293b",
                "borderRadius": "8px",
                "border": "1px dashed #334155",
            },
        )

    # Create table rows
    table_rows = [create_table_row(insight) for insight in insights_data]

    return dmc.Table(
        children=[
            html.Thead(
                html.Tr(
                    [
                        html.Th("", style={"width": "40px"}), # Icon placeholder
                        html.Th(
                            dmc.Text("Document Name", size="xs", fw=700, c="dimmed", tt="uppercase"),
                            style={"padding": "12px"}
                        ),
                        html.Th(
                            dmc.Text("Issuer", size="xs", fw=700, c="dimmed", tt="uppercase"),
                            style={"padding": "12px"}
                        ),
                        html.Th(
                            dmc.Text("Date", size="xs", fw=700, c="dimmed", tt="uppercase"),
                            style={"padding": "12px"}
                        ),
                        html.Th("", style={"width": "50px"}), # Action placeholder
                    ],
                    style={"backgroundColor": "#0f172a", "borderBottom": "1px solid #334155"}
                )
            ),
            html.Tbody(table_rows, style={"backgroundColor": "#1e293b"}),
        ],
        striped=True,
        highlightOnHover=True,
        withTableBorder=True,
        withColumnBorders=False,
        verticalSpacing="xs",
        horizontalSpacing="md",
        style={
            "borderRadius": "8px",
            "overflow": "hidden",
            "border": "1px solid #334155",
            "marginBottom": "20px"
        }
    )
