from ix.misc.terminal import get_logger
from ix.misc import as_date, onemonthbefore, onemonthlater
import pandas as pd
from ix.misc.crawler import get_yahoo_data
from ix.misc.crawler import get_fred_data
from ix.misc.crawler import get_naver_data
from ix.db.models import Timeseries
from ix.db.query import macro_data
from ix.db.conn import Session

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


def run_update_task(source_name, fetch_func, session):
    """
    Generic memory-optimized update function.
    Iterates through items in batches to keep memory usage low.
    """
    logger.info(f"Starting {source_name} data update process.")

    # Query only essential columns (Tuple) to avoid loading heavy 'data' JSON into memory
    items = (
        session.query(Timeseries.id, Timeseries.code, Timeseries.source_code)
        .filter(Timeseries.source == source_name)
        .all()
    )

    count_total = 0
    count_updated = 0
    count_skipped = 0

    # Process one by one, commit/expunge frequently
    for ts_id, ts_code, ts_source_code in items:
        count_total += 1

        if not ts_source_code:
            count_skipped += 1
            continue

        try:
            # Parse ticker/field
            if ":" in str(ts_source_code):
                ticker, field = str(ts_source_code).split(":", maxsplit=1)

                # Fetch Data (Network Call)
                data_dict = fetch_func(ticker)
                _data = data_dict.get(field)

                if _data is not None and not _data.empty:
                    # Update DB - Load ONLY this single object now
                    ts = session.get(Timeseries, ts_id)
                    if ts:
                        ts.data = _data
                        count_updated += 1

        except Exception as e:
            logger.warning(f"Error updating {ts_code}: {e}")

        # Batch Commit & Release Memory every 5 items
        # This prevents the session from growing indefinitely
        if count_total % 5 == 0:
            try:
                session.commit()
                # Expunge objects to free memory from session registry
                session.expunge_all()
            except Exception as e:
                logger.error(f"Commit failed: {e}")
                session.rollback()

    # Final commit
    try:
        session.commit()
    except Exception as e:
        logger.error(f"Final commit failed: {e}")

    logger.info(
        f"{source_name} update complete: {count_updated}/{count_total} updated."
    )


def update_yahoo_data():
    with Session() as session:
        # Wrapper to match fetch signature
        def fetch_yahoo(ticker):
            return get_yahoo_data(code=ticker)

        run_update_task("Yahoo", fetch_yahoo, session)


def update_fred_data():
    with Session() as session:

        def fetch_fred(ticker):
            # Fred crawler returns differently or same?
            # get_fred_data(ticker) returns dict of series usually.
            return get_fred_data(ticker)

        run_update_task("Fred", fetch_fred, session)


def update_naver_data():
    with Session() as session:

        def fetch_naver(ticker):
            return get_naver_data(ticker)

        run_update_task("Naver", fetch_naver, session)


def send_data_reports():
    """
    Send both price data and timeseries reports as separate Excel attachments.
    Memory Optimized: Slices data BEFORE concatenation.
    """
    import io
    from ix.misc.email import EmailSender

    datas = {}
    ts_list = []

    # Define a cutoff date for history to prevent loading decades of daily data into RAM
    # 5 years should be plenty for the report (which asks for last 500 days)
    cutoff_date = pd.Timestamp.now() - pd.DateOffset(years=5)

    with Session() as session:
        # Tuple query for lightweight iteration
        ids = session.query(Timeseries.id).all()

        for (ts_id,) in ids:
            ts = session.get(Timeseries, ts_id)
            if not ts:
                continue

            ts_code = ts.code

            # Efficiently extract data without keeping 'ts' object alive long
            record = ts._get_or_create_data_record(session)
            raw_data = record.data if record else {}

            # Convert
            if raw_data:
                s = pd.Series(raw_data)
                s.index = pd.to_datetime(s.index, errors="coerce")
                s = s.dropna()

                if not s.empty:
                    # 1. Capture Last Price
                    datas[ts_code] = s.iloc[-1]

                    # 2. Add to Timeseries List (Sliced)
                    # Slice EARLY to save memory
                    s_sliced = s[s.index >= cutoff_date]
                    if not s_sliced.empty:
                        s_sliced.name = ts_code
                        ts_list.append(s_sliced)

            # Release memory per item
            session.expunge(ts)
            if record:
                session.expunge(record)

    # 1. Price Snapshot
    datas_series = pd.Series(datas)
    datas_series.index.name = "Code"
    datas_series.name = "Value"

    # 2. Timeseries Matrix
    if ts_list:
        # concat is safer now that pieces are sliced
        timeseries_data = pd.concat(ts_list, axis=1).sort_index()
        timeseries_data = timeseries_data.resample("B").last().iloc[-500:]
        timeseries_data.index.name = "Date"
    else:
        timeseries_data = pd.DataFrame()

    # Macro Data
    macro_df = macro_data()
    macro_df.index.name = "Date"
    macro_df.name = "Value"

    # Create Excel Buffers
    price_buffer = io.BytesIO()
    with pd.ExcelWriter(price_buffer, engine="xlsxwriter") as writer:
        datas_series.to_excel(writer, sheet_name="Data")
    price_buffer.seek(0)

    timeseries_buffer = io.BytesIO()
    with pd.ExcelWriter(timeseries_buffer, engine="xlsxwriter") as writer:
        timeseries_data.to_excel(writer, sheet_name="Data")
        macro_df.to_excel(writer, sheet_name="Macro")
    timeseries_buffer.seek(0)

    # Send Email
    email_sender = EmailSender(
        to="26106825@heungkuklife.co.kr, 26107455@heungkuklife.co.kr, hantianfeng@outlook.com",
        subject="[IX] Data",
        content="\n\nPlease find the attached Excel files with price data and timeseries data.\n\nBest regards,\nYour Automation",
    )
    email_sender.attach(file_buffer=price_buffer, filename="Data.xlsx")
    email_sender.attach(file_buffer=timeseries_buffer, filename="Timeseries.xlsx")
    email_sender.send()

    logger.info("Data reports sent successfully.")


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
