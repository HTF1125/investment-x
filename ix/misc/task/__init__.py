from ix.misc.terminal import get_logger
import pandas as pd

from ix.misc.crawler import get_yahoo_data
from ix.misc.crawler import get_fred_data
from ix.misc.crawler import get_naver_data
from ix.db.models import Timeseries
from ix.db.custom.macro import macro_data


logger = get_logger(__name__)


def _update_source_data(source_name, fetcher, progress_cb=None, start_index: int = 0, total_count: int | None = None):
    """Generic update function for a given data source."""
    logger.info("Starting %s data update process.", source_name)

    count_total = 0
    count_skipped_no_ticker = 0
    count_skipped_empty_data = 0
    count_updated = 0

    from ix.db.conn import Session

    with Session() as session:
        timeseries_list = (
            session.query(Timeseries).filter(Timeseries.source == source_name).all()
        )

        ts_data_list = []
        for ts in timeseries_list:
            ts_data_list.append(
                {"id": ts.id, "code": ts.code, "source_code": ts.source_code}
            )

        for idx, ts_data in enumerate(ts_data_list, start=1):
            ts_id = ts_data["id"]
            ts_code = ts_data["code"]
            ts_source_code = ts_data["source_code"]

            count_total += 1
            if progress_cb:
                current = start_index + idx
                total = total_count if total_count is not None else len(ts_data_list)
                progress_cb(current, total, ts_code)
            if ts_source_code is None:
                logger.debug("Skipping timeseries %s (no source_ticker).", ts_code)
                count_skipped_no_ticker += 1
                continue

            ticker, field = str(ts_source_code).split(":", maxsplit=1)

            logger.debug("Fetching data for %s (field: %s).", ticker, field)
            try:
                # Prefer positional ticker to support fetchers with different kwarg names
                # (e.g. get_fred_data(ticker=...)).
                try:
                    fetched = fetcher(ticker)
                except TypeError:
                    # Backward-compatible fallback for wrappers that still use `code=...`.
                    fetched = fetcher(code=ticker)
                _data = fetched[field]
            except Exception as e:
                logger.warning("Error fetching data for %s: %s", ts_source_code, e)
                continue

            if _data.empty:
                logger.debug("No data returned for %s. Skipping.", ts_source_code)
                count_skipped_empty_data += 1
                continue

            ts_reloaded = (
                session.query(Timeseries).filter(Timeseries.id == ts_id).first()
            )
            if ts_reloaded is not None:
                ts_reloaded.data = _data
                logger.info("Updated data for %s from %s.", ts_code, ts_source_code)
                count_updated += 1

    logger.info(
        "%s data update complete: %d total, %d updated, %d skipped (no ticker), %d skipped (empty data).",
        source_name, count_total, count_updated, count_skipped_no_ticker, count_skipped_empty_data,
    )


def update_yahoo_data(progress_cb=None, start_index: int = 0, total_count: int | None = None):
    _update_source_data("Yahoo", get_yahoo_data, progress_cb, start_index, total_count)


def update_fred_data(progress_cb=None, start_index: int = 0, total_count: int | None = None):
    _update_source_data("Fred", get_fred_data, progress_cb, start_index, total_count)


def update_naver_data(progress_cb=None, start_index: int = 0, total_count: int | None = None):
    _update_source_data("Naver", get_naver_data, progress_cb, start_index, total_count)


