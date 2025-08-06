# import pandas as pd
# from flask import jsonify
# from ix.wx.app import server
# from ix.misc import get_logger
# from ix.db.query import *

# logger = get_logger(__name__)


# from flask import request
# import os
# from ix.db import Timeseries

# @server.route("/api/upload_data", methods=["POST"])
# def upload_data():
#     try:
#         data = request.get_json(force=True)
#         if not isinstance(data, list):
#             return (
#                 jsonify({"error": "Invalid payload: expected a list of records"}),
#                 400,
#             )

#         df = pd.DataFrame(data)

#         required_columns = {"date", "code", "value"}
#         if not required_columns.issubset(df.columns):
#             return (
#                 jsonify(
#                     {
#                         "error": f"Missing required fields: {required_columns - set(df.columns)}"
#                     }
#                 ),
#                 400,
#             )

#         df["value"] = pd.to_numeric(df["value"], errors="coerce")
#         df = df.dropna(subset=["value"])

#         pivoted = (
#             df.pivot(index="date", columns="code", values="value")
#             .sort_index()
#             .dropna(how="all", axis=1)
#             .dropna(how="all", axis=0)
#         )
#         for code in pivoted.columns:

#             ts = Timeseries.find_one({"code": code}).run()
#             if ts is None:
#                 ts = Timeseries(code=code).create()
#             ts.data = pivoted[code].dropna()

#         return (
#             jsonify(
#                 {
#                     "message": f"Successfully received {len(df)} records.",
#                 }
#             ),
#             200,
#         )

#     except Exception as e:
#         logger.exception("Failed to process VBA upload")
#         return jsonify({"error": str(e)}), 500


# @server.route("/api/economic_calendar")
# def get_economic_calendar():
#     """
#     API endpoint to retrieve metadata.
#     """
#     from ix.db import EconomicCalendar
#     from ix.task import update_economic_calendar

#     update_economic_calendar()
#     return jsonify(EconomicCalendar.get_dataframe().to_dict("records"))


# @server.route("/api/insights")
# def get_insights():
#     """
#     API endpoint to retrieve metadata.
#     """
#     from ix.db import get_insights

#     insights = get_insights(limit=100)

#     return jsonify([insight.model_dump() for insight in insights])


# from flask import Response
# import os


# @server.route("/download/0.DataLoader.xlsm")
# def download_file():
#     file_path = os.path.join("docs", "0.DataLoader.xlsm")

#     if not os.path.exists(file_path):
#         return Response("File not found", status=404)

#     with open(file_path, "rb") as f:
#         data = f.read()

#     return Response(
#         data,
#         mimetype="application/vnd.ms-excel.sheet.macroEnabled.12",
#         headers={"Content-Disposition": "attachment; filename=0.DataLoader.xlsm"},
#     )


# @server.route("/api/timeseries", methods=["GET"])
# def _get_timeseries():
#     """
#     API endpoint to retrieve metadata.
#     """
#     from ix.db import Timeseries

#     return jsonify([timeseries.model_dump() for timeseries in Timeseries.find().run()])


# from collections import OrderedDict
# import json
# @server.route("/api/series", methods=["GET"])
# def get_series():
#     import numpy as np
#     series = request.args.getlist("series")
#     start = request.args.get("start")
#     end = request.args.get("end")
#     include_dates = request.args.get("include_dates", "false").lower() == "true"
#     if not series:
#         return jsonify({"error": "Missing 'series' query parameter"}), 400
#     try:
#         datas = pd.DataFrame()

#         for code in series:
#             datas = pd.concat([datas, Series(code)], axis=1)
#         datas.index = pd.to_datetime(datas.index)
#         datas = datas.dropna(how='all')
#         datas = datas.replace(np.nan, None)
#         if start:
#             datas = datas.loc[start:]
#         if end:
#             datas = datas.loc[:end]
#         if include_dates:
#             datas.index = pd.to_datetime(datas.index).strftime("%Y-%m-%d")
#             datas = datas.sort_index()
#             datas.index.name = "Idx"
#             datas = datas.reset_index()
#         payload = OrderedDict((col, datas[col].tolist()) for col in datas.columns)
#         text = json.dumps(payload, ensure_ascii=False, sort_keys=False)
#         return Response(text, mimetype="application/json")
#     except Exception as e:
#         print(str(e))
#         return jsonify({"error": str(e)}), 500


# @server.route("/api/timeseries", methods=["POST"])
# def upload_tickers():
#     """
#     API endpoint to upload ticker metadata.

#     Expects JSON array where each row contains:
#     - id (primary key)
#     - code (ticker code)
#     - name, frequency, asset_class, category (optional metadata)
#     - fields: a string of 'field|source|source_ticker|source_field' joined by '/'
#     """
#     import pandas as pd
#     from flask import request, jsonify
#     from ix.db import Timeseries
#     from bson import ObjectId
#     try:
#         # Parse JSON body into DataFrame
#         data = pd.DataFrame(request.get_json(force=True))
#         if "id" not in data.columns or "code" not in data.columns:
#             return jsonify({"error": "Missing required fields: 'id' or 'code'"}), 400

#         data = data.set_index("id", drop=True)
#         for ts_id, ts_row in data.iterrows():
#             if ts_id is None:
#                 db_timeseries = Timeseries(code=ts_row["code"]).create()
#             else:
#                 db_timeseries = Timeseries.find_one(Timeseries.id == ObjectId(str(ts_id))).run()
#             if db_timeseries is None:
#                 db_timeseries = Timeseries(code=ts_row["code"]).create()
#             db_timeseries.update({"$set": ts_row.to_dict()})
#         return (
#             jsonify({"status": "success", "message": f"{len(data)} tickers processed"}),
#             200,
#         )
#     except Exception as e:
#         return jsonify({"error": f"Unexpected server error: {str(e)}"}), 500

# # @server.route("/api/timeseries_data", methods = ["GET"])
# # def _get_timeseries_data():

# #     ff = []
# #     for ts in Timeseries.find().run():

# #         if ts.code.endswith("Equity:PX_LAST") or ts.code.endswith(":PX_YTM"):
# #             ff.append(ts.data)

# #     return pd.concat(ff, axis=1).iloc[-300:].to_dict("records")
