from ix.wx.utils import get_user_from_token
from dash import html, dcc, callback, Input, Output, State, no_update
import dash_bootstrap_components as dbc
from ix.db.models import MarketCommentary


@callback(
    [Output("saved-content", "children"), Output("market-commentary", "value")],
    [Input("save-button", "n_clicks")],
    [State("market-commentary", "value"), State("token-store", "data")],
)
def update_market_commentary(n_clicks, content, token):
    """
    Loads the current market commentary and, if an admin user clicks Save,
    updates the commentary in the database. Non-admin users are allowed to
    view the commentary but cannot update it.
    """
    user = get_user_from_token(token)
    is_admin = user.is_admin if user else False

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

    if not is_admin:
        return "You are not authorized to update commentary.", no_update

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


layout = dbc.Container(
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
                        dcc.Textarea(
                            id="market-commentary",
                            style={
                                "width": "100%",
                                "height": "200px",
                                "backgroundColor": "#343a40",
                                "color": "#ffffff",
                            },
                            placeholder="Write your commentary in Markdown format...",
                        ),
                        html.Div(
                            id="saved-content",
                            className="mt-2 text-success fw-bold",
                            style={"padding": "0.5rem"},
                        ),
                        html.Hr(),
                        html.H4("Preview"),
                        dcc.Markdown(
                            id="market-commentary-preview",
                            style={
                                "backgroundColor": "#454d55",
                                "color": "#ffffff",
                                "padding": "10px",
                                "borderRadius": "5px",
                            },
                        ),
                    ],
                ),
            ],
        ),
    ],
)


@callback(
    Output("market-commentary-preview", "children"),
    Input("market-commentary", "value"),
)
def update_preview(content):
    return content if content else ""
