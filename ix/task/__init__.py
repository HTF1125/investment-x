import pandas as pd
from ix.misc import get_yahoo_data
from ix.misc import get_bloomberg_data
from ix.misc import get_logger
from ix.misc import yesterday
from ix import db

logger = get_logger(__name__)


def run():
    logger.debug("Initialization complete.")

    for ticker in db.Ticker.find_all():

        px_last = db.PxLast.find_one(db.PxLast.code==ticker.code).run()
        if px_last is None:
            px_last = db.PxLast(code=ticker.code).create()
        data = None

        if ticker.source == "YAHOO":
            if ticker.yahoo is None:
                logger.debug(f"Skipping {ticker.code}: No Yahoo ID.")
                continue
            data = get_yahoo_data(code=ticker.yahoo)["Adj Close"]
            logger.debug(f"Fetched data from Yahoo for {ticker.code}")

        elif ticker.source == "BLOOMBERG":
            if ticker.bloomberg is None:
                logger.debug(f"Skipping {ticker.code}: No Bloomberg ID.")
                continue
            data = get_bloomberg_data(code=ticker.bloomberg)
            if data.empty:
                continue
            data = data.iloc[:, 0]
            logger.debug(f"Fetched data from Bloomberg for {ticker.code}")

        else:
            logger.debug(f"Skipping {ticker.code}: Unsupported source {ticker.source}.")
            continue

        if data is None or data.empty:
            logger.debug(f"No data found for {ticker.code}, skipping.")
            continue

        data = data.combine_first(pd.Series(px_last.data)).loc[: yesterday()]
        px_last.set({"data": data.to_dict()})

    logger.debug("Timeseries update process completed.")


def update_economic_calendar():

    import investpy
    from ix.misc import as_date, onemonthbefore, onemonthlater
    from ix.db import EconomicCalendar
    import pandas as pd

    data: pd.DataFrame = investpy.economic_calendar(
        from_date=as_date(onemonthbefore(), "%d/%m/%Y"),
        to_date=as_date(onemonthlater(), "%d/%m/%Y"),
    )
    data["date"] = pd.to_datetime(data["date"], dayfirst=True).dt.strftime("%Y-%m-%d")
    data = data.drop(columns=["id"])

    EconomicCalendar.delete_all()
    objs = []
    for record in data.to_dict("records"):
        objs.append(EconomicCalendar(**record))
    EconomicCalendar.insert_many(objs)


