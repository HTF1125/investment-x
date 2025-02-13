import dash_bootstrap_components as dbc
from dash import html

footer = dbc.Container(
    fluid=True,
    className="fixed-bottom border-top",
    style={
        "height": "20px",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
    },
    children=[
        html.Div(
            "© 2025 Investment X",
            className="text-center",
            style={
                "fontSize": "14px",
            }
        )
    ]
)
