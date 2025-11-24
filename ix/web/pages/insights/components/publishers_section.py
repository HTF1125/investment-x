"""Publishers section component."""

from dash import html
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from datetime import datetime


def _format_last_visited(last_visited_str: str) -> str:
    """Format last visited timestamp for display."""
    if not last_visited_str:
        return "Never"
    try:
        dt = datetime.fromisoformat(last_visited_str.replace("Z", "+00:00"))
        now = datetime.now()
        diff = now - dt.replace(tzinfo=None)
        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        return "Just now"
    except:
        return "Unknown"


def create_publishers_list_items(publishers):
    """Create list items for publishers."""
    if not publishers:
        return dmc.Text("No publishers configured.", size="sm", c="gray", ta="center")

    items = []
    for pub in publishers:
        if isinstance(pub, dict):
            pub_id = str(pub.get("id", ""))
            name = pub.get("name", "Unknown")
            url = pub.get("url", "#")
            frequency = pub.get("frequency", "Weekly")
            last_visited = pub.get("last_visited", "")
        else:
            pub_id = str(pub.id)
            name = pub.name or "Unknown"
            url = pub.url or "#"
            frequency = pub.frequency or "Weekly"
            last_visited = pub.last_visited

        last_visited_display = _format_last_visited(
            last_visited.isoformat() if hasattr(last_visited, "isoformat") else str(last_visited)
        ) if last_visited else "Never"

        items.append(
            html.Div(
                [
                    html.Div(
                        [
                            dmc.Text(name, size="sm", fw="bold"),
                            dmc.Group(
                                [
                                    dmc.Badge(frequency, variant="light", color="blue", size="xs"),
                                    dmc.Text(last_visited_display, size="xs", c="gray"),
                                ],
                                gap="xs",
                            ),
                        ],
                        style={"flex": 1},
                    ),
                    dmc.Anchor(
                        dmc.ActionIcon(
                            DashIconify(icon="carbon:launch", width=16),
                            variant="light",
                            color="blue",
                            size="sm",
                        ),
                        href=url,
                        target="_blank",
                        id={"type": "visit-publisher", "index": pub_id},
                    ),
                ],
                style={
                    "display": "flex",
                    "alignItems": "center",
                    "justifyContent": "space-between",
                    "padding": "8px 12px",
                    "borderBottom": "1px solid rgba(148, 163, 184, 0.2)",
                },
            )
        )

    return items


def create_publishers_section() -> dmc.GridCol:
    """Create the publishers section."""
    return dmc.GridCol(
        dmc.Stack(
            [
                dmc.Card(
                    [
                        dmc.Stack(
                            [
                                html.Div(
                                    [
                                        dmc.Group(
                                            [
                                                DashIconify(icon="carbon:rss", width=20),
                                                dmc.Text("Publishers", size="sm", fw="bold"),
                                            ],
                                            gap="xs",
                                            style={"flex": 1},
                                        ),
                                        dmc.ActionIcon(
                                            DashIconify(icon="carbon:add", width=18),
                                            id="add-publisher-button",
                                            variant="light",
                                            color="blue",
                                            size="md",
                                            radius="md",
                                        ),
                                    ],
                                    style={
                                        "display": "flex",
                                        "justifyContent": "space-between",
                                        "alignItems": "center",
                                        "marginBottom": "12px",
                                    },
                                ),
                                html.Div(
                                    id="insight-sources-list",
                                    children=[
                                        dmc.Text("Loading sources...", size="sm", c="gray", ta="center"),
                                    ],
                                    style={
                                        "maxHeight": "300px",
                                        "overflowY": "auto",
                                        "overflowX": "hidden",
                                    },
                                ),
                            ],
                            gap="sm",
                        ),
                    ],
                    padding="md",
                    radius="lg",
                    withBorder=True,
                    shadow="sm",
                ),
            ],
            gap="md",
        ),
        span={"base": 12, "md": 6},
    )
