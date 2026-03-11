"""
Fetch latest data from Yahoo/Fred/Naver and write to DB.

Usage:
    python -m ix.scripts.fetch_data
    python -m ix.scripts.fetch_data --workers 8
"""

import argparse
import gc
import sys
import time
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd

from ix.misc.crawler import get_fred_data, get_naver_data
from ix.db.models import Timeseries
from ix.db.conn import Session

# ── Config ──────────────────────────────────────────────────────────
MAX_WORKERS_FETCH = 12
COMMIT_BATCH = 50
YAHOO_CHUNK_SIZE = 40  # tickers per yf.download() call
MAX_RETRIES = 3  # retry failed fetches
RETRY_DELAY = 2  # seconds between retries (doubles each time)

# ── Colors ──────────────────────────────────────────────────────────
_DIM = "\033[2m"
_BOLD = "\033[1m"
_GREEN = "\033[32m"
_YELLOW = "\033[33m"
_RED = "\033[31m"
_CYAN = "\033[36m"
_RESET = "\033[0m"

_print_lock = threading.Lock()


def _log(msg):
    with _print_lock:
        print(msg, flush=True)


def _ok(msg):
    _log(f"  {_GREEN}OK{_RESET}  {msg}")


def _warn(msg):
    _log(f"  {_YELLOW}!!{_RESET}  {msg}")


def _fail(msg):
    _log(f"  {_RED}ERR{_RESET} {msg}")


def _info(msg):
    _log(f"  {_DIM}--{_RESET}  {msg}")


def _header(title):
    _log(f"\n{_BOLD}{_CYAN}{'─' * 50}{_RESET}")
    _log(f"{_BOLD}{_CYAN}  {title}{_RESET}")
    _log(f"{_BOLD}{_CYAN}{'─' * 50}{_RESET}")


def _progress_bar(done, total, width=30):
    pct = done / max(total, 1)
    filled = int(width * pct)
    bar = f"{'█' * filled}{'░' * (width - filled)}"
    return f"{bar} {done}/{total}"


# ── Query helpers ───────────────────────────────────────────────────
def _load_ticker_groups(source_name):
    """Load timeseries for a source from DB, grouped by ticker."""
    with Session() as session:
        rows = (
            session.query(Timeseries.id, Timeseries.code, Timeseries.source_code)
            .filter(Timeseries.source == source_name)
            .all()
        )

    ticker_groups = defaultdict(list)
    skipped = 0
    for ts_id, ts_code, source_code in rows:
        if not source_code or ":" not in str(source_code):
            skipped += 1
            continue
        ticker, field = str(source_code).split(":", maxsplit=1)
        ticker_groups[ticker].append((ts_id, ts_code, field))

    return ticker_groups, len(rows), skipped


# ── Yahoo ───────────────────────────────────────────────────────────
YAHOO_FALLBACK_PERIODS = ["max", "10y", "5y", "1y"]


def _fetch_yahoo_chunk(tickers: list, period: str = "max"):
    """Download a chunk of Yahoo tickers. Returns {ticker: DataFrame}."""
    import yfinance as yf

    try:
        use_threads = True if len(tickers) > 1 else False
        raw = yf.download(
            tickers=tickers,
            period=period,
            progress=False,
            actions=True,
            auto_adjust=False,
            threads=use_threads,
            group_by="ticker",
        )
    except Exception as e:
        _fail(f"Yahoo chunk ({len(tickers)} tickers, period={period}): {e}")
        return {}

    fetched = {}
    if len(tickers) == 1:
        if raw is not None and not raw.empty:
            fetched[tickers[0]] = raw
    else:
        for ticker in tickers:
            try:
                df = raw[ticker].dropna(how="all")
                if not df.empty:
                    fetched[ticker] = df
            except (KeyError, TypeError):
                pass

    return fetched


def _fetch_yahoo_single_fallback(ticker: str):
    """Try a single ticker with fallback periods (max → 10y → 5y → 1y)."""
    for period in YAHOO_FALLBACK_PERIODS:
        result = _fetch_yahoo_chunk([ticker], period=period)
        if result:
            if period != "max":
                _info(f"{ticker}: OK with period={period}")
            return result
    return {}


def _fetch_and_update_yahoo():
    """Download Yahoo data in chunks with retry for failed tickers."""
    t0 = time.time()
    ticker_groups, total_series, skipped = _load_ticker_groups("Yahoo")

    all_tickers = list(ticker_groups.keys())
    _info(
        f"{total_series} series -> {len(all_tickers)} unique tickers"
        + (f" ({skipped} skipped)" if skipped else "")
    )

    if not all_tickers:
        return

    # Split into chunks to avoid timeouts
    chunks = [
        all_tickers[i : i + YAHOO_CHUNK_SIZE]
        for i in range(0, len(all_tickers), YAHOO_CHUNK_SIZE)
    ]

    fetched_all = {}
    failed_tickers = []
    done_tickers = 0

    for ci, chunk in enumerate(chunks):
        fetched = _fetch_yahoo_chunk(chunk)
        fetched_all.update(fetched)

        # Track which tickers failed
        missed = [t for t in chunk if t not in fetched]
        done_tickers += len(chunk)
        _log(f"  {_DIM}     {_progress_bar(done_tickers, len(all_tickers))}{_RESET}")

        if missed:
            failed_tickers.extend(missed)

    # Retry failed tickers individually with period fallback
    if failed_tickers:
        _warn(
            f"{len(failed_tickers)} tickers failed batch download, retrying with fallback periods..."
        )
        still_failed = []
        for ticker in failed_tickers:
            result = _fetch_yahoo_single_fallback(ticker)
            if result:
                fetched_all.update(result)
            else:
                still_failed.append(ticker)
        failed_tickers = still_failed

    # Write to DB
    _write_fetched_to_db("Yahoo", ticker_groups, fetched_all)

    # Summary
    n_ok = len(fetched_all)
    n_fail = len(failed_tickers)
    elapsed = time.time() - t0
    if n_fail == 0:
        _ok(f"Yahoo: {n_ok}/{len(all_tickers)} tickers ({elapsed:.0f}s)")
    else:
        _warn(
            f"Yahoo: {n_ok}/{len(all_tickers)} tickers, {n_fail} failed ({elapsed:.0f}s)"
        )
        for t in failed_tickers[:10]:
            _log(f"       {_DIM}{t}{_RESET}")
        if len(failed_tickers) > 10:
            _log(f"       {_DIM}... and {len(failed_tickers) - 10} more{_RESET}")


