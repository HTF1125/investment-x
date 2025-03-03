import dash

from dash import html
import dash_bootstrap_components as dbc



# Register Page
dash.register_page(__name__, path="/macro", title="Macro", name="Macro")

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

            ],
            style={
                "display": "flex",
                "flexDirection": "column",
                "gap": "10px",
            },
        )
    ],
)
