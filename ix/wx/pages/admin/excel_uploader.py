from dash import dcc, html, callback, Output, Input, State
import dash_bootstrap_components as dbc
import pandas as pd
import io, base64
from ix.db import Metadata, TimeSeries
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
                        # Wrap the upload message in a loading container
                        dcc.Loading(
                            id="loading-upload",
                            type="default",
                            # Set style to ensure the spinner appears within the same section
                            style={"width": "100%"},
                            children=html.Div(
                                id="output-message",
                                style={"marginTop": "10px"},
                            ),
                        ),
                        html.Hr(),
                        dbc.Button(
                            "Send Email",
                            id="send-email-btn",
                            color="primary",
                            className="mt-2",
                        ),
                        # Wrap the email message in a loading container
                        dcc.Loading(
                            id="loading-email",
                            type="default",
                            style={"width": "100%"},
                            children=html.Div(
                                id="output-email-message",
                                style={"marginTop": "10px"},
                            ),
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
    """
    Process the uploaded Excel file by reading its 'Data' sheet,
    uploading data to Bloomberg, and adding a new sheet 'DataV'
    to the original workbook. The modified workbook is then emailed.
    """
    if not contents:
        return ""

    try:
        # Decode the base64 content and create an in-memory file
        header, content_string = contents.split(",", 1)
        decoded = base64.b64decode(content_string)
        in_file = io.BytesIO(decoded)

        # Read the 'Data' sheet using pandas
        data = pd.read_excel(
            in_file, sheet_name="Data", parse_dates=True, index_col=[0]
        ).dropna(how="all")

        # Upload cleaned data
        upload_bbg_data(data)

        logger.info("Files uploaded Successfully")
        return html.Div([html.P(f"File '{filename}' uploaded successfully")])

    except Exception as e:
        logger.error(f"Failed to process and send email: {str(e)}", exc_info=True)
        return html.Div(f"Error processing file: {str(e)}")


@callback(
    Output("output-email-message", "children"),
    Input("send-email-btn", "n_clicks"),
)
def send_email_callback(n_clicks):
    """
    Retrieve the latest time series data, prepare a CSV file, and send an email.
    This is triggered when the "Send Email" button is clicked.
    """
    if not n_clicks:
        return ""

    try:
        datas = []
        for metadata in Metadata.find().run():
            for ts in TimeSeries.find_many({"meta_id": str(metadata.id)}).run():
                if ts.field in [
                    "PX_OPEN",
                    "PX_HIGH",
                    "PX_LOW",
                    "PX_VOLUME",
                    "PX_CLOSE",
                ]:
                    continue
                ts_data = ts.data
                ts_data.name = f"{metadata.code}:{ts.field}"
                datas.append(ts_data.loc["2023":])
                logger.debug(f"{metadata.code} - {ts.field} added.")
        if not datas:
            return html.Div("No data available to send.")
        datas = pd.concat(datas, axis=1)

        email_sender = EmailSender(
            to=", ".join(Settings.email_recipients),
            subject="[IX] Daily Data Share",
            content="Please find the attached CSV file with the latest data.",
        )

        file = io.BytesIO()
        datas.to_csv(file)
        file.seek(0)
        email_sender.attach(file, filename="datas.csv")
        email_sender.send()

        logger.info(
            f"Email sent successfully to {', '.join(Settings.email_recipients)}"
        )
        return html.Div("Data email sent successfully!")
    except Exception as e:
        logger.error(f"Failed to send data email: {str(e)}", exc_info=True)
        return html.Div(f"Error sending email: {str(e)}")


def upload_bbg_data(data: pd.DataFrame) -> bool:
    for ticker_field in data.columns:
        ticker, field = str(ticker_field).split(":", maxsplit=2)
        metadata = Metadata.find_one({"bbg_ticker": ticker}).run()
        if not metadata:
            metadata = Metadata(code=ticker, name="...", bbg_ticker=ticker).create()

        try:
            ts = data[ticker_field].dropna()
            if ts.empty:
                continue
            metadata.ts(field=field).data = ts
        except Exception as e:
            logger.exception(e)

    return True
