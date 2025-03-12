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
    update_performance()

def update_px_last(has_performance: bool = False):
    logger.debug("Initialize update PX_LAST data")

    if has_performance:
        query = {"has_performance": True}
    else:
        query = {}

    for metadata in Metadata.find(query).run():
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
    asofdate = last_business_day()
    for metadata in Metadata.find({"has_performance": True}).run():
        px_last = pd.to_numeric(metadata.ts(field="PX_LAST").data, errors="coerce").dropna()
        px_last.name = metadata.code
        if px_last.empty:
            continue
        px_last = px_last.dropna().loc[:asofdate]
        px_last_end = float(px_last.iloc[-1])
        performance = {"PX_LAST": px_last_end}
        pct_change = to_log_return(px=px_last).iloc[1:]
        init_date = to_timestamp(str(pct_change.index[0]), normalize=True)
        if pct_change.empty:
            continue
        for period in periods:
            rel_date = relative_timestamp(asofdate, period, offset_1d=True, normalize=True)
            if rel_date < init_date:
                continue
            pct_chg_slice = pct_change.loc[str(rel_date) :].copy().astype(float)
            pct_chg_value = np.exp(pct_chg_slice.sum()) - 1
            px_last_start = float(px_last.loc[:rel_date].iloc[-1])
            performance[f"PCT_CHG_{period}"] = round(pct_chg_value, 6) * 100
            performance[f"PX_DIFF_{period}"] = round(px_last_end - px_last_start, 6)
            if period == "1D":
                continue
            vol_value = pct_chg_slice.std() * np.sqrt(252)
            performance[f"VOL_{period}"] = round(float(vol_value), 6) * 100
        metadata.tp().data = pd.Series(performance).astype(float)