def send_data_reports():
    """
    Send both price data and timeseries reports as separate Excel attachments in one email.
    """
    import io
    import gc
    import pandas as pd

    from ix.misc.email import EmailSender
    from ix.db.conn import Session
    from ix.db.models import Timeseries

    # Prepare both price data and timeseries data in a single loop
    datas = {}
    ts_list = []

    # Use a separate scope or careful management to avoid keeping objects alive
    with Session() as session:
        # Fetch only metadata first if possible, or just iterate.
        # Loading all Timeseries objects is usually okay (metadata is small),
        # but the relationships (data_record) and large JSONB are the issue.
        timeseries_list = session.query(Timeseries).all()

        for ts in timeseries_list:
            ts_code = ts.code

            # Access the data relationship
            # We assume data is loaded on access if not eager loading
            data_record = ts._get_or_create_data_record(session)
            column_data = data_record.data if data_record and data_record.data else {}

            # Convert JSON dict to pandas Series immediately and release dict memory
            if column_data and len(column_data) > 0:
                data_dict = column_data if isinstance(column_data, dict) else {}
                data = pd.Series(data_dict)

                # Free the large dict from memory as soon as possible
                del column_data

                if not data.empty:
                    # Convert string dates to datetime index
                    data.index = pd.to_datetime(data.index, errors="coerce")
                    data = data.dropna().sort_index()

                    if not data.empty:
                        # 1. Store last price
                        datas[ts_code] = data.iloc[-1]

                        # 2. Store truncated series for history
                        # We limit to last 1000 items to save memory,
                        # which is sufficient for the final report (last 500 business days).
                        data_truncated = data.iloc[-1000:]
                        data_truncated.name = ts_code
                        ts_list.append(data_truncated)

            # Hint to GC that big objects can be freed
            del data_record

    # Force garbage collection to clear any lingering objects from the loop
    gc.collect()

    datas = pd.Series(datas)
    datas.index.name = "Code"
    datas.name = "Value"

    # Load macro data (cached or computed)
    macro_df = macro_data()
    macro_df.index.name = "Date"
    macro_df.name = "Value"

    if ts_list:
        timeseries_data = pd.concat(ts_list, axis=1)
        timeseries_data = timeseries_data.sort_index()
        timeseries_data = timeseries_data.resample("B").last()
        timeseries_data = timeseries_data.iloc[-500:]
        timeseries_data.index.name = "Date"
    else:
        timeseries_data = pd.DataFrame()

    # Create Excel buffers for both reports
    price_buffer = io.BytesIO()
    with pd.ExcelWriter(price_buffer, engine="xlsxwriter") as writer:
        datas.to_excel(writer, sheet_name="Data")
    price_buffer.seek(0)

    timeseries_buffer = io.BytesIO()
    with pd.ExcelWriter(timeseries_buffer, engine="xlsxwriter") as writer:
        timeseries_data.to_excel(writer, sheet_name="Data")
        macro_df.to_excel(writer, sheet_name="Macro")
    timeseries_buffer.seek(0)

    # Release large dataframes
    del ts_list
    del timeseries_data
    del macro_df
    gc.collect()

    # Fetch recipients from database
    recipients = []
    try:
        from ix.db.models.user import User

        # Use a new session for user query to be safe/clean
        with Session() as user_session:
            # Filter for admins only
            admins = (
                user_session.query(User)
                .filter(
                    User.disabled == False,
                    User.role.in_(list(User.ADMIN_ROLES)),
                )
                .all()
            )
            recipients = [u.email for u in admins if u.email]
    except Exception as e:
        logger.error("Error fetching email recipients from database: %s", e)
        return

    if not recipients:
        logger.warning("No recipients found in database.")
        return

    to_str = ", ".join(recipients)

    # Create and send email with both attachments
    email_sender = EmailSender(
        subject="[IX] Data",
        content="\n\nPlease find the attached Excel files with price data and timeseries data.\n\nBest regards,\nYour Automation",
        bcc=to_str,
    )
    email_sender.attach(file_buffer=price_buffer, filename="Data.xlsx")
    email_sender.attach(file_buffer=timeseries_buffer, filename="Timeseries.xlsx")
    email_sender.send()


def daily():
    update_yahoo_data()
    update_fred_data()
    update_naver_data()


def refresh_all_charts(progress_cb=None):
    """Fetches all charts and forces a re-render to update cached figures.

    Args:
        progress_cb: Optional callback(current, total, chart_code) for progress updates.
    """
    from ix.db.conn import Session
    from ix.db.models import Charts
    from ix.api.routers.charts.custom import execute_custom_code, get_clean_figure_json

    with Session() as s:
        charts = s.query(Charts).order_by(Charts.rank.asc()).all()
        total = len(charts)
        logger.info("Found %d charts to refresh.", total)

        for idx, chart in enumerate(charts, start=1):
            try:
                if progress_cb:
                    progress_cb(idx, total, chart.name or chart.id)
                logger.info(
                    "Refreshing [%d/%d] %s (%s)...", idx, total, chart.name or chart.id, chart.category
                )
                fig = execute_custom_code(chart.code)
                chart.figure = get_clean_figure_json(fig)
            except Exception as e:
                logger.error("Failed to refresh %s: %s", chart.name or chart.id, e)

        s.commit()
        logger.info("All charts processed.")


def run_daily_tasks():
    import gc

    logger.info("Starting daily tasks execution (daily update + reports)")
    daily()
    gc.collect()
    refresh_all_charts()
    # send_data_reports()
    logger.info("Daily tasks execution completed")


def run_macro_research():
    """Run the macro research pipeline as a background task."""
    import subprocess
    import sys

    logger.info("Starting macro research pipeline...")
    try:
        result = subprocess.run(
            [sys.executable, "scripts/macro_research.py",
             "--skip-youtube", "--skip-drive", "--skip-telegram",
             "--days", "3"],
            capture_output=True, text=True, timeout=1800,  # 30 min max
            cwd=str(__import__("pathlib").Path(__file__).resolve().parents[3]),
        )
        if result.returncode == 0:
            logger.info("Macro research pipeline completed successfully")
        else:
            logger.warning("Macro research pipeline failed: %s", result.stderr[:500])
    except subprocess.TimeoutExpired:
        logger.error("Macro research pipeline timed out after 30 minutes")
    except Exception as e:
        logger.error("Macro research pipeline error: %s", e)
