from ix.misc.terminal import get_logger
import investpy
from ix.misc import as_date, onemonthbefore, onemonthlater

# from ix.db import EconomicCalendar  # Commented out - MongoDB not in use
import pandas as pd

# from ix.db.models import Timeseries  # Commented out - MongoDB not in use
from ix.misc.crawler import get_yahoo_data
from ix.misc.crawler import get_fred_data
from ix.misc.crawler import get_naver_data
from ix.db.models import Timeseries

logger = get_logger(__name__)


# def update_economic_calendar():

#     data = investpy.economic_calendar(
#         from_date=as_date(onemonthbefore(), "%d/%m/%Y"),
#         to_date=as_date(onemonthlater(), "%d/%m/%Y"),
#     )

#     if not isinstance(data, pd.DataFrame):
#         return
#     data["date"] = pd.to_datetime(data["date"], dayfirst=True).dt.strftime("%Y-%m-%d")
#     data = data.drop(columns=["id"])

#     EconomicCalendar.delete_all()
#     objs = []
#     for record in data.to_dict("records"):
#         record = {str(key): value for key, value in record.items()}
#         objs.append(EconomicCalendar(**record))
#     EconomicCalendar.insert_many(objs)


def update_yahoo_data():

    logger.info("Starting Yahoo data update process.")

    count_total = 0
    count_skipped_no_ticker = 0
    count_skipped_empty_data = 0
    count_updated = 0

    from ix.db.conn import Session

    with Session() as session:
        timeseries_list = (
            session.query(Timeseries).filter(Timeseries.source == "Yahoo").all()
        )

        # Extract all attributes immediately to avoid detached instance errors
        ts_data_list = []
        for ts in timeseries_list:
            ts_data_list.append(
                {"id": ts.id, "code": ts.code, "source_code": ts.source_code}
            )

        for ts_data in ts_data_list:
            ts_id = ts_data["id"]
            ts_code = ts_data["code"]
            ts_source_code = ts_data["source_code"]

            count_total += 1
            if ts_source_code is None:
                logger.debug(f"Skipping timeseries {ts_code} (no source_ticker).")
                count_skipped_no_ticker += 1
                continue

            ticker, field = str(ts_source_code).split(":", maxsplit=1)

            logger.debug(f"Fetching data for {ticker} (field: {field}).")
            try:
                _data = get_yahoo_data(code=ticker)[field]
            except Exception as e:
                logger.warning(f"Error fetching data for {ts_source_code}: {e}")
                continue

            if _data.empty:
                logger.debug(f"No data returned for {ts_source_code}. Skipping.")
                count_skipped_empty_data += 1
                continue

            # Reload the object and set data within session
            ts_reloaded = (
                session.query(Timeseries).filter(Timeseries.id == ts_id).first()
            )
            if ts_reloaded is not None:
                ts_reloaded.data = _data
                logger.info(f"Updated data for {ts_code} from {ts_source_code}.")
                count_updated += 1

    logger.info(
        f"Yahoo data update complete: "
        f"{count_total} total, "
        f"{count_updated} updated, "
        f"{count_skipped_no_ticker} skipped (no ticker), "
        f"{count_skipped_empty_data} skipped (empty data)."
    )


def update_fred_data():

    logger.info("Starting Fred data update process.")

    count_total = 0
    count_skipped_no_ticker = 0
    count_skipped_empty_data = 0
    count_updated = 0

    from ix.db.conn import Session

    with Session() as session:
        timeseries_list = (
            session.query(Timeseries).filter(Timeseries.source == "Fred").all()
        )

        # Extract all attributes immediately to avoid detached instance errors
        ts_data_list = []
        for ts in timeseries_list:
            ts_data_list.append(
                {"id": ts.id, "code": ts.code, "source_code": ts.source_code}
            )

        for ts_data in ts_data_list:
            ts_id = ts_data["id"]
            ts_code = ts_data["code"]
            ts_source_code = ts_data["source_code"]

            count_total += 1
            if ts_source_code is None:
                logger.debug(f"Skipping timeseries {ts_code} (no source_ticker).")
                count_skipped_no_ticker += 1
                continue
            ticker, field = str(ts_source_code).split(":")
            logger.debug(f"Fetching data for {ticker} (field: {field}).")
            try:
                _data = get_fred_data(ticker)[field]
            except Exception as e:
                logger.warning(f"Error fetching data for {ts_source_code}: {e}")
                continue

            if _data.empty:
                logger.debug(f"No data returned for {ts_source_code}. Skipping.")
                count_skipped_empty_data += 1
                continue

            # Reload the object and set data within session
            ts_reloaded = (
                session.query(Timeseries).filter(Timeseries.id == ts_id).first()
            )
            if ts_reloaded is not None:
                ts_reloaded.data = _data
                logger.info(f"Updated data for {ts_code} from {ts_source_code}.")
                count_updated += 1

    logger.info(
        f"Fred data update complete: "
        f"{count_total} total, "
        f"{count_updated} updated, "
        f"{count_skipped_no_ticker} skipped (no ticker), "
        f"{count_skipped_empty_data} skipped (empty data)."
    )


