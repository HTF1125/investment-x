import pandas as pd
from flask import jsonify
from ix.wx.app import server
from ix.misc import get_logger
from ix.db import Metadata

logger = get_logger(__name__)


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
    from ix.db import TimeSeries
    from ix.misc import relative_timestamp
    datas = []
    for ts in TimeSeries.find({"field" : "PX_LAST"}).run():
        if ts.field not in [
            "PX_OPEN",
            "PX_HIGH",
            "PX_LOW",
            "PX_VOLUME",
            "PX_CLOSE",
        ]:
            data = ts.data
            if data.empty:
                continue
            data.name = f"{ts.code}:{ts.field}"
            datas.append(data.loc[relative_timestamp(period="3Y"):])

    datas = pd.concat(datas, axis=1).replace(np.nan, None).sort_index()
    datas.index = pd.to_datetime(datas.index)
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
    return jsonify(EconomicCalendar.get_dataframe().to_dict("records"))


@server.route("/api/insights")
def get_insights():
    """
    API endpoint to retrieve metadata.
    """
    from ix.db import get_insights

    insights = get_insights(limit=100)

    return jsonify([insight.model_dump()  for insight in insights])
