import dash

from dash import html
import dash_bootstrap_components as dbc
# from ix.wx.components import technical
from ix.wx.pages.dashboard import performance
from ix.wx.pages.dashboard import commentary
from ix.wx.pages.dashboard import technical

# Register Page
dash.register_page(
    __name__,
    path="/",
    title="Dashboard",
    name="Dashboard"
)

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
                performance.layout,
                technical.get_layout(),
                commentary.layout,
            ],
            style={
                "display": "flex",
                "flexDirection": "column",
                "gap": "10px",
            },
        )
    ],
)
