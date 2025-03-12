from dash import dcc, html, callback, Output, Input, State, set_props
import dash_bootstrap_components as dbc
import pandas as pd
import io, base64
import diskcache
from ix.db import Metadata, TimeSeries, EconomicCalendar
from ix.misc.email import EmailSender
from ix.misc.settings import Settings
from ix.misc.terminal import get_logger
from dash.long_callback import DiskcacheManager
from ix.db.client import get_performances

logger = get_logger(__name__)

# Initialize cache for background callbacks
cache = diskcache.Cache("./cache")
manager = DiskcacheManager(cache)

# -------------------------------- Layout ---------------------------------------
layout = dbc.Container(
    fluid=True,
    style={"backgroundColor": "#121212", "color": "#f8f9fa", "padding": "20px"},
    children=[
        dbc.Card(
            className="shadow rounded-3 w-100",
            style={
                "backgroundColor": "#1e1e1e",
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
                    style={"backgroundColor": "#1e1e1e", "color": "#f8f9fa"},
                    children=[
                        dcc.Upload(
                            id="upload_file",
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
                                "backgroundColor": "#282828",
                                "color": "#f8f9fa",
                            },
                            multiple=False,
                        ),
                        dcc.Loading(
                            id="loading_upload_file",
                            type="default",
                            children=html.Div(
                                id="output_message_upload_file",
                                style={"marginTop": "10px"},
                            ),
                        ),
                        html.Hr(),
                        dbc.Button(
                            "Send Email",
                            id="send_email_button",
                            color="primary",
                            className="mt-2",
                        ),
                        dcc.Loading(
                            id="loading_send_email",
                            type="default",
                            children=html.Div(
                                id="output_email_message", style={"marginTop": "10px"}
                            ),
                        ),
                    ],
                ),
            ],
        ),
    ],
)


@callback(
    Output("output_message_upload_file", "children"),
    Input("upload_file", "contents"),
    State("upload_file", "filename"),
    background=True,
    manager=manager,
    prevent_initial_call=True,
    running=[
        (
            Output("output_message_upload_file", "children"),
            "Uploading and processing...",
            "",
        )
    ],
)
def process_uploaded_file(contents, filename):
    if not contents:
        return "No file uploaded."
    try:
        _, content_string = contents.split(",", 1)
        decoded = base64.b64decode(content_string)
        in_file = io.BytesIO(decoded)
        data = pd.read_excel(
            in_file, sheet_name="Data", parse_dates=True, index_col=[0]
        ).dropna(how="all")
    except Exception as e:
        logger.error(f"Error processing Excel file: {e}", exc_info=True)
        return html.Div("Error: Could not read 'Data' sheet.")

    try:
        upload_bbg_data(data)
        logger.info("File processed successfully")
        return html.Div(f"File '{filename}' uploaded and processed successfully")
    except Exception as e:
        logger.error(f"Upload Error: {e}", exc_info=True)
        return html.Div(f"Error uploading data: {str(e)}")


def upload_bbg_data(data: pd.DataFrame):
    """Uploads data to Bloomberg."""
    for ticker_field in data.columns:
        if ":" not in ticker_field:
            logger.warning(f"Invalid format: {ticker_field}")
            continue
        ticker, field = map(str.strip, ticker_field.split(":", maxsplit=1))
        metadata = Metadata.find_one({"bbg_ticker": ticker}).run()
        if not metadata:
            metadata = Metadata(code=ticker, name="...", bbg_ticker=ticker).create()
        ts = data[ticker_field].dropna()
        if not ts.empty:
            metadata.ts(field=field).data = ts
    return True


@callback(
    Output("output_email_message", "children"),
    Input("send_email_button", "n_clicks"),
    background=True,
    manager=manager,
    prevent_initial_call=True,
    running=[(Output("send_email_button", "disabled"), True, False)],
)
def send_email_callback(n_clicks):
    if not n_clicks:
        return ""

    try:
        # Update email content to refer to an Excel file if desired.
        email_sender = EmailSender(
            to=", ".join(Settings.email_recipients),
            subject="[IX] Daily Data Share",
            content="Please find the attached Excel file with the latest data.",
        )

        datas = []

        for ts in TimeSeries.find(
            {
                "field": {
                    "$nin": [
                        "PX_OPEN",
                        "PX_HIGH",
                        "PX_LOW",
                        "PX_VOLUME",
                        "PX_CLOSE",
                        "PX_SPLITS",
                        "PX_DVDNS",
                        "CAPTIAL_GAINS",
                    ]
                }
            }
        ).run():
            data = ts.data
            if data.empty:
                continue
            data.name = f"{ts.code}:{ts.field}"
            datas.append(data.loc["2024":])
        datas = pd.concat(datas, axis=1)
        metdatas = Metadata.to_dataframe()
        performances = get_performances()
        releases = EconomicCalendar.get_dataframe()

        # Create an in-memory Excel file with multiple sheets.
        file = io.BytesIO()
        with pd.ExcelWriter(file, engine="xlsxwriter") as writer:
            datas.to_excel(writer, sheet_name="Data")
            metdatas.to_excel(writer, sheet_name="Metadata")
            performances.to_excel(writer, sheet_name="Performance")
            releases.to_excel(writer, sheet_name="Economic Calendar")

        file.seek(0)

        # Attach the Excel file with the desired filename.
        email_sender.attach(file, filename="Database.xlsx")
        email_sender.send()
        return html.Div("Data email sent successfully!")
    except Exception as e:
        logger.error(f"Email sending error: {e}", exc_info=True)
        return html.Div(f"Error sending email: {str(e)}")
