from dash import html, dcc, register_page
import dash_bootstrap_components as dbc

# Register the page with a path and optional name (shown in page registry)
register_page(__name__, path="/", name="Home")

# Layout of the page
layout = html.Div(
    [
        dbc.Container(
            [
                html.H2("Home Page"),
                html.P("This is the home page of your Dash app."),
                dbc.Textarea(
                    id="ff", placeholder="Type something...", style={"width": "100%"}
                ),
                html.Br(),
                dcc.Link("Go to Another Page", href="/dash/about"),
            ]
        )
    ]
)
