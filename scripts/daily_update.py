"""
Daily data update script.
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
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ix.misc.task import (
    update_yahoo_data,
    update_fred_data,
    update_naver_data,
    refresh_all_charts,
)


def progress(current, total, label=""):
    pct = current / max(total, 1) * 100
    print(f"  [{current}/{total}] {pct:5.1f}%  {label}", flush=True)


def run_data_update():
    print("\n[1/3] Updating Yahoo data...")
    t0 = time.time()
    update_yahoo_data(progress_cb=progress)
    print(f"  Done in {time.time() - t0:.1f}s")

    print("\n[2/3] Updating Fred data...")
    t0 = time.time()
    update_fred_data(progress_cb=progress)
    print(f"  Done in {time.time() - t0:.1f}s")

    print("\n[3/3] Updating Naver data...")
    t0 = time.time()
    update_naver_data(progress_cb=progress)
    print(f"  Done in {time.time() - t0:.1f}s")

    gc.collect()


def run_chart_refresh():
    print("\nRefreshing all charts...")
    t0 = time.time()
    refresh_all_charts(progress_cb=progress)
    print(f"  Done in {time.time() - t0:.1f}s")


def main():
    parser = argparse.ArgumentParser(description="Daily data update + chart refresh")
    parser.add_argument("--data-only", action="store_true", help="Only update data (skip charts)")
    parser.add_argument("--charts-only", action="store_true", help="Only refresh charts (skip data)")
    args = parser.parse_args()

    print("=" * 50)
    print("  Daily Update")
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
