from dash import dcc, html, callback, Output, Input, State
import dash_bootstrap_components as dbc
import pandas as pd
import io, base64
from ix.misc.email import EmailSender
from ix.misc.settings import Settings
from ix.misc.terminal import get_logger

logger = get_logger(__name__)


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


@callback(
    Output("output-message", "children"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
)
def update_output(contents, filename):
    if contents is not None:
        try:
            _, content_string = contents.split(",")
            decoded = base64.b64decode(content_string)
            in_file = io.BytesIO(decoded)
            data = pd.read_excel(in_file, sheet_name="Data")
            upload_bbg_data(data=data)
            # # Write to a new in-memory Excel file
            # output_buffer = io.BytesIO()
            # with pd.ExcelWriter(output_buffer, engine="xlsxwriter") as writer:
            #     data.to_excel(writer, sheet_name="DataV", index=False)
            # # Finalize writing
            # output_buffer.seek(0)
            email_sender = EmailSender(
                to=", ".join(Settings.email_recipients),
                subject="[IX] Daily Data Share",
                content="Please find the attached Excel file with the latest data.",
            )
            email_sender.attach(in_file, filename=filename)
            email_sender.send()
            logger.info(
                f"Email sent successfully to {', '.join(Settings.email_recipients)}"
            )
            return html.Div(
                [
                    html.P(f"File '{filename}' uploaded successfully and emailed!"),
                ]
            )
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return html.Div(f"Error processing file: {str(e)}")
    return ""


from ix.db.models import Metadata


def upload_bbg_data(data: pd.DataFrame) -> bool:
    for ticker_field in data.columns:
        ticker, field = str(ticker_field).split(":", maxsplit=2)
        metadata = Metadata.find_one({"bbg_ticker": ticker}).run()
        if metadata:
            ts = data[ticker_field].dropna()
            if ts.empty:
                continue
            metadata.ts(field=field).data = ts
    return True
