from dash import html, dcc
from dash_iconify import DashIconify
import dash_mantine_components as dmc

layout = dmc.Modal(
    [
        # Header content
        dmc.Group(
            [
                html.Div(id="modal-header"),
                dmc.Button(
                    "×",
                    id="close-modal",
                    size="sm",
                    variant="subtle",
                    color="gray",
                    style={"minWidth": "32px", "height": "32px"},
                ),
            ],
            justify="space-between",
            align="center",
            style={"marginBottom": "16px"},
        ),
        # Overview section
        dmc.Divider(label="Overview", size="sm", style={"marginBottom": "16px"}),
        html.Div(id="tab-overview", style={"marginBottom": "24px"}),
        # Details section
        dmc.Divider(label="Details", size="sm", style={"marginBottom": "16px"}),
        html.Div(id="tab-details", style={"marginBottom": "24px"}),
        # Chart section
        dmc.Divider(label="Chart", size="sm", style={"marginBottom": "16px"}),
        dcc.Graph(id="chart", style={"height": "400px", "marginBottom": "24px"}),
        # Data section
        dmc.Divider(label="Data", size="sm", style={"marginBottom": "16px"}),
        html.Div(id="tab-data", style={"marginBottom": "24px"}),
        # Footer actions
        dmc.Group(
            [
                dmc.Button(
                    "Edit",
                    id="edit-btn",
                    variant="outline",
                    color="blue",
                    leftSection=DashIconify(icon="material-symbols:edit"),
                ),
                dmc.Button(
                    "Export",
                    id="export-btn",
                    variant="outline",
                    color="green",
                    leftSection=DashIconify(icon="material-symbols:download"),
                ),
                dmc.Button(
                    "Delete",
                    id="delete-btn",
                    variant="outline",
                    color="red",
                    leftSection=DashIconify(icon="material-symbols:delete"),
                ),
            ],
            gap="sm",
            justify="flex-start",
        ),
    ],
    id="detail-modal",
    size="xl",
    centered=True,
)
