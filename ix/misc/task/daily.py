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
    Memory Optimized:
    - Uses a master index to align data immediately.
    - Stores values as float32 numpy arrays to save memory and avoid Series/Index overhead.
    - Constructs DataFrame directly from dict, bypassing pd.concat alignment.
    """
    import io
    import gc
    import numpy as np
    from ix.misc.email import EmailSender

    datas = {}

    # 1. Setup Master Index (last ~3 years covers the required 500 business days with buffer)
    # Using 'B' (business day) freq might miss data if we just reindex,
    # so we use 'D' (daily) to capture everything, then resample later.
    end_date = pd.Timestamp.now().normalize()
    start_date = end_date - pd.DateOffset(years=3)
    master_index = pd.date_range(start=start_date, end=end_date, freq="D")

    # Storage for aligned data: {code: numpy_array}
    # This avoids storing thousands of Index objects and overhead.
    aligned_data = {}

    with Session() as session:
        # Tuple query for lightweight iteration
        ids = session.query(Timeseries.id, Timeseries.code).all()
        total_count = len(ids)

        for idx, (ts_id, ts_code) in enumerate(ids):
            # Explicitly clear loop variables
            record = None
            raw_data = None
            s = None

            try:
                # Direct query for data record to avoid loading full Timeseries object
                # We need to reflect the model structure. TimeseriesData is joined by id.
                # Since we are optimizing, let's use the relationship via the ts object
                # but detach it quickly, OR use direct query if we imported TimeseriesData.
                # 'Timeseries' model was imported. 'TimeseriesData' is in the same file but
                # might not be imported in daily.py.
                # Let's stick to the existing method ensuring we expunge.

                ts = session.get(Timeseries, ts_id)
                if not ts:
                    continue

                record = ts._get_or_create_data_record(session)
                raw_data = record.data if record else {}

                # Release DB objects immediately
                session.expunge(ts)
                if record:
                    session.expunge(record)

                if not raw_data:
                    continue

                # Convert to Series
                # Note: creating Series from dict automatically handles index
                s = pd.Series(raw_data)

                # Convert index to datetime (handles "YYYY-MM-DD")
                s.index = pd.to_datetime(s.index, errors="coerce")
                s = s.dropna()

                if s.empty:
                    continue

                # Sort index necessary for proper search/reindex
                s = s.sort_index()

                # 1. Capture Last Price
                datas[ts_code] = s.iloc[-1]

                # 2. Slice to cutoff first
                # Slice slightly wider than master index to ensure we have data for filling if needed
                # But here we just want data overlapping with master_index.
                s_sliced = s.loc[start_date:end_date]

                if s_sliced.empty:
                    continue

                # Reindex to master_index (Daily)
                # This fills missing dates with NaN.
                s_aligned = s_sliced.reindex(master_index)

                # Store as float32 numpy array to save memory
                # We drop the index here since we know it aligns with master_index
                aligned_data[ts_code] = s_aligned.values.astype("float32")

            except Exception as e:
                logger.error(f"Error processing {ts_code}: {e}")

            # Frequent GC for large loops
            if idx % 100 == 0:
                gc.collect()

    # 1. Price Snapshot
    datas_series = pd.Series(datas)
    datas_series.index.name = "Code"
    datas_series.name = "Value"

    # 2. Timeseries Matrix
    logger.info("Constructing Timeseries DataFrame...")
    if aligned_data:
        # Create DataFrame from dict of arrays.
        # This is extremely fast and memory efficient compared to concat of Series.
        timeseries_data = pd.DataFrame(aligned_data, index=master_index, copy=False)

        # Resample to Business Days and take last 500
        # 'copy=False' tries to avoid duplicating data
        timeseries_data = timeseries_data.resample("B").last()
        timeseries_data = timeseries_data.iloc[-500:]
        timeseries_data.index.name = "Date"

        # Sort columns for tidiness
        timeseries_data = timeseries_data.sort_index(axis=1)
    else:
        timeseries_data = pd.DataFrame()

    # Clear large intermediate dict
    del aligned_data
    gc.collect()

    # Macro Data
    logger.info("Generating Macro Data...")
    try:
        macro_df = macro_data()
        macro_df.index.name = "Date"
        macro_df.name = "Value"
    except Exception as e:
        logger.error(f"Error generating macro data: {e}")
        macro_df = pd.DataFrame()

    # Create Excel Buffers
    logger.info("Writing to Excel...")
    price_buffer = io.BytesIO()
    with pd.ExcelWriter(price_buffer, engine="xlsxwriter") as writer:
        datas_series.to_excel(writer, sheet_name="Data")
    price_buffer.seek(0)

    # Explicitly clear datas_series
    del datas_series
    gc.collect()

    timeseries_buffer = io.BytesIO()
    with pd.ExcelWriter(timeseries_buffer, engine="xlsxwriter") as writer:
        timeseries_data.to_excel(writer, sheet_name="Data")
        macro_df.to_excel(writer, sheet_name="Macro")
    timeseries_buffer.seek(0)

    del timeseries_data
    del macro_df
    gc.collect()

    # Send Email
    logger.info("Sending Email...")
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
