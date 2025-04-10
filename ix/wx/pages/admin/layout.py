from dash import html, register_page, callback, Input, Output, dcc
import dash_bootstrap_components as dbc
from ix.wx.pages.admin import excel_uploader

register_page(__name__, path="/admin", title="Admin", name="Admin")

# Task trigger button
refresh_button = dbc.Button(
    "Task",
    id="task-button",
    color="primary",
    className="px-4",
)

# Excel download button (served via custom Flask route)
download_button = html.A(
    "Download Excel",
    href="/download/0.DataLoader.xlsm",
    download="0.DataLoader.xlsm",
    target="_blank",
    className="btn btn-success",
    style={"width": "fit-content"},
)

# Progress loader
progress_bar = dcc.Loading(
    id="loading-task",
    type="default",
    children=html.Div(id="task-status"),
)

# Page layout
layout = dbc.Container(
    fluid=True,
    className="p-1",
    style={"backgroundColor": "#000000"},
    children=[
        html.Div(
            children=[
                excel_uploader.layout,
                refresh_button,
                download_button,  # ← Added download button here
                progress_bar,
            ],
            style={
                "display": "flex",
                "flexDirection": "column",
                "gap": "10px",
            },
        )
    ],
)

# Task execution callback
@callback(
    Output("task-status", "children"),
    Input("task-button", "n_clicks"),
    running=[(Output("task-button", "disabled"), True, False)],
    prevent_initial_call=True,
)
def handle_task(n_clicks):
    import ix
    ix.task.run()
    return "Task completed!"
