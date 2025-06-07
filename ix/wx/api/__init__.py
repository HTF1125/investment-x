import pandas as pd
from flask import jsonify
from ix.wx.app import server
from ix.misc import get_logger

logger = get_logger(__name__)


from flask import request
import os
from datetime import datetime
from ix import db


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
        for ticker_field in data.columns:
            if ":" not in ticker_field:
                print(f"Invalid format: {ticker_field}")
                continue
            ticker_code, field_code = map(
                str.strip, ticker_field.split(":", maxsplit=1)
            )
            ticker = db.get_ticker(code=ticker_code, create=True)
            timeseries = ticker.get_historical(field=field_code, create=True)
            timeseries.data = data[ticker_field].dropna()

        return (
            jsonify(
                {
                    "message": f"Successfully received {len(df)} records.",
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


@server.route("/api/tickers")
def get_tickers():
    """
    API endpoint to retrieve metadata.
    """
    from ix.db import Ticker

    return jsonify([ticker.model_dump() for ticker in Ticker.find().run()])


@server.route("/api/tickers", methods=["POST"])
def upload_tickers():
    """
    API endpoint to upload ticker metadata.

    Expects JSON array where each row contains:
    - id (primary key)
    - code (ticker code)
    - name, frequency, asset_class, category (optional metadata)
    - fields: a string of 'field|source|source_ticker|source_field' joined by '/'
    """
    import pandas as pd
    from flask import request, jsonify
    from ix.db import SourceF
    from ix import db

    try:
        # Parse JSON body into DataFrame
        data = pd.DataFrame(request.get_json(force=True))
        if "id" not in data.columns or "code" not in data.columns:
            return jsonify({"error": "Missing required fields: 'id' or 'code'"}), 400

        data = data.set_index("id", drop=True)

        for ticker_id, row in data.iterrows():
            ticker = db.get_ticker(code=row["code"], create=True)

            ticker.name = row.get("name", "")
            ticker.frequency = row.get("frequency", "")
            ticker.asset_class = row.get("asset_class", "")
            ticker.category = row.get("category", "")
            ticker.fields = []

            fields_str = row.get("fields", "")
            if fields_str:
                try:
                    for entry in fields_str.split("/"):
                        parts = entry.split("|")
                        if len(parts) != 4:
                            raise ValueError(f"Invalid field format: '{entry}'")
                        field, source, source_ticker, source_field = parts
                        ticker.fields.append(
                            SourceF(
                                field=field.strip(),
                                source=source.strip(),
                                source_ticker=source_ticker.strip(),
                                source_field=source_field.strip(),
                            )
                        )
                except Exception as e:
                    return (
                        jsonify(
                            {
                                "error": f"Error parsing 'fields' for ticker {ticker_id}: {str(e)}"
                            }
                        ),
                        400,
                    )

            ticker.save()

        return (
            jsonify({"status": "success", "message": f"{len(data)} tickers processed"}),
            200,
        )

    except Exception as e:
        return jsonify({"error": f"Unexpected server error: {str(e)}"}), 500
