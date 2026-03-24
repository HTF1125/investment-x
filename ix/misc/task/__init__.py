from ix.misc.terminal import get_logger
import pandas as pd

from ix.misc.crawler import get_yahoo_data
from ix.misc.crawler import get_fred_data
from ix.misc.crawler import get_naver_data
from ix.db.models import Timeseries
from ix.core.indicators.macro import macro_data


logger = get_logger(__name__)


def _update_source_data(source_name, fetcher, progress_cb=None, start_index: int = 0, total_count: int | None = None):
    """Generic update function for a given data source."""
    logger.info("Starting %s data update process.", source_name)

    count_total = 0
    count_skipped_no_ticker = 0
    count_skipped_empty_data = 0
    count_updated = 0

    from ix.db.conn import Session

    from sqlalchemy.orm import load_only

    with Session() as session:
        timeseries_list = (
            session.query(Timeseries)
            .options(load_only(Timeseries.id, Timeseries.code, Timeseries.source_code))
            .filter(Timeseries.source == source_name)
            .all()
        )

        ts_data_list = [
            {"id": ts.id, "code": ts.code, "source_code": ts.source_code}
            for ts in timeseries_list
        ]

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
    import pandas as pd

    from ix.misc.email import EmailSender
    from ix.db.conn import Session
    from ix.db.models import Timeseries
    from ix.db.query import Series as FetchSeries, MultiSeries
    from sqlalchemy.orm import load_only
    from sqlalchemy import or_
    from concurrent.futures import ThreadPoolExecutor, as_completed

    # Get all timeseries codes, excluding FRED-sourced series
    with Session() as session:
        codes = [
            ts.code for ts in
            session.query(Timeseries)
            .options(load_only(Timeseries.code))
            .filter(or_(Timeseries.source != "Fred", Timeseries.source.is_(None)))
            .all()
        ]

    # Fetch all series in parallel (I/O-bound: DB + web crawlers)
    def _fetch_one(code):
        s = FetchSeries(code)
        if not s.empty:
            return s.iloc[-1], s.iloc[-500:].copy()
        return None, None

    datas = {}
    ts_dict = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_fetch_one, c): c for c in codes}
        for fut in as_completed(futures):
            code = futures[fut]
            try:
                last_val, truncated = fut.result(timeout=30)
                if last_val is not None:
                    datas[code] = last_val
                    ts_dict[code] = truncated
            except Exception:
                logger.warning("Failed to fetch %s for report", code)

    datas = pd.Series(datas)
    datas.index.name = "Code"
    datas.name = "Value"

    # Load macro data (cached or computed)
    macro_df = macro_data()
    macro_df.index.name = "Date"

    if ts_dict:
        timeseries_data = MultiSeries(ts_dict)
        timeseries_data = timeseries_data.resample("B").last().iloc[-500:]
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
