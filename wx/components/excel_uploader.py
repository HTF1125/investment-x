from dash import dcc, html, callback, Output, Input, State
import dash_bootstrap_components as dbc
import pandas as pd
import io, base64

# Layout wrapped in a Card for a polished look.
layout = dbc.Container(
    fluid=True,
    style={
        "backgroundColor": "transparent",
        "color": "#f8f9fa",
        "padding": "10px",
    },
    children=[
        dbc.Card(
            className="shadow rounded-3 w-100",
            style={
                "backgroundColor": "transparent",
                "border": "1px solid #f8f9fa",
                "boxShadow": "2px 2px 5px rgba(0,0,0,0.5)",
                "marginBottom": "1rem",
            },
            children=[
                dbc.CardHeader(
                    html.H3("Excel File Uploader", className="mb-0"),
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
                        dcc.Upload(
                            id="upload-data",
                            children=html.Div(
                                ["Drag and Drop or ", html.A("Select Files")]
                            ),
                            style={
                                "width": "100%",
                                "height": "60px",
                                "lineHeight": "60px",
                                "borderWidth": "1px",
                                "borderStyle": "dashed",
                                "borderRadius": "5px",
                                "textAlign": "center",
                                "margin": "10px 0",
                                "backgroundColor": "transparent",
                                "color": "#f8f9fa",
                            },
                            multiple=False,
                        ),
                        html.Div(
                            id="output-message",
                            style={"marginTop": "10px"},
                        ),
                    ],
                ),
            ],
        ),
    ],
)


def parse_contents(contents):
    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)

    # Save the decoded content as uploaded.xlsx
    with open("uploaded.xlsx", "wb") as file:
        file.write(decoded)
    df = pd.read_excel(io.BytesIO(decoded))
    return df


@callback(
    Output("output-message", "children"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
)
def update_output(contents, filename):
    if contents is not None:
        try:
            df = parse_contents(contents)
            return html.Div(
                [
                    html.P(
                        f"File '{filename}' uploaded successfully and saved as 'uploaded.xlsx'!"
                    ),
                    html.P(f"{df.shape[0]} rows loaded."),
                ]
            )
        except Exception as e:
            return html.Div(f"Error processing file: {str(e)}")
    return ""
