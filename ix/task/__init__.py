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


def update_yahoo_data():

    from ix.db import Ticker
    from ix.misc import get_yahoo_data

    tickers = list(Ticker.find().run())
    total_tickers = len(tickers)

    for i, ticker_code in enumerate(tickers, start=1):
        print(f"[{i}/{total_tickers}] Processing ticker: {ticker_code.code}")
        for field_code in ticker_code.fields:
            if field_code.source == "Yahoo":
                if field_code.source_ticker is None:
                    print(f" - Skipped: No source_ticker for field {field_code.field}")
                    continue
                print(
                    f" - Fetching {field_code.field} from Yahoo ({field_code.source_ticker})..."
                )
                data = get_yahoo_data(code=field_code.source_ticker)
                if data.empty:
                    print(f"   -> No data returned for {field_code.source_ticker}")
                    continue
                ticker_code.get_timeseries(field_code.field).data = data[
                    field_code.source_field
                ]
                print(f"   -> Data updated for field: {field_code.field}")


def update_investmentx_data():

    import ix

    for ticker_code in ix.db.Ticker.find().run():
        for field_code in ticker_code.fields:
            try:
                if field_code.source == "InvestmentX":
                    if field_code.field == "PX_DIFF":
                        temp_data = ticker_code.get_data(field="PX_LAST")
                        if ticker_code.frequency == "Monthly":
                            f_data = temp_data.diff(1).dropna()
                            ticker_code.get_timeseries(field=field_code.field).data = (
                                f_data
                            )
                    if field_code.field == "PX_DIFF_DIFF":
                        temp_data = ticker_code.get_data(field="PX_LAST")
                        if ticker_code.frequency == "Monthly":
                            f_data = temp_data.diff(1).diff(1).dropna()
                            ticker_code.get_timeseries(field=field_code.field).data = (
                                f_data
                            )
                    if field_code.field == "EPS_NTMA_YOY":
                        f_data = (
                            ticker_code.get_data("EPS_NTMA")
                            .div(ticker_code.get_data("EPS_LTMA"))
                            .sub(1)
                            .mul(100)
                            .dropna()
                        )
                        if f_data.empty:
                            continue
                        ticker_code.get_timeseries(field=field_code.field).data = f_data
                    if field_code.field == "PX_YOY":
                        if ticker_code.frequency == "Monthly":
                            temp_data = ticker_code.get_data(field="PX_LAST")
                            ticker_code.get_timeseries(field=field_code.field).data = (
                                temp_data.pct_change(12).mul(100).dropna()
                            )
            except Exception as e:
                print(f"Error: {e}")
                continue
