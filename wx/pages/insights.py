import json
import base64
from datetime import datetime

import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, callback, Input, Output, State, ALL
from dash.exceptions import PreventUpdate

# External modules—ensure these are installed/in your PYTHONPATH.
from ix.db.client import get_insights
from ix.db.conn import Insight
from ix.db.boto import Boto
from ix.misc import PDFSummarizer, Settings


# ----------------------------
# Helper Function
# ----------------------------
def create_insight_card(insight):
    published_date = (
        insight.get("published_date", "")[:10]
        if isinstance(insight.get("published_date", ""), str)
        else ""
    )
    summary = insight.get("summary", "No summary available.")
    # Left side content (clickable to open modal)
    left_content = html.Div(
        [
            html.Small(
                f"Published: {published_date}", style={"color": "white", "opacity": 0.7}
            ),
            html.H4(
                insight.get("name", "No Name"),
                className="mt-1 mb-1",
                style={"color": "white"},
            ),
            html.Small(
                f"Issuer: {insight.get('issuer', 'Unknown')}",
                style={"color": "white", "opacity": 0.7},
            ),
        ],
        id={"type": "insight-card-clickable", "index": insight.get("id")},
        n_clicks=0,
        style={"cursor": "pointer"},
    )
    # Right side: PDF button
    pdf_button = dbc.Button(
        [html.I(className="fas fa-file-pdf me-2"), "View PDF"],
        href=f"https://files.investment-x.app/{insight.get('id')}.pdf",
        target="_blank",
        color="light",
        size="sm",
    )
    card = dbc.Card(
        dbc.CardBody(
            dbc.Row(
                [
                    dbc.Col(left_content, width=10),
                    dbc.Col(
                        pdf_button,
                        width=2,
                        className="d-flex align-items-center justify-content-end",
                    ),
                ],
                align="center",
            )
        ),
        className="mb-4 shadow-sm",
        style={
            "border": "1px solid white",
            "backgroundColor": "black",
            "color": "white",
        },
    )
    return card


# ----------------------------
# Layout Definition
# ----------------------------
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
        # Insight Cards Container (each card in its own row)
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
        # Full-Screen Modal for Summary (takes up entire screen and is centered)
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
            style={
                "height": "80%",
            },
        ),
        # JavaScript to enable speech synthesis via button clicks.
        # This script adds event listeners to the Read and Stop buttons.
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

# ----------------------------
# Callbacks
# ----------------------------


# --- Loading Insights Callback ---
@callback(
    Output("insights-data", "data"),
    Output("total-insights-loaded", "data"),
    Output("search-query", "data"),
    Input("load-more-insights", "n_clicks"),
    Input("search-button", "n_clicks"),
    Input("insights-search", "n_submit"),
    State("insights-data", "data"),
    State("total-insights-loaded", "data"),
    State("search-query", "data"),
    State("insights-search", "value"),
)
def fetch_insights(
    load_clicks,
    search_clicks,
    search_submit,
    current_data,
    total_loaded,
    search_query,
    search_value,
):
    ctx = dash.callback_context
    if not ctx.triggered:
        triggered_id = ""
    else:
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    # For search or initial load, reset the data.
    if triggered_id in ["search-button", "insights-search", ""]:
        search_query = search_value or ""
        skip = 0
    elif triggered_id == "load-more-insights":
        skip = total_loaded or 0
    else:
        skip = 0
    limit = 10
    new_insights = get_insights(search=search_query, skip=skip, limit=limit)
    if not new_insights:
        if triggered_id == "load-more-insights":
            raise PreventUpdate
        new_serialized = []
    else:
        new_serialized = [insight.model_dump_json() for insight in new_insights]
    if triggered_id in ["search-button", "insights-search", ""]:
        updated_data = new_serialized
        new_total = len(new_serialized)
    else:
        updated_data = current_data + new_serialized
        new_total = total_loaded + len(new_insights)
    return updated_data, new_total, search_query