# ── Fred / Naver ────────────────────────────────────────────────────
def _fetch_with_retry(fetcher, ticker, max_retries=MAX_RETRIES):
    """Fetch a single ticker with retries."""
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            data = fetcher(ticker)
            if data is not None and isinstance(data, pd.DataFrame) and not data.empty:
                return data
            return None
        except Exception as e:
            last_err = e
            if attempt < max_retries:
                time.sleep(RETRY_DELAY * (2 ** (attempt - 1)))
    return None


def _fetch_and_update_source(source_name, fetcher):
    """Fetch all tickers for a source concurrently with retries."""
    t0 = time.time()
    ticker_groups, total_series, skipped = _load_ticker_groups(source_name)

    unique_tickers = list(ticker_groups.keys())
    _info(
        f"{total_series} series -> {len(unique_tickers)} unique tickers"
        + (f" ({skipped} skipped)" if skipped else "")
    )

    if not unique_tickers:
        return

    fetched_data = {}
    failed_tickers = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS_FETCH) as pool:
        futures = {
            pool.submit(_fetch_with_retry, fetcher, t): t for t in unique_tickers
        }
        done = 0
        for future in as_completed(futures):
            done += 1
            ticker = futures[future]
            data = future.result()
            if data is not None:
                fetched_data[ticker] = data
            else:
                failed_tickers.append(ticker)
            # Progress every 25% or at the end
            if done == len(unique_tickers) or (
                len(unique_tickers) > 4 and done % max(1, len(unique_tickers) // 4) == 0
            ):
                _log(f"  {_DIM}     {_progress_bar(done, len(unique_tickers))}{_RESET}")

    _write_fetched_to_db(source_name, ticker_groups, fetched_data)

    n_ok = len(fetched_data)
    n_fail = len(failed_tickers)
    elapsed = time.time() - t0
    if n_fail == 0:
        _ok(f"{source_name}: {n_ok}/{len(unique_tickers)} tickers ({elapsed:.0f}s)")
    else:
        _warn(
            f"{source_name}: {n_ok}/{len(unique_tickers)} tickers, {n_fail} failed ({elapsed:.0f}s)"
        )
        for t in failed_tickers[:10]:
            _log(f"       {_DIM}{t}{_RESET}")
        if len(failed_tickers) > 10:
            _log(f"       {_DIM}... and {len(failed_tickers) - 10} more{_RESET}")


# ── DB write ────────────────────────────────────────────────────────
def _write_fetched_to_db(source_name, ticker_groups, fetched_data):
    """Write fetched data to DB in batches."""
    from ix.db.conn import custom_chart_session

    updated = 0
    errors = 0
    with Session() as session:
        # Prevent Timeseries.data setter from opening a new session for every item
        token = custom_chart_session.set(session)
        try:
            for ticker, items in ticker_groups.items():
                df = fetched_data.get(ticker)
                if df is None:
                    continue
                for ts_id, ts_code, field in items:
                    try:
                        if field in df.columns:
                            series_data = df[field]
                            if series_data is not None and not series_data.empty:
                                ts = session.get(Timeseries, ts_id)
                                if ts:
                                    ts.data = series_data
                                    updated += 1
                    except Exception as e:
                        session.rollback()
                        errors += 1
                        if errors <= 3:
                            _fail(f"DB write {ts_code}: {e}")
                if updated > 0 and updated % COMMIT_BATCH == 0:
                    try:
                        session.commit()
                        session.expunge_all()
                    except Exception as e:
                        session.rollback()
                        errors += 1
                        if errors <= 3:
                            _fail(f"DB batch commit: {e}")
            try:
                session.commit()
            except Exception as e:
                session.rollback()
                _fail(f"DB final commit: {e}")
        finally:
            custom_chart_session.reset(token)

    msg = f"{source_name}: {updated} series written to DB"
    if errors:
        msg += f" ({errors} write errors)"
    _info(msg)


# ── Main ────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Fetch data from Yahoo/Fred/Naver")
    parser.add_argument(
        "--workers", type=int, default=12, help="Concurrent fetch workers"
    )
    args = parser.parse_args()

    global MAX_WORKERS_FETCH
    MAX_WORKERS_FETCH = args.workers

    _log(f"\n{_BOLD}  Investment-X Data Fetch{_RESET}")
    _header("Data Update")
    t_start = time.time()

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_fetch_and_update_yahoo): "Yahoo",
            pool.submit(_fetch_and_update_source, "Fred", get_fred_data): "Fred",
            pool.submit(_fetch_and_update_source, "Naver", get_naver_data): "Naver",
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                future.result()
            except Exception as e:
                _fail(f"{name} crashed: {e}")

    elapsed = time.time() - t_start
    _log(f"\n{_BOLD}{_GREEN}  Done in {elapsed:.0f}s{_RESET}\n")
    gc.collect()


if __name__ == "__main__":
    main()
