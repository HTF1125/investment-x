import pandas as pd
from ix.misc import get_yahoo_data
from ix.misc import get_bloomberg_data
from ix.misc import get_logger
from ix import db
from ix import misc


logger = get_logger(__name__)


def run():

    update_price_data()
    db.Performance.delete_all()
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

        data = data.combine_first(pd.Series(px_last.data)).loc[
            : misc.last_business_day()
        ]
        px_last.set({"data": data.to_dict()})

    logger.debug("Timeseries update process completed.")


def update_economic_calendar():

    import investpy
    from ix.misc import as_date, onemonthbefore, onemonthlater
    from ix.db import EconomicCalendar
    import pandas as pd

    data = investpy.economic_calendar(
        from_date=as_date(onemonthbefore(), "%d/%m/%Y"),
        to_date=as_date(onemonthlater(), "%d/%m/%Y"),
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


def update_price_performance():

    pxlasts = []
    asofdate = misc.last_business_day().date()

    for ticker in db.Ticker.find_many(db.Ticker.source == "YAHOO").run():
        if ticker.source == "YAHOO":
            pxlast = db.PxLast.find_one(db.PxLast.code == ticker.code).run()
            if pxlast is None:
                continue
            pxlast_data = pd.Series(data=pxlast.data, name=pxlast.code)
            pxlasts.append(pxlast_data)
    pxlasts = pd.concat(pxlasts, axis=1)
    pxlasts.index = pd.to_datetime(pxlasts.index)
    pxlasts = pxlasts.sort_index().loc[:asofdate].resample("D").last().ffill()


    print(f"update performance for {pxlasts.index[-1]}")
    for code in pxlasts:
        pxlast = pxlasts[code]
        level = pxlast.iloc[-1]
        pct_chg = (level / pxlast).sub(1).mul(100).round(2)
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
            "code": code,
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
        try:
            if existing_performance:
                # Update the existing document
                existing_performance.update({"$set": performance_data})
                print(f"Updated Performance for {code} on {asofdate}")
            else:
                # Create a new document
                new_performance = db.Performance(**performance_data)
                new_performance.create()
                print(f"Created new Performance for {code} on {asofdate}")
        except Exception as exc:
            print(exc)
            print(performance_data)
