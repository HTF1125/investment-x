import pandas as pd
from ix.misc import get_yahoo_data
from ix.misc import get_bloomberg_data
from ix.misc import get_logger
from ix.misc import yesterday, as_date
from ix import db

logger = get_logger(__name__)


def run():

    update_price_data()
    update_price_performance()
    update_economic_calendar()


def update_price_data():
    logger.debug("Initialization complete.")

    for ticker in db.Ticker.find_all():

        px_last = db.PxLast.find_one(db.PxLast.code == ticker.code).run()
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


def update_price_performance():

    asofdate = yesterday().date()

    for ticker in db.Ticker.find_all().run():

        if ticker.source == "YAHOO":

            pxlast = db.PxLast.find_one(db.PxLast.code == ticker.code).run()

            if pxlast is not None:
                pxlastdata = pd.Series(pxlast.data)
                pxlastdata.index = pd.to_datetime(pxlastdata.index)
                pxlastdata = pxlastdata.loc[:asofdate].resample("D").last().ffill()
                level = pxlastdata.get(as_date(asofdate), None)
                if level is None:
                    continue
                pct_chg = (level / pxlastdata).sub(1).mul(100).round(2)
                pct_chg_1d = pct_chg.get(asofdate - pd.offsets.BusinessDay(1), None)
                pct_chg_1w = pct_chg.get(asofdate - pd.DateOffset(days=7), None)
                pct_chg_1m = pct_chg.get(asofdate - pd.DateOffset(months=1), None)
                pct_chg_3m = pct_chg.get(asofdate - pd.DateOffset(months=3), None)
                pct_chg_6m = pct_chg.get(asofdate - pd.DateOffset(months=6), None)
                pct_chg_1y = pct_chg.get(asofdate - pd.DateOffset(months=12), None)
                pct_chg_3y = pct_chg.get(asofdate - pd.DateOffset(months=12 * 3), None)
                pct_chg_mtd = pct_chg.get(
                    asofdate - pd.offsets.MonthBegin() - pd.DateOffset(days=1), None
                )
                pct_chg_ytd = pct_chg.get(
                    asofdate - pd.offsets.YearBegin() - pd.DateOffset(days=1), None
                )

                # Check if a Performance document with the same date and code exists
                existing_performance = db.Performance.find_one(
                    db.Performance.code == ticker.code, db.Performance.date == asofdate
                ).run()

                performance_data = {
                    "code": ticker.code,
                    "date": asofdate,
                    "level": level,
                    "pct_chg_1d": pct_chg_1d,
                    "pct_chg_1w": pct_chg_1w,
                    "pct_chg_1m": pct_chg_1m,
                    "pct_chg_3m": pct_chg_3m,
                    "pct_chg_6m": pct_chg_6m,
                    "pct_chg_1y": pct_chg_1y,
                    "pct_chg_3y": pct_chg_3y,
                    "pct_chg_mtd": pct_chg_mtd,
                    "pct_chg_ytd": pct_chg_ytd,
                }

                if existing_performance:
                    # Update the existing document
                    existing_performance.update({"$set": performance_data})
                    print(f"Updated Performance for {ticker.code} on {asofdate}")
                else:
                    # Create a new document
                    new_performance = db.Performance(**performance_data)
                    new_performance.create()
                    print(f"Created new Performance for {ticker.code} on {asofdate}")
