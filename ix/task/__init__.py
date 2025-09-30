
from ix.misc.terminal import get_logger
import investpy
from ix.misc import as_date, onemonthbefore, onemonthlater
from ix.db import EconomicCalendar
import pandas as pd
from ix.db.models import Timeseries
from ix.misc.crawler import get_yahoo_data
from ix.misc.crawler import get_fred_data
from ix.misc.crawler import get_naver_data




logger = get_logger(__name__)



def update_economic_calendar():

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





def update_yahoo_data():

    logger.info("Starting Yahoo data update process.")

    count_total = 0
    count_skipped_no_ticker = 0
    count_skipped_empty_data = 0
    count_updated = 0

    for ts in Timeseries.find({"source": "Yahoo"}).run():
        count_total += 1
        if ts.source_code is None:
            logger.debug(f"Skipping timeseries {ts.code} (no source_ticker).")
            count_skipped_no_ticker += 1
            continue

        ticker, field = str(ts.source_code).split(":")

        logger.debug(f"Fetching data for {ticker} (field: {field}).")
        try:
            _data = get_yahoo_data(code=ticker)[field]
        except Exception as e:
            logger.warning(f"Error fetching data for {ts.source_code}: {e}")
            continue

        if _data.empty:
            logger.debug(f"No data returned for {ts.source_code}. Skipping.")
            count_skipped_empty_data += 1
            continue

        ts.data = _data
        logger.info(f"Updated data for {ts.code} from {ts.source_code}.")
        count_updated += 1

    logger.info(f"Yahoo data update complete: "
                f"{count_total} total, "
                f"{count_updated} updated, "
                f"{count_skipped_no_ticker} skipped (no ticker), "
                f"{count_skipped_empty_data} skipped (empty data).")


def update_fred_data():


    logger.info("Starting Fred data update process.")

    count_total = 0
    count_skipped_no_ticker = 0
    count_skipped_empty_data = 0
    count_updated = 0

    for ts in Timeseries.find({"source": "Fred"}).run():
        count_total += 1
        if ts.source_code is None:
            logger.debug(f"Skipping timeseries {ts.code} (no source_ticker).")
            count_skipped_no_ticker += 1
            continue
        ticker, field = str(ts.source_code).split(":")
        logger.debug(f"Fetching data for {ticker} (field: {field}).")
        try:
            _data = get_fred_data(ticker)[field]
        except Exception as e:
            logger.warning(f"Error fetching data for {ts.source_code}: {e}")
            continue

        if _data.empty:
            logger.debug(f"No data returned for {ts.source_code}. Skipping.")
            count_skipped_empty_data += 1
            continue

        ts.data = _data
        logger.info(f"Updated data for {ts.code} from {ts.source_code}.")
        count_updated += 1

    logger.info(f"Fred data update complete: "
                f"{count_total} total, "
                f"{count_updated} updated, "
                f"{count_skipped_no_ticker} skipped (no ticker), "
                f"{count_skipped_empty_data} skipped (empty data).")



def update_naver_data():


    logger.info("Starting Naver data update process.")

    count_total = 0
    count_skipped_no_ticker = 0
    count_skipped_empty_data = 0
    count_updated = 0

    for ts in Timeseries.find({"source": "Naver"}).run():
        count_total += 1
        if ts.source_code is None:
            logger.debug(f"Skipping timeseries {ts.code} (no source_ticker).")
            count_skipped_no_ticker += 1
            continue
        ticker, field = str(ts.source_code).split(":")
        logger.debug(f"Fetching data for {ticker} (field: {field}).")
        try:
            _data = get_naver_data(ticker)[field]
        except Exception as e:
            logger.warning(f"Error fetching data for {ts.source_code}: {e}")
            continue

        if _data.empty:
            logger.debug(f"No data returned for {ts.source_code}. Skipping.")
            count_skipped_empty_data += 1
            continue

        ts.data = _data
        logger.info(f"Updated data for {ts.code} from {ts.source_code}.")
        count_updated += 1

    logger.info(f"Fred data update complete: "
                f"{count_total} total, "
                f"{count_updated} updated, "
                f"{count_skipped_no_ticker} skipped (no ticker), "
                f"{count_skipped_empty_data} skipped (empty data).")


def send_price_data():
    import io
    import pandas as pd
    from ix.db.models import Timeseries
    from ix.misc.email import EmailSender
    datas = {}
    for ts in Timeseries.find().run():
        if str(ts.code).endswith("Equity:PX_LAST"):
            data = ts.data
            if data.empty:
                continue
            datas[ts.code] = data.iloc[-1]

    datas = pd.Series(datas)
    datas.index.name = "Code"
    datas.name = "Value"

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="xlsxwriter") as writer:
        datas.to_excel(writer, sheet_name="Data")
    excel_buffer.seek(0)

    # Step 3: Create and send email
    email_sender = EmailSender(
        to="26106825@heungkuklife.co.kr, 26107455@heungkuklife.co.kr",
        subject="[IX] Data",
        content="\n\nPlease find the attached Excel file as requested.\n\nBest regards,\nYour Automation",
    )
    email_sender.attach(file_buffer=excel_buffer, filename="Data.xlsx")
    email_sender.send()










def daily():
    update_yahoo_data()
    update_fred_data()
    update_naver_data()
    # send_price_data()
