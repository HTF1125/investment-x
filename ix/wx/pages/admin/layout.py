from dash import html, register_page, callback, Input, Output
import dash_bootstrap_components as dbc
import time
from ix.wx.pages.admin import excel_uploader

register_page(__name__, path="/admin", title="Admin", name="Admin")

refresh_button = dbc.Button(
    "Task",
    id="task-button",
    color="primary",
    className="px-4",
)


from dash import dcc

# Add a progress indicator
progress_bar = dcc.Loading(
    id="loading-task",
    type="default",
    children=html.Div(id="task-status"),
)

# Update layout to include the progress bar
layout = dbc.Container(
    fluid=True,
    className="p-1",
    style={"backgroundColor": "#000000"},
    children=[
        html.Div(
            children=[
                excel_uploader.layout,
                refresh_button,
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


@callback(
    Output("task-status", "children"),
    Input("task-button", "n_clicks"),
    running=[(Output("task-button", "disabled"), True, False)],
    prevent_initial_call=True,
)
def handle_task(n_clicks):
    # Indicate that the task is running

    import ix

    ix.task.run()

    # Indicate that the task is completed
    return "Task completed!"
