"""
Daily data update script — concurrent version.
Fetches latest data from Yahoo/Fred/Naver, refreshes all charts.

Usage:
    python scripts/daily_update.py              # full run (data + charts)
    python scripts/daily_update.py --data-only  # data update only
    python scripts/daily_update.py --charts-only # chart refresh only
"""
import argparse
import gc
import sys
import time
import threading
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from ix.misc.crawler import get_yahoo_data, get_fred_data, get_naver_data
from ix.db.models import Timeseries
from ix.db.conn import Session

_max_workers_fetch = 8
MAX_WORKERS_CHARTS = 4
COMMIT_BATCH = 20

# yfinance uses a global shared._DFS dict that is NOT thread-safe.
# Serialize Yahoo downloads with a lock while keeping Fred/Naver parallel.
_yfinance_lock = threading.Lock()
_print_lock = threading.Lock()


def _log(msg):
    with _print_lock:
        print(msg, flush=True)


def _fetch_and_update_source(source_name, fetcher, lock=None):
    """Fetch all tickers for a source concurrently, deduplicate, write to DB.

    Args:
        lock: Optional threading.Lock to serialize fetcher calls (needed for
              yfinance which uses non-thread-safe global state).
    """
    t0 = time.time()

    # 1. Query all timeseries for this source
    with Session() as session:
        rows = (
            session.query(Timeseries.id, Timeseries.code, Timeseries.source_code)
            .filter(Timeseries.source == source_name)
            .all()
        )

    # 2. Group by ticker to avoid duplicate fetches
    # e.g. "SPY:Close" and "SPY:Volume" share ticker "SPY"
    ticker_groups = defaultdict(list)
    skipped = 0
    for ts_id, ts_code, source_code in rows:
        if not source_code or ":" not in str(source_code):
            skipped += 1
            continue
        ticker, field = str(source_code).split(":", maxsplit=1)
        ticker_groups[ticker].append((ts_id, ts_code, field))

    unique_tickers = list(ticker_groups.keys())
    _log(f"  [{source_name}] {len(rows)} series, {len(unique_tickers)} unique tickers, {skipped} skipped")

    if not unique_tickers:
        return

    # 3. Fetch unique tickers concurrently (or serialized if lock provided)
    fetched_data = {}
    fetch_errors = 0

    def fetch_one(ticker):
        try:
            if lock:
                with lock:
                    return ticker, fetcher(ticker)
            return ticker, fetcher(ticker)
        except Exception:
            return ticker, None

    workers = 1 if lock else _max_workers_fetch
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch_one, t): t for t in unique_tickers}
        done = 0
        for future in as_completed(futures):
            done += 1
            ticker, data = future.result()
            if data is not None and isinstance(data, pd.DataFrame) and not data.empty:
                fetched_data[ticker] = data
            else:
                fetch_errors += 1
            if done % 20 == 0 or done == len(unique_tickers):
                pct = done / len(unique_tickers) * 100
                _log(f"  [{source_name}] fetched {done}/{len(unique_tickers)} ({pct:.0f}%)")

    # 4. Write results to DB (sequential — fast local writes)
    updated = 0
    with Session() as session:
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
                except Exception:
                    pass
            # Batch commit to keep session light
            if updated > 0 and updated % COMMIT_BATCH == 0:
                session.commit()
                session.expunge_all()
        session.commit()

    elapsed = time.time() - t0
    _log(f"  [{source_name}] {updated} updated, {fetch_errors} errors — {elapsed:.1f}s")


def run_data_update():
    """Run all three source updates concurrently."""
    sources = [
        ("Yahoo", lambda t: get_yahoo_data(code=t), _yfinance_lock),
        ("Fred", get_fred_data, None),
        ("Naver", get_naver_data, None),
    ]

    _log("\nUpdating data (Yahoo + Fred + Naver in parallel)...")
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_fetch_and_update_source, name, fn, lock): name
            for name, fn, lock in sources
        }
        for future in as_completed(futures):
            name = futures[future]
            try:
                future.result()
            except Exception as e:
                _log(f"  [{name}] FAILED: {e}")

    _log(f"  All data updated in {time.time() - t0:.1f}s")
    gc.collect()


def run_chart_refresh():
    """Refresh all custom charts sequentially.

    Chart rendering is CPU-bound (Plotly + Python exec) so threading
    doesn't help — it just causes GIL contention and timeout failures.
    """
    from ix.db.models import CustomChart
    from ix.api.routers.custom import execute_custom_code, get_clean_figure_json

    _log("\nRefreshing charts...")
    t0 = time.time()

    with Session() as session:
        charts = session.query(CustomChart).order_by(CustomChart.rank.asc()).all()
        total = len(charts)
        _log(f"  {total} charts to refresh")

        updated = 0
        errors = 0
        for idx, chart in enumerate(charts, start=1):
            try:
                fig = execute_custom_code(chart.code)
                chart.figure = get_clean_figure_json(fig)
                updated += 1
            except Exception as e:
                errors += 1
                _log(f"  FAIL: {chart.name or chart.id} — {e}")
            if idx % 10 == 0 or idx == total:
                pct = idx / max(total, 1) * 100
                _log(f"  rendered {idx}/{total} ({pct:.0f}%)")
            # Batch commit every 10 charts
            if idx % 10 == 0:
                session.commit()
                session.expunge_all()
        session.commit()

    _log(f"  {updated} charts refreshed, {errors} failed — {time.time() - t0:.1f}s")


def main():
    parser = argparse.ArgumentParser(description="Daily data update + chart refresh")
    parser.add_argument("--data-only", action="store_true", help="Only update data (skip charts)")
    parser.add_argument("--charts-only", action="store_true", help="Only refresh charts (skip data)")
    parser.add_argument("--workers", type=int, default=8, help="Concurrent fetch workers per source")
    args = parser.parse_args()

    global _max_workers_fetch
    _max_workers_fetch = args.workers

    print("=" * 50)
    print("  Daily Update (concurrent)")
    print("=" * 50)

    t_start = time.time()

    if not args.charts_only:
        run_data_update()

    if not args.data_only:
        run_chart_refresh()

    elapsed = time.time() - t_start
    print(f"\n{'=' * 50}")
    print(f"  Complete in {elapsed:.0f}s")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
