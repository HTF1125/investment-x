import dash
from dash import (
    html,
    dcc,
    callback,
    Input,
    Output,
    State,
    no_update,
    clientside_callback,
)
import dash_bootstrap_components as dbc
import dash_summernote
from ix.db.models import MarketCommentary


@callback(
    [Output("saved-content", "children"), Output("market-commentary", "value")],
    [Input("save-button", "n_clicks")],
    [State("market-commentary", "value")],
)
def update_market_commentary(n_clicks, content):
    if n_clicks is None:
        try:
            commentary_doc = MarketCommentary.find_one(
                {}, sort=[("asofdate", -1)]
            ).run()
            if commentary_doc:
                return "", commentary_doc.content
            else:
                return "", "No market commentary available."
        except Exception as e:
            return f"Error loading market commentary: {str(e)}", no_update
    else:
        if content:
            try:
                new_commentary = MarketCommentary(content=content)
                MarketCommentary.find_many(
                    {"asofdate": new_commentary.asofdate}
                ).delete().run()
                new_commentary.create()
                return "Content saved successfully!", content
            except Exception as e:
                return f"Error saving commentary: {str(e)}", no_update
        else:
            return "No content to save.", no_update


# Inject custom CSS for Summernote dark mode.
clientside_callback(
    """
    function() {
        const style = document.createElement('style');
        style.type = 'text/css';
        style.innerHTML = `
            .note-editor.note-frame {
                background-color: #343a40 !important;
                border-color: #454d55 !important;
                color: #ffffff !important;
            }
            .note-editor.note-frame .note-toolbar {
                background-color: #454d55 !important;
                border-color: #454d55 !important;
            }
            .note-editor.note-frame .note-statusbar {
                background-color: #454d55 !important;
                border-color: #454d55 !important;
            }
            .note-editor.note-frame .note-editing-area .note-editable {
                background-color: #343a40 !important;
                color: #ffffff !important;
            }
            .note-editor.note-frame .note-btn {
                background-color: #454d55 !important;
                border-color: #454d55 !important;
                color: #ffffff !important;
            }
            .note-editor.note-frame .note-btn:hover {
                background-color: #5a6268 !important;
                border-color: #5a6268 !important;
            }
        `;
        document.head.appendChild(style);
        return true;
    }
    """,
    Output("summernote-dark-mode", "children"),
    Input("summernote-dark-mode", "id"),
)


def get_layout():
    return dbc.Container(
        fluid=True,
        className="py-3",
        style={
            "backgroundColor": "transparent",
            "color": "#f8f9fa",
            "padding": "20px",
        },
        children=[
            dbc.Card(
                className="shadow rounded-3 w-100",
                style={
                    "backgroundColor": "transparent",
                    "color": "#f8f9fa",
                    "border": "1px solid #f8f9fa",
                    "boxShadow": "2px 2px 5px rgba(0,0,0,0.5)",
                    "marginBottom": "1rem",
                },
                children=[
                    dbc.CardHeader(
                        dbc.Row(
                            [
                                dbc.Col(
                                    html.H3("Commentary", className="mb-0"),
                                    width=True,
                                ),
                                dbc.Col(
                                    dbc.Button(
                                        "Save",
                                        id="save-button",
                                        style={
                                            "backgroundColor": "transparent",
                                            "border": "1px solid #f8f9fa",
                                            "color": "#f8f9fa",
                                            "padding": "0.5rem 1rem",
                                            "borderRadius": "4px",
                                            "cursor": "pointer",
                                        },
                                    ),
                                    width="auto",
                                    className="text-end",
                                ),
                            ],
                            align="center",
                        ),
                        style={
                            "backgroundColor": "transparent",
                            "color": "#f8f9fa",
                            "borderBottom": "2px solid #f8f9fa",
                            "padding": "1rem",
                        },
                    ),
                    dbc.CardBody(
                        style={
                            "backgroundColor": "transparent",
                            "color": "#f8f9fa",
                            "padding": "1.5rem",
                        },
                        children=[
                            # Wrap the DashSummernote component in a Div if additional styling is needed.
                            html.Div(
                                dash_summernote.DashSummernote(
                                    id="market-commentary",
                                    height=600,
                                    toolbar=[
                                        [
                                            "style",
                                            ["bold", "italic", "underline", "clear"],
                                        ],
                                        ["font", ["arial"]],
                                        ["para", ["ul", "ol", "paragraph"]],
                                        ["table", ["table"]],
                                        ["insert", ["link", "picture", "video", "hr"]],
                                    ],
                                    value="Write your commentary here...",
                                )
                            ),
                            html.Div(
                                id="summernote-dark-mode", style={"display": "none"}
                            ),
                            html.Div(
                                id="saved-content",
                                className="mt-2 text-success fw-bold",
                                style={"padding": "0.5rem"},
                            ),
                        ],
                    ),
                ],
            ),
        ],
    )
