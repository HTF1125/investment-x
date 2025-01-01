import pandas as pd
from ix.misc import get_yahoo_data
from ix.misc import get_bloomberg_data
from ix.misc import get_fred_data
from ix.misc import get_logger
from ix import misc
from ix.db import MetaData, Performance

logger = get_logger(__name__)


def run():

    # update_px_last()
    Performance.delete_all()
    update_price_performance()
    update_economic_calendar()


def update_px_last():
    logger.debug("Initialize update PX_LAST data")
    for metadata in MetaData.find_all().run():
        logger.info(f"Processing metadata with code: {metadata.code}")
        # Loop through each data source for the metadata
        for data_source in metadata.data_sources:
            try:
                logger.info(
                    f"Checking data source: {data_source.source} for metadata code={metadata.code}"
                )
                if data_source.source == "YAHOO":
                    ts = get_yahoo_data(code=data_source.s_code)[data_source.s_field]
                    logger.info(
                        f"Successfully fetched data from YAHOO for code={data_source.s_code}, field={data_source.s_field}"
                    )
                elif data_source.source == "BLOOMBERG":
                    ts = get_bloomberg_data(
                        code=data_source.s_code,
                        field=data_source.s_field,
                    ).iloc[:, 0]
                    logger.info(
                        f"Successfully fetched data from BLOOMBERG for code={data_source.s_code}, field={data_source.s_field}"
                    )
                elif data_source.source == "FRED":
                    ts = get_fred_data(ticker=data_source.s_code).iloc[:, 0]
                    logger.info(
                        f"Successfully fetched data from FRED for ticker={data_source.s_code}"
                    )
                else:
                    logger.warning(
                        f"Unknown data source: {data_source.source} for metadata code={metadata.code}"
                    )
                    continue
                # Update the corresponding field in metadata with the fetched time series
                metadata.ts(field=data_source.field).data = ts
                logger.info(
                    f"Updated field={data_source.field} for metadata code={metadata.code} with new time series data"
                )

            except Exception as e:
                # Log errors if data fetching or updating fails
                logger.error(
                    f"Error processing metadata code={metadata.code}, data source={data_source.source}, field={data_source.field}: {e}"
                )

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
    for metadata in MetaData.find_all().run():
        px_last = metadata.ts(field="PX_LAST").data
        px_last.name = metadata.code
        if px_last.empty:
            continue
        px_lasts.append(px_last)
    px_lasts = pd.concat(px_lasts, axis=1)
    px_lasts = px_lasts.sort_index().loc[:asofdate].resample("D").last().ffill()

    print(f"update performance for {px_lasts.index[-1]}")
    for code in px_lasts:
        pxlast = px_lasts[code].round(2)
        level = round(pxlast.iloc[-1], 2)
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


def bloomberg_only():

    import requests
    from ix.db import MetaData
    from ix.misc import get_bloomberg_data

    # Define the API URL and parameters
    url = "https://port-0-investmentx-ghdys32bls2zef7e.sel5.cloudtype.app"
    response = requests.get(f"{url}/api/metadatas")
    for metadata in response.json():
        mt = MetaData(**metadata)
        for data_source in mt.data_sources:
            if data_source.source == "BLOOMBERG":
                ts = get_bloomberg_data(
                    code=data_source.s_code,
                    field=data_source.s_field,
                ).iloc[:, 0]
                params = {"code": mt.code, "field": data_source.field}
                body = {"data": ts.to_dict()}
                requests.put(f"{url}/api/timeseries", params=params, json=body)
                # Check the response
                if response.status_code == 200:
                    print("Time series updated successfully.")
                else:
                    print(
                        f"Failed to update time series. Status code: {response.status_code}, Response: {response.text}"
                    )
