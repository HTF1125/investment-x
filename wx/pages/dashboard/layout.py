import dash

# Register Page
dash.register_page(
    __name__,
    path="/",
    title="Dashboard",
    name="Dashboard"
)

from dash import html
import dash_bootstrap_components as dbc
from wx.components import commentary, technical, performance, excel_uploader

# Wrap the four sections in a flex container with a small gap.
layout = dbc.Container(
    fluid=True,
    className="p-1",  # Minimal outer padding
    style={
        "backgroundColor": "#000000",
    },
    children=[
        html.Div(
            children=[
                excel_uploader.layout,
                performance.get_layout(),
                technical.get_layout(),
                commentary.get_layout(),
            ],
            style={
                "display": "flex",
                "flexDirection": "column",
                "gap": "10px",  # Only a 10px gap between sections
            },
        )
    ],
)

# dash.register_page(__name__, path="/", title="Dashboard", name="Dashboard")

