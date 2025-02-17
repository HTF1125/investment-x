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
                data = ts.data
                data.name = f"{metadata.code}:{ts.field}"
                datas.append(data.loc["2023":])
        datas = pd.concat(datas, axis=1)

        # Prepare and send the email with the updated Excel file attached
        email_sender = EmailSender(
            to=", ".join(Settings.email_recipients),
            subject="[IX] Daily Data Share",
            content="Please find the attached Excel file with the latest data and added sheet.",
        )

        file = io.BytesIO()
        datas.to_csv(file)
        email_sender.attach(file, filename="datas.csv")
        email_sender.send()

        logger.info(
            f"Email sent successfully to {', '.join(Settings.email_recipients)}"
        )
        return html.Div(
            [html.P(f"File '{filename}' uploaded successfully, updated, and emailed!")]
        )

    except Exception as e:
        logger.error(f"Failed to process and send email: {str(e)}", exc_info=True)
        return html.Div(f"Error processing file: {str(e)}")


from ix.db.models import Metadata


def upload_bbg_data(data: pd.DataFrame) -> bool:
    for ticker_field in data.columns:
        ticker, field = str(ticker_field).split(":", maxsplit=2)
        metadata = Metadata.find_one({"bbg_ticker": ticker}).run()
        if metadata:
            ts = data[ticker_field].dropna()
            if ts.empty:
                continue
            print(ts)
            metadata.ts(field=field).data = ts
    return True
