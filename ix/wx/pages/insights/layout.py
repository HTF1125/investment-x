import dash_bootstrap_components as dbc
from dash import html, dcc, Dash, callback_context
import dash
import dash_player
from ix.wx.pages.insights.callbacks import *
from ix.wx.pages.insights.summary_modal import summary_modal

# Register Page
dash.register_page(__name__, path="/insights", title="Insights", name="Insights")

# Define common style constants.
UPLOAD_STYLE = {
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
}

INPUT_STYLE = {
    "backgroundColor": "black",
    "color": "white",
    "border": "1px solid white",
}

# File Uploader Component
file_uploader = dbc.Row(
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
                style=UPLOAD_STYLE,
                multiple=False,
            ),
            html.Div(id="output-pdf-upload"),
        ],
        width=10,
        style={"margin": "auto"},
        className="mb-4",
    )
)

# Search Bar Component
search_bar = dbc.Row(
    dbc.Col(
        dbc.InputGroup(
            [
                dbc.Input(
                    id="insights-search",
                    placeholder="Search insights...",
                    type="text",
                    style=INPUT_STYLE,
                ),
                dbc.Button("Search", id="search-button", color="primary"),
            ],
            className="mb-4",
        ),
        width=8,
        style={"margin": "auto"},
    )
)

# Load More Button Component
load_more_button = dbc.Row(
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
)

# Layout
layout = dbc.Container(
    id="insights-main-container",
    fluid=True,
    className="py-4",
    style={"backgroundColor": "black", "color": "white"},
    children=[
        dbc.Row(
            dbc.Col(
                html.H1("Insights", style={"color": "white", "textAlign": "center"}),
                width=12,
            )
        ),
        file_uploader,
        search_bar,
        html.Div(id="insights-container-wrapper", children=[]),
        load_more_button,
        dcc.Store(id="insights-data", data=[]),
        dcc.Store(id="total-insights-loaded", data=0),
        dcc.Store(id="search-query", data=""),
        summary_modal,
        html.Script(
            """
            document.addEventListener("DOMContentLoaded", function() {
                setTimeout(function() {
                    var readBtn = document.getElementById("read-summary");
                    var stopBtn = document.getElementById("stop-summary");

                    if(readBtn && stopBtn) {
                        readBtn.addEventListener("click", function() {
                            var modalBody = document.getElementById("modal-body-content");
                            var summary = modalBody ? modalBody.innerText.trim() : "";

                            if (summary.length > 0 && window.speechSynthesis) {
                                window.speechSynthesis.cancel();
                                var utterance = new SpeechSynthesisUtterance(summary);
                                utterance.rate = 1.0;
                                utterance.pitch = 1.0;
                                utterance.volume = 1.0;
                                window.speechSynthesis.speak(utterance);
                            }
                        });

                        stopBtn.addEventListener("click", function() {
                            if (window.speechSynthesis) {
                                window.speechSynthesis.cancel();
                            }
                        });
                    }
                }, 1000);
            });
            """
        ),
    ],
)