def update_naver_data():

    logger.info("Starting Naver data update process.")

    count_total = 0
    count_skipped_no_ticker = 0
    count_skipped_empty_data = 0
    count_updated = 0

    from ix.db.conn import Session

    with Session() as session:
        timeseries_list = (
            session.query(Timeseries).filter(Timeseries.source == "Naver").all()
        )

        # Extract all attributes immediately to avoid detached instance errors
        ts_data_list = []
        for ts in timeseries_list:
            ts_data_list.append(
                {"id": ts.id, "code": ts.code, "source_code": ts.source_code}
            )

        for ts_data in ts_data_list:
            ts_id = ts_data["id"]
            ts_code = ts_data["code"]
            ts_source_code = ts_data["source_code"]

            count_total += 1
            if ts_source_code is None:
                logger.debug(f"Skipping timeseries {ts_code} (no source_ticker).")
                count_skipped_no_ticker += 1
                continue
            ticker, field = str(ts_source_code).split(":")
            logger.debug(f"Fetching data for {ticker} (field: {field}).")
            try:
                _data = get_naver_data(ticker)[field]
            except Exception as e:
                logger.warning(f"Error fetching data for {ts_source_code}: {e}")
                continue

            if _data.empty:
                logger.debug(f"No data returned for {ts_source_code}. Skipping.")
                count_skipped_empty_data += 1
                continue

            # Reload the object and set data within session
            ts_reloaded = (
                session.query(Timeseries).filter(Timeseries.id == ts_id).first()
            )
            if ts_reloaded is not None:
                ts_reloaded.data = _data
                logger.info(f"Updated data for {ts_code} from {ts_source_code}.")
                count_updated += 1

    logger.info(
        f"Fred data update complete: "
        f"{count_total} total, "
        f"{count_updated} updated, "
        f"{count_skipped_no_ticker} skipped (no ticker), "
        f"{count_skipped_empty_data} skipped (empty data)."
    )


def send_data_reports():
    """
    Send both price data and timeseries reports as separate Excel attachments in one email.
    """
    import io
    import pandas as pd

    from ix.misc.email import EmailSender
    from ix.db.conn import Session
    from ix.db.models import Timeseries

    # Prepare both price data and timeseries data in a single loop
    datas = {}
    ts_list = []

    with Session() as session:
        timeseries_list = session.query(Timeseries).all()

        # Extract all necessary attributes while in session
        ts_data_list = []
        for ts in timeseries_list:
            # Extract code and data while in session
            ts_code = ts.code
            # Access timeseries_data directly to avoid detached instance error
            column_data = ts.timeseries_data if hasattr(ts, 'timeseries_data') else {}

            # Convert JSONB dict to pandas Series
            if column_data and len(column_data) > 0:
                data_dict = column_data if isinstance(column_data, dict) else {}
                data = pd.Series(data_dict)
                if not data.empty:
                    # Convert string dates to datetime index
                    data.index = pd.to_datetime(data.index, errors='coerce')
                    data = data.dropna()
            else:
                data = pd.Series(dtype=float)

            ts_data_list.append({
                'code': ts_code,
                'data': data
            })

        # Process the extracted data outside the session
        for ts_data in ts_data_list:
            ts_code = ts_data['code']
            data = ts_data['data']

            # Prepare price data for Equity:PX_LAST codes
            data_clean = data.dropna()
            if not data_clean.empty:
                datas[ts_code] = data_clean.iloc[-1]

            # Prepare timeseries data for all
            data_clean = data.dropna()
            data_clean.name = ts_code
            if not data_clean.empty:
                data_clean.index = pd.to_datetime(data_clean.index)
                data_clean = data_clean.sort_index()
                data_clean.name = ts_code
                ts_list.append(data_clean)

    datas = pd.Series(datas)
    datas.index.name = "Code"
    datas.name = "Value"

    timeseries_data = pd.concat(ts_list, axis=1)
    timeseries_data = timeseries_data.sort_index()
    timeseries_data = timeseries_data.resample("B").last()
    timeseries_data = timeseries_data.iloc[-500:]
    timeseries_data.index.name = "Date"

    # Create Excel buffers for both reports
    price_buffer = io.BytesIO()
    with pd.ExcelWriter(price_buffer, engine="xlsxwriter") as writer:
        datas.to_excel(writer, sheet_name="Data")
    price_buffer.seek(0)

    timeseries_buffer = io.BytesIO()
    with pd.ExcelWriter(timeseries_buffer, engine="xlsxwriter") as writer:
        timeseries_data.to_excel(writer, sheet_name="Data")
    timeseries_buffer.seek(0)

    # Create and send email with both attachments
    email_sender = EmailSender(
        to="26106825@heungkuklife.co.kr, 26107455@heungkuklife.co.kr, hantianfeng@outlook.com",
        subject="[IX] Data Reports",
        content="\n\nPlease find the attached Excel files with price data and timeseries data.\n\nBest regards,\nYour Automation",
    )
    email_sender.attach(file_buffer=price_buffer, filename="Data.xlsx")
    email_sender.attach(file_buffer=timeseries_buffer, filename="Timeseries.xlsx")
    email_sender.send()


def send_price_data():
    """
    Legacy function - now calls send_data_reports.
    Kept for backward compatibility.
    """
    send_data_reports()


def send_timeseries():
    """
    Legacy function - now calls send_data_reports.
    Kept for backward compatibility.
    """
    send_data_reports()


def daily():
    update_yahoo_data()
    update_fred_data()
    update_naver_data()
    # send_price_data()
