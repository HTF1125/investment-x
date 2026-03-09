"""Run the macro outlook pipeline for all targets and display results.

Usage:
    python scripts/run_macro_pipeline.py                  # All default targets
    python scripts/run_macro_pipeline.py "S&P 500"        # Single target
    python scripts/run_macro_pipeline.py --save            # Compute and save to DB
    python scripts/run_macro_pipeline.py --ic-report       # Show full IC report
"""

import os
import sys
import time
import warnings

# Add project root to path to allow 'ix' imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

from ix.core.macro.pipeline import compute_full_pipeline, compute_and_save
from ix.core.macro.rolling_ic import compute_axis_ic_report
from ix.core.macro.indicators import (
    LIQUIDITY_WEIGHTS,
    load_growth_data,
    load_inflation_data,
    load_liquidity_data,
    load_tactical_data,
    load_target_index,
    GROWTH_LOADERS,
    INFLATION_LOADERS,
    LIQUIDITY_LOADERS,
    TACTICAL_LOADERS,
)
from ix.core.macro.engine import normalize_indicator
from ix.core.macro.config import TARGET_INDICES

DEFAULT_TARGETS = ["S&P 500", "KOSPI", "Nasdaq 100", "KOSDAQ"]


def fmt(v, decimals=2):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "  n/a"
    return f"{v:+.{decimals}f}" if v != 0 else f" {v:.{decimals}f}"


def print_header(text):
    print(f"\n{'=' * 70}")
    print(f"  {text}")
    print(f"{'=' * 70}")


def print_section(text):
    print(f"\n--- {text} ---")


def run_target(target_name, save=False, show_ic_report=False):
    print_header(f"{target_name}")
    t0 = time.time()

    if save:
        compute_and_save(target_name)
        results = compute_full_pipeline(target_name)
    else:
        results = compute_full_pipeline(target_name)

    elapsed = time.time() - t0
    print(f"  Computed in {elapsed:.1f}s")

    # Current state
    regime_probs = results["regime_probs"]
    growth = results["growth_composite"]
    inflation = results["inflation_composite"]
    liquidity = results["liquidity_composite"]
    tac = results["tac_score"]
    alloc = results["alloc"]
    alloc_vs = results["alloc_vol_scaled"]
    trend = results.get("trend_signal", pd.Series(dtype=float))
    binary = results.get("binary_alloc", pd.Series(dtype=float))

    print_section("Current State")
    if not regime_probs.empty:
        latest_probs = regime_probs.iloc[-1]
        dominant = latest_probs.idxmax()
        confidence = latest_probs.max()
        print(f"  Regime:     {dominant} ({confidence:.0%} confidence)")
        print(f"  Growth:     {fmt(growth.iloc[-1], 3)}   Inflation: {fmt(inflation.iloc[-1], 3)}")
        print(f"  Liquidity:  {fmt(liquidity.iloc[-1], 3)}   Tactical:  {fmt(tac.iloc[-1], 3)}")
        print(f"  Allocation: {alloc.iloc[-1]:.1%} (raw)  {alloc_vs.iloc[-1]:.1%} (vol-scaled)")
        if not trend.empty:
            trend_label = "Bullish" if trend.iloc[-1] > 0.5 else "Bearish"
            print(f"  Trend:      {trend_label} (40w SMA)")
        if not binary.empty:
            print(f"  Binary:     {binary.iloc[-1]:.0%}")

    # Regime probabilities
    print_section("Regime Probabilities")
    if not regime_probs.empty:
        for regime in regime_probs.columns:
            print(f"  {regime:15s}: {regime_probs[regime].iloc[-1]:.1%}")

    # Adaptive liquidity weights vs fixed
    print_section("Liquidity Weights (Adaptive IC vs Fixed)")
    adaptive = results.get("adaptive_liq_weights", {})
    all_names = sorted(set(list(adaptive.keys()) + list(LIQUIDITY_WEIGHTS.keys())))
    print(f"  {'Indicator':25s}  {'Adaptive':>10s}  {'Fixed':>10s}  {'Change':>10s}")
    for name in sorted(all_names, key=lambda n: abs(adaptive.get(n, 0)), reverse=True):
        aw = adaptive.get(name)
        fw = LIQUIDITY_WEIGHTS.get(name)
        aw_str = f"{aw:+.4f}" if aw else "excluded"
        fw_str = f"{fw:+.4f}" if fw else "excluded"
        if aw and fw:
            diff = f"{aw - fw:+.4f}"
        elif aw:
            diff = "NEW"
        else:
            diff = "DROPPED"
        print(f"  {name:25s}  {aw_str:>10s}  {fw_str:>10s}  {diff:>10s}")

    # IC history (latest values)
    ic_hist = results.get("liq_ic_history")
    if ic_hist is not None and not ic_hist.empty:
        print_section("Liquidity IC (Latest Rolling 2yr Spearman)")
        latest_ic = ic_hist.iloc[-1].dropna().sort_values(key=abs, ascending=False)
        for name, val in latest_ic.items():
            marker = "*" if abs(val) >= 0.03 else " "
            print(f"  {marker} {name:25s}: {val:+.4f}")

    # Vol scaling
    print_section("Volatility Scaling")
    rv = results["realized_vol"]
    sc = results["vol_scalar"]
    if not rv.empty:
        print(f"  Realized vol (26w ann):  {rv.iloc[-1]:.1%}")
        print(f"  Median vol (target):     {rv.median():.1%}")
        print(f"  Vol scalar:              {sc.iloc[-1]:.2f}x")
        print(f"  Allocation adjustment:   {alloc.iloc[-1]:.1%} -> {alloc_vs.iloc[-1]:.1%}")

    # Backtest comparison
    print_section("Backtest Results")
    stats = results["stats_df"]
    st_vs = results["st_volscaled"]
    st_bin = results["st_binary"]

    all_stats = []
    for _, row in stats.iterrows():
        all_stats.append(row.to_dict())
    if not st_vs.empty and len(st_vs) > 1:
        row = st_vs.iloc[1]
        all_stats.append({**row.to_dict(), "Strategy": "Vol-Scaled Strategy"})
    if not st_bin.empty and len(st_bin) > 1:
        row = st_bin.iloc[1]
        all_stats.append({**row.to_dict(), "Strategy": "Binary (90/50/10)"})

    print(f"  {'Strategy':25s}  {'Return':>8s}  {'Vol':>8s}  {'Sharpe':>8s}  {'MaxDD':>8s}  {'IR':>8s}  {'TO':>8s}")
    for s in all_stats:
        print(
            f"  {s['Strategy']:25s}"
            f"  {s.get('Ann Return (%)', 0):7.1f}%"
            f"  {s.get('Ann Vol (%)', 0):7.1f}%"
            f"  {s.get('Sharpe', 0):8.3f}"
            f"  {s.get('Max DD (%)', 0):7.1f}%"
            f"  {s.get('Info Ratio', 0):8.3f}"
            f"  {s.get('Ann Turnover (%)', 0):7.1f}%"
        )

    # Full IC report across all axes
    if show_ic_report:
        target = TARGET_INDICES[target_name]
        target_px = load_target_index(target.ticker, "W")
        print_section(f"Full IC Report — {target_name}")

        axes = [
            ("Growth", load_growth_data, GROWTH_LOADERS),
            ("Inflation", load_inflation_data, INFLATION_LOADERS),
            ("Liquidity", load_liquidity_data, LIQUIDITY_LOADERS),
            ("Tactical", load_tactical_data, TACTICAL_LOADERS),
        ]
        for axis_name, load_fn, loaders in axes:
            raw = load_fn("W")
            normalized = {}
            for name, series in raw.items():
                try:
                    z = normalize_indicator(series, name, loaders, 78)
                    if len(z.dropna()) > 52:
                        normalized[name] = z
                except Exception:
                    pass

            report = compute_axis_ic_report(normalized, target_px, axis_name)
            if report.empty:
                continue
            print(f"\n  [{axis_name.upper()}]")
            print(f"  {'Indicator':25s}  {'Curr IC':>9s}  {'Mean IC':>9s}  {'Std':>7s}  {'%Pos':>6s}  {'N':>5s}")
            for _, row in report.iterrows():
                print(
                    f"  {row['name']:25s}"
                    f"  {row['current_ic']:+9.4f}"
                    f"  {row['mean_ic']:+9.4f}"
                    f"  {row['std_ic']:7.4f}"
                    f"  {row['pct_positive']:5.0f}%"
                    f"  {row['n_obs']:5d}"
                )

    return results