# --- Update Insight Cards Callback ---
@callback(
    Output("insights-container-wrapper", "children"),
    Input("insights-data", "data"),
)
def update_insights_cards(insights_data):
    if not insights_data:
        return dbc.Alert(
            "No insights available.", color="info", className="text-center"
        )
    try:
        cards = [create_insight_card(json.loads(insight)) for insight in insights_data]
        return [dbc.Row(dbc.Col(card, width=12)) for card in cards]
    except Exception as e:
        return dbc.Alert(
            f"Error processing insights: {str(e)}",
            color="danger",
            className="text-center",
        )


# --- PDF Upload Processing Callback ---
@callback(
    Output("output-pdf-upload", "children"),
    Output("upload-pdf", "contents"),
    Input("upload-pdf", "contents"),
    State("upload-pdf", "filename"),
    State("upload-pdf", "last_modified"),
    prevent_initial_call=True,
)
def update_output(content, filename, last_modified):
    if content is None:
        raise PreventUpdate
    try:
        content_type, content_string = content.split(",")
        decoded = base64.b64decode(content_string)
        if not filename.lower().endswith(".pdf"):
            return html.Div("Only PDF files are allowed.", style={"color": "red"}), None
        if not decoded.startswith(b"%PDF-"):
            return html.Div("Invalid PDF file.", style={"color": "red"}), None
        try:
            published_date_str, issuer, name = filename.rsplit("_", 2)
            name = name.rsplit(".", 1)[0]
            published_date = datetime.strptime(published_date_str, "%Y%m%d").date()
        except ValueError:
            return (
                html.Div(
                    "Filename must be in the format 'YYYYMMDD_issuer_name.pdf'",
                    style={"color": "red"},
                ),
                None,
            )
        insight = Insight(
            published_date=published_date, issuer=issuer, name=name
        ).create()
        filename_pdf = f"{insight.id}.pdf"
        Boto().save_pdf(pdf_content=decoded, filename=filename_pdf)
        insight.set(
            {
                "summary": PDFSummarizer(Settings.openai_secret_key).process_insights(
                    Boto().get_pdf(filename=filename_pdf)
                )
            }
        )
        return (
            html.Div(
                [
                    html.H5(
                        f"File '{filename_pdf}' uploaded successfully",
                        style={"color": "green"},
                    ),
                    html.P(f"Published Date: {published_date}"),
                    html.P(f"Issuer: {issuer}"),
                    html.P(f"Name: {name}"),
                    html.P(f"Last modified: {datetime.fromtimestamp(last_modified)}"),
                    html.P(f"Insight ID: {insight.id}"),
                    html.P(f"File size: {len(decoded) / 1024:.2f} KB"),
                ]
            ),
            None,
        )
    except Exception as e:
        return (
            html.Div(
                [
                    html.H5("Error processing file", style={"color": "red"}),
                    html.P(str(e)),
                ]
            ),
            None,
        )


# --- Modal Display Callback ---
@callback(
    Output("insight-modal", "is_open"),
    Output("modal-body-content", "children"),
    Input({"type": "insight-card-clickable", "index": ALL}, "n_clicks"),
    Input("close-modal", "n_clicks"),
    State("insight-modal", "is_open"),
    State("insights-data", "data"),
)
def display_modal(n_clicks_list, close_n, is_open, insights_data):
    ctx = dash.callback_context
    if not ctx.triggered:
        raise PreventUpdate
    triggered = ctx.triggered[0]
    if "close-modal" in triggered["prop_id"]:
        return False, dash.no_update
    if not any(n_clicks_list):
        raise PreventUpdate
    try:
        triggered_id = json.loads(triggered["prop_id"].split(".")[0])
        card_index = triggered_id["index"]
    except Exception:
        return is_open, dash.no_update
    summary_text = "No summary available."
    for insight_json in insights_data:
        insight = json.loads(insight_json)
        if str(insight.get("id")) == str(card_index):
            summary_text = insight.get("summary", "No summary available.")
            break
    return True, summary_text


# ----------------------------
# Register the page (do not create an app here)
# ----------------------------
dash.register_page(__name__, path="/insights", title="Insights", name="Insights")
