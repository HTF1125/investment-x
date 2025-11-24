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
    summary = insight_data.get("summary", "")
    summary_preview = truncate_text(summary, max_length=200) if summary else "No summary available"

    return html.Tr(
        [
            html.Td(
                dmc.Text(
                    name,
                    size="sm",
                    fw="600",
                    style={
                        "color": "#f8fafc",
                        "lineHeight": "1.5",
                    },
                ),
                style={
                    "padding": "16px 20px",
                    "verticalAlign": "top",
                    "maxWidth": "320px",
                    "minWidth": "250px",
                },
            ),
            html.Td(
                dmc.Badge(
                    issuer,
                    variant="light",
                    color="blue",
                    size="md",
                    radius="sm",
                ),
                style={
                    "padding": "16px 20px",
                    "verticalAlign": "top",
                    "whiteSpace": "nowrap",
                },
            ),
            html.Td(
                dmc.Text(
                    published_date_display,
                    size="sm",
                    c="gray.5",
                    fw="500",
                ),
                style={
                    "padding": "16px 20px",
                    "verticalAlign": "top",
                    "whiteSpace": "nowrap",
                    "minWidth": "120px",
                },
            ),
            html.Td(
                dmc.Text(
                    summary_preview,
                    size="sm",
                    c="gray.6",
                    style={
                        "display": "-webkit-box",
                        "-webkitLineClamp": "3",
                        "-webkitBoxOrient": "vertical",
                        "overflow": "hidden",
                        "textOverflow": "ellipsis",
                        "lineHeight": "1.6",
                        "maxWidth": "450px",
                    },
                ),
                title=summary if summary else "No summary",
                style={
                    "padding": "16px 20px",
                    "verticalAlign": "top",
                    "maxWidth": "450px",
                },
            ),
        ],
        id=f"insight-row-{insight_id}",
        **{"data-insight-id": str(insight_id)},
        style={
            "borderBottom": "1px solid #334155",
            "transition": "all 0.2s ease",
            "backgroundColor": "transparent",
            "cursor": "pointer",
        },
        className="insight-table-row",
    )


def create_insights_table(insights_data: List[Dict[str, Any]]) -> html.Div:
    """Create an enhanced table from insights data."""
    if not insights_data:
        return html.Div(
            [
                dmc.Stack(
                    [
                        DashIconify(icon="carbon:document-blank", width=80, color="#64748b"),
                        dmc.Text("No research reports found", size="xl", fw="600", c="gray.4"),
                        dmc.Text(
                            "Upload PDF reports to start building your research library",
                            size="sm",
                            c="gray.6",
                        ),
                    ],
                    align="center",
                    gap="md",
                ),
            ],
            style={
                "padding": "100px 20px",
                "textAlign": "center",
                "backgroundColor": "#1e293b",
                "borderRadius": "12px",
                "border": "1px solid #334155",
            },
        )

    # Create table rows
    table_rows = [create_table_row(insight) for insight in insights_data]

    return html.Div(
        [
            html.Table(
                [
                    html.Thead(
                        html.Tr(
                            [
                                html.Th(
                                    dmc.Group(
                                        [
                                            DashIconify(icon="carbon:document", width=16, color="#64748b"),
                                            dmc.Text("Title", size="sm", fw="700", c="gray.3"),
                                        ],
                                        gap="xs",
                                        align="center",
                                    ),
                                    style={
                                        "padding": "16px 20px",
                                        "textAlign": "left",
                                        "fontSize": "13px",
                                        "textTransform": "uppercase",
                                        "letterSpacing": "0.5px",
                                    },
                                ),
                                html.Th(
                                    dmc.Text("Issuer", size="sm", fw="700", c="gray.3"),
                                    style={
                                        "padding": "16px 20px",
                                        "textAlign": "left",
                                        "fontSize": "13px",
                                        "textTransform": "uppercase",
                                        "letterSpacing": "0.5px",
                                    },
                                ),
                                html.Th(
                                    dmc.Text("Date", size="sm", fw="700", c="gray.3"),
                                    style={
                                        "padding": "16px 20px",
                                        "textAlign": "left",
                                        "fontSize": "13px",
                                        "textTransform": "uppercase",
                                        "letterSpacing": "0.5px",
                                    },
                                ),
                                html.Th(
                                    dmc.Text("Summary", size="sm", fw="700", c="gray.3"),
                                    style={
                                        "padding": "16px 20px",
                                        "textAlign": "left",
                                        "fontSize": "13px",
                                        "textTransform": "uppercase",
                                        "letterSpacing": "0.5px",
                                    },
                                ),
                            ],
                            style={
                                "backgroundColor": "#1e293b",
                                "borderBottom": "2px solid #475569",
                                "position": "sticky",
                                "top": "0",
                                "zIndex": "10",
                                "boxShadow": "0 2px 4px rgba(0, 0, 0, 0.1)",
                            },
                        ),
                    ),
                    html.Tbody(table_rows),
                ],
                style={
                    "width": "100%",
                    "borderCollapse": "collapse",
                    "backgroundColor": "#0f172a",
                    "fontSize": "14px",
                },
            ),
        ],
        style={
            "width": "100%",
        },
    )
