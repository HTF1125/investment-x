import numpy as np
import pandas as pd
from ix.misc import get_logger
from ix.db import Metadata
from ix.misc import as_date, onemonthbefore, onemonthlater
from ix.misc.date import periods, last_business_day, to_timestamp, relative_timestamp
from ix.core.perf import to_log_return
from ix.db import EconomicCalendar

logger = get_logger(__name__)


def run():
    update_px_last()
    update_economic_calendar()

def update_px_last():
    logger.debug("Initialize update PX_LAST data")
    for metadata in Metadata.find_all().run():
        try:
            # Process Yahoo ticker data if available.
            if metadata.yah_ticker:
                metadata.update_px()
        except Exception as e:
            logger.error(
                f"Error processing metadata code {metadata.code}: {e}", exc_info=True
            )
    logger.debug("Timeseries update process completed.")

def update_economic_calendar():

    import investpy

    data = investpy.economic_calendar(
        from_date=as_date(onemonthbefore(), "%d/%m/%Y"),
        to_date=as_date(onemonthlater(), "%d/%m/%Y"),
        importances=["high"],
    )

    if not isinstance(data, pd.DataFrame):
        return
    data["date"] = pd.to_datetime(data["date"], dayfirst=True).dt.strftime("%Y-%m-%d")
    data = data.drop(columns=["id"])

    EconomicCalendar.delete_all()
    objs = []
    for record in data.to_dict("records"):
        record = {str(key): value for key, value in record.items()}
        objs.append(EconomicCalendar(**record))
    EconomicCalendar.insert_many(objs)


