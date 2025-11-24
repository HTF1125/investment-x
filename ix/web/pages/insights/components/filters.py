"""Filters section component."""

from dash import html
import dash_mantine_components as dmc
from dash_iconify import DashIconify


def create_filters_section() -> dmc.Stack:
    """Create the filters section."""
    return dmc.Stack(
        [
            dmc.Group(
                [
                    dmc.TextInput(
                        id="insights-search",
                        placeholder="Search by title, issuer, date (YYYY-MM-DD), or keywords...",
                        leftSection=DashIconify(icon="carbon:search", width=20),
                        rightSection=dmc.ActionIcon(
                            DashIconify(icon="carbon:close", width=16),
                            variant="subtle",
                            color="gray",
                            id="clear-search",
                        ),
                        size="lg",
                        radius="md",
                        style={"flex": 1},
                    ),
                    dmc.Button(
                        "Search",
                        id="search-button",
                        leftSection=DashIconify(icon="carbon:search", width=16),
                        variant="gradient",
                        gradient={"from": "blue", "to": "cyan", "deg": 90},
                        size="md",
                    ),
                ],
                gap="sm",
                align="center",
            ),
        ],
        gap="md",
    )
