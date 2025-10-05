"""
Modern Insight Card Component
Enhanced design with better visual hierarchy, improved readability, and modern UI patterns.
"""

from typing import Dict, Any
from dash import html
import dash_bootstrap_components as dbc
from datetime import datetime

# Modern Color Scheme
COLORS = {
    "primary": "#3b82f6",
    "secondary": "#64748b",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "dark": "#1e293b",
    "light": "#f8fafc",
    "background": "#0f172a",
    "surface": "#1e293b",
    "surface_light": "#334155",
    "text_primary": "#f1f5f9",
    "text_secondary": "#94a3b8",
    "border": "#475569",
}


class InsightCard:
    """Enhanced insight card with modern design and improved UX."""

    def __init__(self):
        self.colors = COLORS

    def _format_date(self, date_str: str) -> str:
        """Format date string for display."""
        if not date_str:
            return "Unknown Date"

        try:
            if isinstance(date_str, str) and len(date_str) >= 10:
                date_obj = datetime.strptime(date_str[:10], "%Y-%m-%d")
                return date_obj.strftime("%b %d, %Y")
            return date_str
        except:
            return date_str

    def _get_issuer_color(self, issuer: str) -> str:
        """Get color based on issuer name."""
        issuer_colors = {
            "federal reserve": self.colors["primary"],
            "fed": self.colors["primary"],
            "treasury": self.colors["success"],
            "sec": self.colors["warning"],
            "ecb": self.colors["secondary"],
            "boe": self.colors["danger"],
        }

        issuer_lower = issuer.lower()
        for key, color in issuer_colors.items():
            if key in issuer_lower:
                return color
        return self.colors["secondary"]

    def _create_status_badge(self, insight: Dict[str, Any]) -> html.Span:
        """Create status badge based on insight data."""
        published_date = insight.get("published_date", "")
        if published_date:
            try:
                date_obj = datetime.strptime(published_date[:10], "%Y-%m-%d")
                days_ago = (datetime.now() - date_obj).days

                if days_ago <= 7:
                    return html.Span(
                        "🆕 New",
                        className="badge bg-success",
                        style={"fontSize": "0.7rem", "marginLeft": "8px"},
                    )
                elif days_ago <= 30:
                    return html.Span(
                        "📅 Recent",
                        className="badge bg-info",
                        style={"fontSize": "0.7rem", "marginLeft": "8px"},
                    )
            except:
                pass

        return html.Span(
            "📄 Archived",
            className="badge bg-secondary",
            style={"fontSize": "0.7rem", "marginLeft": "8px"},
        )

    def _create_action_buttons(self, insight: Dict[str, Any]) -> html.Div:
        """Create modern action buttons."""
        insight_id = insight.get("id")

        # View Summary Button
        view_button = dbc.Button(
            [html.I(className="fas fa-eye me-1"), "View"],
            id={"type": "insight-card-clickable", "index": insight_id},
            n_clicks=0,
            color="primary",
            size="sm",
            style={
                "borderRadius": "6px",
                "fontSize": "0.8rem",
                "padding": "4px 12px",
            },
        )

        # PDF Download Button
        pdf_button = dbc.Button(
            [html.I(className="fas fa-file-pdf me-1"), "PDF"],
            href=f"https://files.investment-x.app/{insight_id}.pdf",
            target="_blank",
            color="outline-danger",
            size="sm",
            style={
                "borderRadius": "6px",
                "fontSize": "0.8rem",
                "padding": "4px 12px",
                "borderColor": self.colors["danger"],
                "color": self.colors["danger"],
            },
        )

        # Delete Button
        delete_button = dbc.Button(
            [html.I(className="fas fa-trash-alt me-1"), "Delete"],
            id={"type": "delete-insight-button", "index": insight_id},
            color="outline-danger",
            size="sm",
            n_clicks=0,
            style={
                "borderRadius": "6px",
                "fontSize": "0.8rem",
                "padding": "4px 12px",
                "borderColor": self.colors["danger"],
                "color": self.colors["danger"],
            },
        )

        return html.Div(
            [view_button, pdf_button, delete_button],
            className="d-flex gap-2",
            style={"justifyContent": "flex-end"},
        )

    def _create_summary_preview(self, insight: Dict[str, Any]) -> html.P:
        """Create a preview of the summary."""
        summary = insight.get("summary", "")
        if not summary:
            return html.P(
                "No summary available",
                className="text-muted mb-0",
                style={"fontSize": "0.85rem", "fontStyle": "italic"},
            )

        # Truncate summary for preview
        preview_text = summary[:150] + "..." if len(summary) > 150 else summary

        return html.P(
            preview_text,
            className="mb-0",
            style={
                "fontSize": "0.85rem",
                "lineHeight": "1.4",
                "color": self.colors["text_secondary"],
            },
        )

    def layout(self, insight: Dict[str, Any]):
        """Create the enhanced insight card layout."""
        # Extract data
        published_date = self._format_date(insight.get("published_date", ""))
        issuer = insight.get("issuer", "Unknown Issuer")
        name = insight.get("name", "Untitled Document")
        insight_id = insight.get("id")

        # Get issuer color
        issuer_color = self._get_issuer_color(issuer)

        # Create status badge
        status_badge = self._create_status_badge(insight)

        # Create action buttons
        action_buttons = self._create_action_buttons(insight)

        # Create summary preview
        summary_preview = self._create_summary_preview(insight)

        # Main card
        card = dbc.Card(
            [
                dbc.CardBody(
                    [
                        # Header Row
                        dbc.Row(
                            [
                                dbc.Col(
                                    [
                                        html.Div(
                                            [
                                                html.H5(
                                                    name,
                                                    className="mb-1",
                                                    style={
                                                        "color": self.colors[
                                                            "text_primary"
                                                        ],
                                                        "fontSize": "1.1rem",
                                                        "fontWeight": "600",
                                                        "lineHeight": "1.3",
                                                    },
                                                ),
                                                html.Div(
                                                    [
                                                        html.Span(
                                                            f"📅 {published_date}",
                                                            style={
                                                                "color": self.colors[
                                                                    "text_secondary"
                                                                ],
                                                                "fontSize": "0.8rem",
                                                                "marginRight": "12px",
                                                            },
                                                        ),
                                                        html.Span(
                                                            f"🏢 {issuer}",
                                                            style={
                                                                "color": issuer_color,
                                                                "fontSize": "0.8rem",
                                                                "fontWeight": "500",
                                                            },
                                                        ),
                                                        status_badge,
                                                    ],
                                                    className="mb-2",
                                                ),
                                            ]
                                        )
                                    ],
                                    md=8,
                                ),
                                dbc.Col(
                                    action_buttons,
                                    md=4,
                                    className="d-flex align-items-start justify-content-end",
                                ),
                            ],
                            className="mb-3",
                        ),
                        # Summary Preview
                        html.Div(
                            [
                                html.H6(
                                    "Summary Preview:",
                                    style={
                                        "color": self.colors["text_primary"],
                                        "fontSize": "0.9rem",
                                        "fontWeight": "600",
                                        "marginBottom": "8px",
                                    },
                                ),
                                summary_preview,
                            ],
                            className="mb-3",
                            style={
                                "padding": "12px",
                                "backgroundColor": self.colors["background"],
                                "borderRadius": "8px",
                                "border": f"1px solid {self.colors['border']}",
                            },
                        ),
                        # Footer with metadata
                        html.Div(
                            [
                                html.Small(
                                    f"ID: {insight_id}",
                                    style={
                                        "color": self.colors["text_secondary"],
                                        "fontSize": "0.7rem",
                                        "fontFamily": "monospace",
                                    },
                                ),
                            ],
                            className="text-end",
                        ),
                    ],
                    style={"padding": "20px"},
                )
            ],
            className="mb-3",
            style={
                "border": f"1px solid {self.colors['border']}",
                "borderRadius": "12px",
                "backgroundColor": self.colors["surface"],
                "transition": "all 0.3s ease",
                "boxShadow": "0 2px 4px rgba(0, 0, 0, 0.1)",
            },
        )

        # Card is ready for hover effects via CSS

        return card


def create_insight_card(insight_data):
    """
    Factory function to create an enhanced insight card.
    Maintains backward compatibility with existing callback code.
    """
    card_instance = InsightCard()
    return card_instance.layout(insight_data)
