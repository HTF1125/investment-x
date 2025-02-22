import numpy as np
import pandas as pd
from ix.misc import get_logger, yesterday
from ix.db import Metadata
from ix.misc import as_date, onemonthbefore, onemonthlater
from ix.misc.date import periods, yesterday, to_timestamp, relative_timestamp
from ix.core.perf import to_log_return

from ix.db import EconomicCalendar
logger = get_logger(__name__)


def run():
    update_px_last()
    update_economic_calendar()
    update_performance()

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

def update_performance():
    asofdate = yesterday()
    logger.debug("Starting metadata performance processing...")
    for _, metadata in enumerate(Metadata.find({"has_performance": True}).run()):
        try:
            # Retrieve and convert price data to float
            px_last = metadata.ts(field="PX_LAST").data.astype(float)
        except Exception as e:
            logger.warning(
                f"Failed to retrieve PX_LAST for metadata ID {metadata.code}: {e}"
            )
            continue
        if px_last.empty:
            logger.warning(
                f"Skipping empty PX_LAST data for metadata ID: {metadata.code}"
            )
            continue
        # Filter data up to the as-of date and update the last price field
        px_last = px_last.loc[:asofdate]
        latest_price = float(px_last.iloc[-1])
        metadata.tp(field="PX_LAST").data = round(latest_price, 6)

        # Calculate log returns and convert to simple returns (ignoring the initial NA)
        pct_change = to_log_return(px=px_last).iloc[1:]
        if pct_change.empty:
            logger.warning(
                f"No log return data available for metadata ID: {metadata.code}"
            )
            continue

        init_date = to_timestamp(str(pct_change.index[0]), normalize=True)
        logger.debug(f"Processing metadata ID: {metadata.code}")
        logger.debug(f"Data range: {init_date.date()} to {asofdate.date()}")

        for period in periods:
            # Determine the relative start date for the current period
            rel_date = relative_timestamp(
                asofdate, period, offset_1d=True, normalize=True
            )

            if rel_date < init_date:
                logger.debug(
                    f"Skipping period '{period}' - relative date {rel_date} is before init date {init_date.date()}"
                )
                continue

            # Slice the log returns from the relative date onward
            pct_chg_slice = pct_change.loc[str(rel_date) :].copy().astype(float)
            if pct_chg_slice.empty:
                logger.debug(f"No data for period '{period}' starting from {rel_date}")
                continue

            # Calculate cumulative percentage change from log returns
            pct_chg_value = np.exp(pct_chg_slice.sum()) - 1
            metadata.tp(field=f"PCT_CHG_{period}").data = round(pct_chg_value, 6) * 100

            # Calculate annualized volatility using a 252-day year
            vol_value = pct_chg_slice.std() * np.sqrt(252)
            metadata.tp(field=f"VOL_{period}").data = round(float(vol_value), 6) * 100

            logger.debug(
                f"Updated period '{period}': PCT_CHG={round(pct_chg_value, 6)}, VOL={round(vol_value, 6)}"
            )

    logger.debug("Metadata performance processing completed.")