def main():
    args = sys.argv[1:]
    save = "--save" in args
    ic_report = "--ic-report" in args
    args = [a for a in args if not a.startswith("--")]

    targets = args if args else DEFAULT_TARGETS

    if save:
        print("Mode: COMPUTE + SAVE TO DB")
    else:
        print("Mode: COMPUTE ONLY (use --save to persist)")

    all_results = {}
    for target in targets:
        if target not in TARGET_INDICES:
            print(f"Unknown target: {target}. Available: {list(TARGET_INDICES.keys())}")
            continue
        all_results[target] = run_target(target, save=save, show_ic_report=ic_report)

    # Summary table
    if len(all_results) > 1:
        print_header("SUMMARY")
        print(f"  {'Target':20s}  {'Regime':15s}  {'Alloc':>7s}  {'VolScaled':>10s}  {'Sharpe':>8s}  {'VS Sharpe':>10s}  {'Binary':>8s}")
        for name, res in all_results.items():
            rp = res["regime_probs"]
            if rp.empty:
                continue
            regime = rp.iloc[-1].idxmax()
            alloc_val = res["alloc"].iloc[-1]
            vs_val = res["alloc_vol_scaled"].iloc[-1]
            sharpe = 0
            vs_sharpe = 0
            bin_sharpe = 0
            if not res["stats_df"].empty and len(res["stats_df"]) > 1:
                sharpe = res["stats_df"].iloc[1]["Sharpe"]
            if not res["st_volscaled"].empty and len(res["st_volscaled"]) > 1:
                vs_sharpe = res["st_volscaled"].iloc[1]["Sharpe"]
            if not res["st_binary"].empty and len(res["st_binary"]) > 1:
                bin_sharpe = res["st_binary"].iloc[1]["Sharpe"]
            print(
                f"  {name:20s}"
                f"  {regime:15s}"
                f"  {alloc_val:6.1%}"
                f"  {vs_val:9.1%}"
                f"  {sharpe:8.3f}"
                f"  {vs_sharpe:10.3f}"
                f"  {bin_sharpe:8.3f}"
            )

    print(f"\n{'=' * 70}")
    print(f"  Done. {len(all_results)} target(s) computed.")
    if not save:
        print("  Run with --save to persist to DB.")
    print(f"{'=' * 70}\n")


if __name__ == "__main__":
    main()
