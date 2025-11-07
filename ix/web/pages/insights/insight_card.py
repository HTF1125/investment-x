"""
Investment Insights Card - Completely Redesigned
Ultra-modern, clean card design with outstanding visual hierarchy
"""

from typing import Dict, Any
from dash import html
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from datetime import datetime

# Color palette for consistency
COLORS = {
    "primary": "#2563eb",
    "secondary": "#7c3aed",
    "accent": "#0891b2",
    "success": "#059669",
    "warning": "#d97706",
    "danger": "#dc2626",
}


class InsightCard:
    """Completely redesigned insight card with premium aesthetics."""

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

    def _get_issuer_badge_color(self, issuer: str) -> str:
        """Get badge color based on issuer name."""
        issuer_colors = {
            "federal reserve": "blue",
            "fed": "blue",
            "goldman": "indigo",
            "jp morgan": "violet",
            "morgan stanley": "grape",
            "treasury": "green",
            "sec": "orange",
            "ecb": "cyan",
            "boe": "red",
        }

        issuer_lower = issuer.lower()
        for key, color in issuer_colors.items():
            if key in issuer_lower:
                return color
        return "gray"

    def _create_status_badge(self, insight: Dict[str, Any]) -> dmc.Badge:
        """Create status badge based on insight data."""
        published_date = insight.get("published_date", "")
        if published_date:
            try:
                date_obj = datetime.strptime(published_date[:10], "%Y-%m-%d")
                days_ago = (datetime.now() - date_obj).days

                if days_ago <= 7:
                    return dmc.Badge(
                        [DashIconify(icon="carbon:new-tab", width=12), " New"],
                        color="green",
                        variant="filled",
                        size="sm",
                        radius="sm",
                    )
                elif days_ago <= 30:
                    return dmc.Badge(
                        [DashIconify(icon="carbon:time", width=12), " Recent"],
                        color="cyan",
                        variant="light",
                        size="sm",
                        radius="sm",
                    )
            except:
                pass

        return dmc.Badge(
            [DashIconify(icon="carbon:archive", width=12), " Archived"],
            color="gray",
            variant="outline",
            size="sm",
            radius="sm",
        )

    def _create_action_buttons(self, insight: Dict[str, Any]) -> dmc.Group:
        """Create modern action buttons - DEPRECATED, using inline buttons in layout()"""
        # This method is no longer used but kept for backward compatibility
        pass

    def _create_summary_preview(self, insight: Dict[str, Any]) -> html.Div:
        """Create a preview of the summary."""
        summary = insight.get("summary", "")
        if not summary:
            return dmc.Text(
                "No summary available",
                c="gray",
                size="sm",
                fs="italic",
            )

        # Truncate summary for preview
        preview_text = summary[:200] + "..." if len(summary) > 200 else summary

        return dmc.Text(
            preview_text,
            size="sm",
            c="gray",
            style={"lineHeight": "1.6"},
        )

    def layout(self, insight: Dict[str, Any]):
        """Create the completely redesigned insight card layout."""
        # Extract data
        published_date = self._format_date(insight.get("published_date", ""))
        issuer = insight.get("issuer", "Unknown Issuer")
        name = insight.get("name", "Untitled Document")
        insight_id = insight.get("id")
        summary = insight.get("summary", "")

        # Get issuer badge color
        issuer_color = self._get_issuer_badge_color(issuer)

        # Create status badge
        status_badge = self._create_status_badge(insight)

        # Truncate summary for preview
        summary_preview = (
            (summary[:180] + "..." if len(summary) > 180 else summary)
            if summary
            else "No summary available"
        )

        # Ultra-modern card design
        card = dmc.Card(
            [
                # Header gradient bar
                dmc.Box(
                    style={
                        "height": "4px",
                        "background": f"linear-gradient(90deg, {issuer_color} 0%, {issuer_color} 100%)",
                        "borderRadius": "12px 12px 0 0",
                        "marginTop": "-16px",
                        "marginLeft": "-16px",
                        "marginRight": "-16px",
                        "marginBottom": "12px",
                    }
                ),
                # Top section - Badges and meta
                dmc.Group(
                    [
                        dmc.Badge(
                            [
                                DashIconify(icon="carbon:industry", width=12),
                                f" {issuer}",
                            ],
                            color=issuer_color,
                            variant="light",
                            size="md",
                            radius="sm",
                        ),
                        status_badge,
                    ],
                    justify="space-between",
                    align="center",
                    style={"marginBottom": "12px"},
                ),
                # Title section
                dmc.Stack(
                    [
                        dmc.Text(
                            name,
                            size="lg",
                            fw="bold",
                            style={
                                "lineHeight": "1.3",
                                "color": "blue",
                                "cursor": "pointer",
                            },
                            id={"type": "insight-title-click", "index": insight_id},
                        ),
                        dmc.Group(
                            [
                                DashIconify(
                                    icon="carbon:calendar", width=14, color="gray"
                                ),
                                dmc.Text(
                                    published_date, size="xs", c="gray", fw="normal"
                                ),
                            ],
                            gap=6,
                        ),
                    ],
                    gap="xs",
                    style={"marginBottom": "16px"},
                ),
                # Summary section with subtle background
                dmc.Paper(
                    [
                        dmc.Group(
                            [
                                DashIconify(
                                    icon="carbon:notebook",
                                    width=14,
                                    color="cyan",
                                ),
                                dmc.Text(
                                    "AI Summary",
                                    size="xs",
                                    fw="bold",
                                    c="cyan",
                                    tt="uppercase",
                                ),
                            ],
                            gap=6,
                            style={"marginBottom": "8px"},
                        ),
                        dmc.Text(
                            (
                                summary_preview
                                if summary
                                else "Click 'View' to generate AI summary"
                            ),
                            size="sm",
                            c="gray" if summary else "orange",
                            fs="italic" if not summary else "normal",
                            style={"lineHeight": "1.6"},
                        ),
                    ],
                    p="md",
                    radius="md",
                    style={
                        "background": "linear-gradient(135deg, rgba(6, 182, 212, 0.05) 0%, rgba(59, 130, 246, 0.05) 100%)",
                        "border": "1px solid #ccc",
                        "marginBottom": "16px",
                    },
                ),
                # Action buttons section
                dmc.Group(
                    [
                        dmc.Button(
                            "View PDF",
                            id={"type": "view-pdf-button", "index": insight_id},
                            n_clicks=0,
                            leftSection=DashIconify(
                                icon="carbon:document-view", width=16
                            ),
                            variant="gradient",
                            gradient={"from": "blue", "to": "cyan", "deg": 90},
                            size="sm",
                            radius="md",
                            style={"flex": 1},
                        ),
                        dmc.Anchor(
                            dmc.Button(
                                "Download PDF",
                                leftSection=DashIconify(
                                    icon="carbon:download", width=16
                                ),
                                variant="light",
                                color="red",
                                size="sm",
                                radius="md",
                                fullWidth=True,
                            ),
                            href=f"/api/download-pdf/{insight_id}?download=1",
                            target="_blank",
                            style={"textDecoration": "none"},
                        ),
                        dmc.ActionIcon(
                            DashIconify(icon="carbon:trash-can", width=18),
                            id={"type": "delete-insight-button", "index": insight_id},
                            n_clicks=0,
                            variant="subtle",
                            color="red",
                            size="lg",
                            radius="md",
                        ),
                    ],
                    gap="xs",
                    grow=False,
                    style={"marginTop": "4px"},
                ),
                # ID footer removed per request
            ],
            shadow="md",
            padding="lg",
            radius="lg",
            withBorder=True,
            style={
                "height": "100%",
                "transition": "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                "position": "relative",
                "overflow": "hidden",
            },
            className="insight-card-modern",
        )

        return card


def create_insight_card(insight_data):
    """
    Factory function to create a modern insight card.
    Maintains backward compatibility with existing callback code.
    """
    card_instance = InsightCard()
    return card_instance.layout(insight_data)
