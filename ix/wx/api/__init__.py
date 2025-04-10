import pandas as pd
from flask import jsonify
from ix.wx.app import server
from ix.misc import get_logger
from ix.db import Metadata, get_ticker

logger = get_logger(__name__)


from flask import request
import os
from datetime import datetime


@server.route("/api/upload_data", methods=["POST"])
def upload_data():
    try:
        data = request.get_json(force=True)
        if not isinstance(data, list):
            return (
                jsonify({"error": "Invalid payload: expected a list of records"}),
                400,
            )

        df = pd.DataFrame(data)

        required_columns = {"date", "ticker", "field", "value"}
        if not required_columns.issubset(df.columns):
            return (
                jsonify(
                    {
                        "error": f"Missing required fields: {required_columns - set(df.columns)}"
                    }
                ),
                400,
            )

        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["value"])

        df["column"] = df["ticker"] + ":" + df["field"]
        data = df.pivot(index="date", columns="column", values="value").sort_index()
        data = data.dropna(how="all", axis=1).dropna(how="all", axis=0)

        logger.info("Received %d records from VBA upload", len(df))
        logger.debug("Preview of received data:\n%s", df.head())

        # === Save file in docs/ directory with timestamp ===
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_dir = "docs"
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, f"Data_{timestamp}.csv")
        data.to_csv(file_path, index=True)

        return (
            jsonify(
                {
                    "message": f"Successfully received {len(df)} records.",
                    "saved_file": file_path,
                }
            ),
            200,
        )

    except Exception as e:
        logger.exception("Failed to process VBA upload")
        return jsonify({"error": str(e)}), 500


@server.route("/api/fields", methods=["GET"])
def get_fields():
    """
    API endpoint to return available fields.
    Optional query parameter:
        - source: filter fields by data source (e.g., 'Bloomberg', 'Reuters')
    Example:
        /api/fields
        /api/fields?source=Bloomberg
    """
    from ix.db import Ticker  # Replace with your actual Field model

    try:
        source = request.args.get("source", default=None)
        ticker_field = []
        for ticker in Ticker.find().run():
            for field in ticker.fields:
                if source is not None:
                    if field.source != source:
                        continue
                ticker_field.append(
                    {
                        "Ticker": ticker.code,
                        "Field": field.field,
                        "Source": field.source,
                        "Source.Ticker": field.source_ticker,
                        "Source.Field": field.source_field,
                    }
                )
        data = (
            pd.DataFrame(ticker_field)
            .drop_duplicates()
            .reset_index(drop=True)
            .to_dict("records")
        )

        return jsonify(data), 200

    except Exception as e:
        logger.exception("Failed to fetch fields")
        return jsonify({"error": str(e)}), 500


@server.route("/api/metadata")
def get_metadata():
    """
    API endpoint to retrieve metadata.
    """
    try:
        metadatas = pd.DataFrame(
            [metadata.model_dump() for metadata in Metadata.find().run()]
        )
    except Exception as e:
        logger.error("Error fetching metadata: %s", e)
        return jsonify({"error": "Failed to fetch metadata"}), 500
    return jsonify(metadatas.to_dict("records"))


@server.route("/api/performance")
def get_performance():
    """
    API endpoint to retrieve metadata.
    """
    import numpy as np
    from ix.db.client import get_performances

    performances = get_performances()
    performances = performances.replace(np.nan, None)
    return jsonify(performances.to_dict("records"))


@server.route("/api/timeseries")
def get_timeseries():
    """
    API endpoint to retrieve metadata.
    """
    import numpy as np
    import pandas as pd
    from ix.db import TimeSeries

    import os
    import pandas as pd
    from ix.db import get_ticker

    DOCS_DIR = "docs"

    def upload_data_from_saved(data: pd.DataFrame) -> bool:
        try:
            for ticker_field in data.columns:
                if ":" not in ticker_field:
                    print(f"Invalid format: {ticker_field}")
                    continue
                ticker_code, field_code = map(
                    str.strip, ticker_field.split(":", maxsplit=1)
                )

                ticker = get_ticker(code=ticker_code, create=True)
                timeseries = ticker.get_timeseries(field=field_code, create=True)
                timeseries.data = data[ticker_field].dropna()
            return True
        except Exception as e:
            print(f"❌ Upload failed due to error: {e}")
            return False

    def process_all_csv_files(directory: str) -> None:
        # List CSV files with full paths and sort by modification time (oldest first)
        csv_files = [
            os.path.join(directory, f)
            for f in os.listdir(directory)
            if f.lower().endswith(".csv")
        ]
        csv_files.sort(key=os.path.getmtime)

        for file_path in csv_files:
            filename = os.path.basename(file_path)
            try:
                print(f"📄 Processing {file_path} ...")
                df = pd.read_csv(file_path, index_col=0, parse_dates=[0])
                success = upload_data_from_saved(df)
                if success:
                    os.remove(file_path)
                    print(f"✅ Successfully processed and deleted {filename}")
                else:
                    print(f"⚠️ Upload failed — file retained: {filename}")
            except Exception as e:
                print(f"❌ Failed to process {filename}: {e}")

    process_all_csv_files("docs")
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
        datas.append(data)

    datas = pd.concat(datas, axis=1).replace(np.nan, None).sort_index()
    datas.index = pd.to_datetime(datas.index)
    datas = datas.resample("D").last().loc["2024":]
    datas.index.name = "Date"
    datas.index = datas.index.strftime("%Y-%m-%d")
    datas = datas.reset_index()
    return jsonify(datas.to_dict("records"))


@server.route("/api/economic_calendar")
def get_economic_calendar():
    """
    API endpoint to retrieve metadata.
    """
    from ix.db import EconomicCalendar
    from ix.task import update_economic_calendar

    update_economic_calendar()
    return jsonify(EconomicCalendar.get_dataframe().to_dict("records"))


@server.route("/api/insights")
def get_insights():
    """
    API endpoint to retrieve metadata.
    """
    from ix.db import get_insights

    insights = get_insights(limit=100)

    return jsonify([insight.model_dump() for insight in insights])


from flask import Response
import os


@server.route("/download/0.DataLoader.xlsm")
def download_file():
    file_path = os.path.join("docs", "0.DataLoader.xlsm")

    if not os.path.exists(file_path):
        return Response("File not found", status=404)

    with open(file_path, "rb") as f:
        data = f.read()

    return Response(
        data,
        mimetype="application/vnd.ms-excel.sheet.macroEnabled.12",
        headers={"Content-Disposition": "attachment; filename=0.DataLoader.xlsm"},
    )
