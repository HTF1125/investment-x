import dash_bootstrap_components as dbc
from dash import html

# Full-Screen Modal for Summary with Improved Styling
summary_modal = dbc.Modal(
    [
        dbc.ModalHeader(
            [
                dbc.ModalTitle("Summary"),
                dbc.Button(
                    "Read",
                    id="read-summary",
                    color="info",
                    className="me-2",
                    n_clicks=0,
                ),
                dbc.Button(
                    "Stop",
                    id="stop-summary",
                    color="warning",
                    className="me-2",
                    n_clicks=0,
                ),
                dbc.Button("Close", id="close-modal", color="secondary", n_clicks=0),
            ],
            style={"backgroundColor": "black", "color": "white"},
        ),
        dbc.ModalBody(
            id="modal-body-content",
            style={
                "backgroundColor": "black",
                "color": "white",
                "whiteSpace": "pre-wrap",
                "overflowY": "auto",
                "fontSize": "1.2rem",
                "maxHeight": "70vh",  # Prevents overflow
            },
        ),
        dbc.ModalFooter(
            [],
            style={"backgroundColor": "black", "color": "white"},
        ),
    ],
    id="insight-modal",
    is_open=False,
    centered=True,
    backdrop=True,
    style={
        "height": "100vh",
        "width": "100vw",
        "maxWidth": "100vw",
    },
)
