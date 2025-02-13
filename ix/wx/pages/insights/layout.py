import dash_bootstrap_components as dbc
from dash import html, dcc
import dash
from ix.wx.pages.insights.callbacks import *

# Register Page
dash.register_page(
    __name__,
    path="/insights",
    title="Insights",
    name="Insights"
)


layout = dbc.Container(
    id="insights-main-container",
    fluid=True,
    className="py-4",
    style={"backgroundColor": "black", "color": "white"},
    children=[
        # Page Header
        dbc.Row(
            dbc.Col(
                html.H1("Insights", style={"color": "white", "textAlign": "center"}),
                width=12,
            )
        ),
        # File Upload
        dbc.Row(
            dbc.Col(
                [
                    dcc.Upload(
                        id="upload-pdf",
                        children=html.Div(
                            [
                                "Drag and Drop or ",
                                html.A("Select PDF Files", style={"color": "white"}),
                            ]
                        ),
                        style={
                            "width": "100%",
                            "height": "60px",
                            "lineHeight": "60px",
                            "borderWidth": "1px",
                            "borderStyle": "dashed",
                            "borderRadius": "5px",
                            "textAlign": "center",
                            "margin": "10px",
                            "backgroundColor": "black",
                            "borderColor": "white",
                            "color": "white",
                        },
                        multiple=False,
                    ),
                    html.Div(id="output-pdf-upload"),
                ],
                width=10,
                style={"margin": "auto"},
                className="mb-4",
            )
        ),
        # Search Bar
        dbc.Row(
            dbc.Col(
                dbc.InputGroup(
                    [
                        dbc.Input(
                            id="insights-search",
                            placeholder="Search insights...",
                            type="text",
                            style={
                                "backgroundColor": "black",
                                "color": "white",
                                "border": "1px solid white",
                            },
                        ),
                        dbc.Button("Search", id="search-button", color="primary"),
                    ],
                    className="mb-4",
                ),
                width=8,
                style={"margin": "auto"},
            )
        ),
        # Insight Cards Container
        html.Div(id="insights-container-wrapper", children=[]),
        # Load More Button
        dbc.Row(
            dbc.Col(
                dbc.Button(
                    "Load More",
                    id="load-more-insights",
                    color="secondary",
                    className="mb-4 d-block mx-auto",
                ),
                width=4,
                style={"margin": "auto"},
            )
        ),
        # Hidden Stores for data and dummy outputs for speech synthesis
        dcc.Store(id="insights-data", data=[]),
        dcc.Store(id="total-insights-loaded", data=0),
        dcc.Store(id="search-query", data=""),
        dcc.Store(id="dummy-read", data=""),
        dcc.Store(id="dummy-stop", data=""),
        # Full-Screen Modal for Summary
        dbc.Modal(
            [
                dbc.ModalHeader(
                    dbc.ModalTitle("Summary"),
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
                    },
                ),
                dbc.ModalFooter(
                    [
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
                        dbc.Button(
                            "Close", id="close-modal", color="secondary", n_clicks=0
                        ),
                    ],
                    style={"backgroundColor": "black", "color": "white"},
                ),
            ],
            id="insight-modal",
            is_open=False,
            centered=True,
            backdrop=True,
            style={"height": "80%"},
        ),
        # JavaScript for speech synthesis
        html.Script(
            """
            document.addEventListener("DOMContentLoaded", function() {
                var readBtn = document.getElementById("read-summary");
                var stopBtn = document.getElementById("stop-summary");
                if(readBtn) {
                    readBtn.addEventListener("click", function() {
                        var modalBody = document.getElementById("modal-body-content");
                        var summary = modalBody ? modalBody.innerText : "";
                        if (summary && window.speechSynthesis) {
                            window.speechSynthesis.cancel();
                            var utterance = new SpeechSynthesisUtterance(summary);
                            window.speechSynthesis.speak(utterance);
                        }
                    });
                }
                if(stopBtn) {
                    stopBtn.addEventListener("click", function() {
                        if (window.speechSynthesis) {
                            window.speechSynthesis.cancel();
                        }
                    });
                }
            });
            """
        ),
    ],
)
