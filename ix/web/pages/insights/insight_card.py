"""
Modern Insight Card Component - Redesigned with Dash Mantine Components
Beautiful card-based design with enhanced visual hierarchy and UX
"""

from typing import Dict, Any
from dash import html
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from datetime import datetime


class InsightCard:
    """Modern insight card with beautiful design and improved UX."""

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
                        "New",
                        color="green",
                        variant="light",
                        size="sm",
                        leftSection=DashIconify(
                            icon="material-symbols:fiber-new", width=14
                        ),
                    )
                elif days_ago <= 30:
                    return dmc.Badge(
                        "Recent",
                        color="blue",
                        variant="light",
                        size="sm",
                        leftSection=DashIconify(
                            icon="material-symbols:schedule", width=14
                        ),
                    )
            except:
                pass

        return dmc.Badge(
            "Archived",
            color="gray",
            variant="light",
            size="sm",
            leftSection=DashIconify(icon="material-symbols:inventory", width=14),
        )

    def _create_action_buttons(self, insight: Dict[str, Any]) -> dmc.Group:
        """Create modern action buttons."""
        insight_id = insight.get("id")

        return dmc.Group(
            [
                dmc.Button(
                    "View",
                    id={"type": "insight-card-clickable", "index": insight_id},
                    n_clicks=0,
                    leftSection=DashIconify(
                        icon="material-symbols:visibility", width=18
                    ),
                    variant="filled",
                    color="blue",
                    size="sm",
                    radius="md",
                ),
                dmc.Button(
                    "PDF",
                    component="a",
                    href=f"https://files.investment-x.app/{insight_id}.pdf",
                    target="_blank",
                    leftSection=DashIconify(
                        icon="material-symbols:picture-as-pdf", width=18
                    ),
                    variant="light",
                    color="red",
                    size="sm",
                    radius="md",
                ),
                dmc.ActionIcon(
                    DashIconify(icon="material-symbols:delete-outline", width=18),
                    id={"type": "delete-insight-button", "index": insight_id},
                    n_clicks=0,
                    variant="subtle",
                    color="red",
                    size="lg",
                    radius="md",
                ),
            ],
            gap="xs",
        )

    def _create_summary_preview(self, insight: Dict[str, Any]) -> html.Div:
        """Create a preview of the summary."""
        summary = insight.get("summary", "")
        if not summary:
            return dmc.Text(
                "No summary available",
                c="dimmed",
                size="sm",
                fs="italic",
            )

        # Truncate summary for preview
        preview_text = summary[:200] + "..." if len(summary) > 200 else summary

        return dmc.Text(
            preview_text,
            size="sm",
            c="dimmed",
            style={"lineHeight": "1.6"},
        )

    def layout(self, insight: Dict[str, Any]):
        """Create the modern insight card layout."""
        # Extract data
        published_date = self._format_date(insight.get("published_date", ""))
        issuer = insight.get("issuer", "Unknown Issuer")
        name = insight.get("name", "Untitled Document")
        insight_id = insight.get("id")

        # Get issuer badge color
        issuer_color = self._get_issuer_badge_color(issuer)

        # Create status badge
        status_badge = self._create_status_badge(insight)

        # Create action buttons
        action_buttons = self._create_action_buttons(insight)

        # Create summary preview
        summary_preview = self._create_summary_preview(insight)

        # Main card with modern design
        card = dmc.Card(
            [
                dmc.CardSection(
                    dmc.Group(
                        [
                            dmc.Badge(
                                issuer,
                                color=issuer_color,
                                variant="light",
                                size="lg",
                                leftSection=DashIconify(
                                    icon="material-symbols:business", width=16
                                ),
                            ),
                            status_badge,
                        ],
                        gap="xs",
                    ),
                    inheritPadding=True,
                    py="xs",
                ),
                dmc.CardSection(
                    [
                        dmc.Title(
                            name,
                            order=5,
                            style={
                                "marginBottom": "8px",
                                "lineHeight": "1.4",
                                "fontWeight": "600",
                            },
                        ),
                        dmc.Group(
                            [
                                dmc.Text(
                                    published_date,
                                    size="xs",
                                    c="dimmed",
                                    style={
                                        "display": "flex",
                                        "alignItems": "center",
                                        "gap": "4px",
                                    },
                                ),
                                DashIconify(
                                    icon="material-symbols:calendar-month",
                                    width=14,
                                    style={"color": "var(--mantine-color-dimmed)"},
                                ),
                            ],
                            gap=4,
                        ),
                    ],
                    inheritPadding=True,
                    pt="xs",
                    pb="md",
                ),
                dmc.CardSection(
                    dmc.Paper(
                        [
                            dmc.Text(
                                "Summary",
                                size="xs",
                                fw=600,
                                c="blue",
                                style={
                                    "marginBottom": "8px",
                                    "textTransform": "uppercase",
                                    "letterSpacing": "0.5px",
                                },
                            ),
                            summary_preview,
                        ],
                        p="md",
                        radius="md",
                        withBorder=True,
                        style={"backgroundColor": "rgba(59, 130, 246, 0.05)"},
                    ),
                    inheritPadding=True,
                    pb="md",
                ),
                dmc.CardSection(
                    dmc.Group(
                        [
                            dmc.Text(
                                f"ID: {insight_id}",
                                size="xs",
                                c="dimmed",
                                style={"fontFamily": "monospace"},
                            ),
                            action_buttons,
                        ],
                        justify="space-between",
                        align="center",
                    ),
                    inheritPadding=True,
                    py="sm",
                    style={"borderTop": "1px solid var(--mantine-color-dark-4)"},
                ),
            ],
            shadow="sm",
            padding="lg",
            radius="lg",
            withBorder=True,
            className="insight-card-hover",
            style={
                "height": "100%",
                "transition": "all 0.3s ease",
            },
        )

        return card


def create_insight_card(insight_data):
    """
    Factory function to create a modern insight card.
    Maintains backward compatibility with existing callback code.
    """
    card_instance = InsightCard()
    return card_instance.layout(insight_data)
