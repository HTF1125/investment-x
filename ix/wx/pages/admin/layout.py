from dash import html, register_page
import dash_bootstrap_components as dbc
from ix.wx.pages.admin import excel_uploader

register_page(__name__, path="/admin", title="Admin", name="Admin")

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
            ],
            style={
                "display": "flex",
                "flexDirection": "column",
                "gap": "10px",  # Only a 10px gap between sections
            },
        )
    ],
)
