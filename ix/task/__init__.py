import pandas as pd
from ix.misc import get_yahoo_data
from ix.misc import get_bloomberg_data
from ix.misc import get_logger
from ix import misc
from ix.db import MetaData, Performance

logger = get_logger(__name__)


def run():

    update_px_last()
    Performance.delete_all()
    update_price_performance()
    update_economic_calendar()


def update_px_last():
    logger.debug("Initialize update PX_LAST data")
    for metadata in MetaData.find_all():
        if metadata.source == "YAHOO":
            if metadata.yahoo is None:
                logger.debug(f"Skipping {metadata.code}: No Yahoo ID.")
                continue
            data = get_yahoo_data(code=metadata.yahoo)["Adj Close"]
            logger.debug(f"Fetched data from Yahoo for {metadata.code}")

        elif metadata.source == "BLOOMBERG":
            if metadata.bloomberg is None:
                logger.debug(f"Skipping {metadata.code}: No Bloomberg ID.")
                continue
            data = get_bloomberg_data(code=metadata.bloomberg)
            if data.empty:
                continue
            data = data.iloc[:, 0]
            logger.debug(f"Fetched data from Bloomberg for {metadata.code}")
        else:
            logger.debug(
                f"Skipping {metadata.code}: Unsupported source {metadata.source}."
            )
            continue
        if data.empty:
            continue

        px_last = metadata.ts(field="PX_LAST")
        px_last.data = data
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

    asofdate = misc.last_business_day().date()
    px_lasts = []
    for metadata in MetaData.find_many(MetaData.source == "YAHOO").run():
        px_last = metadata.ts(field="PX_LAST").data
        px_last.name = metadata.code
        if px_last.empty:
            continue
        px_lasts.append(px_last)
    px_lasts = pd.concat(px_lasts, axis=1)
    px_lasts = px_lasts.sort_index().loc[:asofdate].resample("D").last().ffill()

    print(f"update performance for {px_lasts.index[-1]}")
    for code in px_lasts:
        pxlast = px_lasts[code]
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
        existing_performance = Performance.find_one(
            Performance.code == metadata.code,
            Performance.date == asofdate,
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
                new_performance = Performance(**performance_data)
                new_performance.create()
                print(f"Created new Performance for {code} on {asofdate}")
        except Exception as exc:
            print(exc)
            print(performance_data)
