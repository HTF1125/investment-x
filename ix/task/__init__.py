import pandas as pd
from ix.misc import get_yahoo_data
from ix.misc import get_bloomberg_data
from ix.misc import get_logger
from ix.db.models import Ticker, Timeseries, TickerNew

logger = get_logger(__name__)


def run():
    logger.debug("Initialization complete.")

    for ticker in TickerNew.find_all():
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

        data = data.combine_first(pd.Series(ticker.px_last))
        ticker.set({"px_last": data.to_dict()})

    logger.debug("Timeseries update process completed.")


def update_yahoo_data():
    for ticker in Ticker.find_many({"source": "YAHOO", "yahoo": {"$ne": None}}):
        if ticker.yahoo is None:
            continue
        data = get_yahoo_data(code=ticker.yahoo)["Adj Close"]
        if data.empty:
            continue
        insert_in_timeseries(data, code=ticker.code, field="PxLast")


def update_bloomberg_data():
    for ticker in Ticker.find_many({"source": "BLOOMBERG", "bloomberg": {"$ne": None}}):
        if ticker.bloomberg is None:
            continue
        data = get_bloomberg_data(code=ticker.bloomberg)
        if data.empty:
            continue
        data = data.iloc[:, 0]
        insert_in_timeseries(data, code=ticker.code, field="PxLast")


def insert_in_timeseries(data: pd.Series, code: str, field: str):
    ts = Timeseries.find_one(code=code, field=field).run()
    if ts is None:
        # If no existing timeseries, create a new one
        ts = Timeseries(data=data.to_dict(), code=code, field=field).sort_index()
        Timeseries.insert_one(ts)
        logger.debug(f"Created new timeseries for {code}")
    else:
        # If timeseries exists, update its data field
        existing_data = pd.Series(ts.data).sort_index()
        logger.debug(f"Existing data for {code}: {existing_data.tail()}")

        # Combine the existing data with the new data, prioritizing existing data
        combined_data = existing_data.combine_first(data)
        ts.set({"data": combined_data.to_dict()})

        logger.debug(f"Updated timeseries for {code}")
    pass


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
