"""Backtest engine for the macro allocation strategy.

Returns DataFrames and Series (no Plotly figures) so the results can be
serialized to JSON for the API or rendered in the Streamlit app.
"""

import numpy as np
import pandas as pd

from ix.common.data.transforms import clean_series


def _clean_series(series: pd.Series, name: str) -> pd.Series:
    """Clean + parse datetime index (extends core clean_series)."""
    clean = clean_series(series, name=name)
    if clean.empty:
        return clean
    idx = pd.to_datetime(clean.index, errors="coerce")
    clean = clean.loc[~idx.isna()].copy()
    clean.index = idx[~idx.isna()]
    return clean.sort_index()


def _empty_outputs() -> tuple:
    equity_df = pd.DataFrame(columns=["date", "strategy", "benchmark", "full"])
    weights = pd.Series(dtype=float, name="allocation")
    stats_df = pd.DataFrame(
        columns=[
            "Strategy",
            "Ann Return (%)",
            "Ann Vol (%)",
            "Sharpe",
            "Max DD (%)",
            "Info Ratio",
            "Tracking Err (%)",
            "Ann Turnover (%)",
        ]
    )
    return equity_df, weights, stats_df


def run_backtest(
    alloc: pd.Series,
    target_px: pd.Series,
    target_name: str,
    tc_bps: float = 10.0,
) -> tuple:
    """Run backtest of the three-horizon allocation vs 50% benchmark.

    The strategy uses the allocation signal lagged by 1 week (no look-ahead)
    and subtracts transaction costs proportional to turnover.

    Args:
        alloc: Allocation weight series (0 to 1).
        target_px: Target index price series.
        target_name: Name of the target index (for labels).
        tc_bps: Transaction cost in basis points per unit of turnover.

    Returns:
        Tuple of (equity_df, weights_series, stats_df) where:
          - equity_df: DataFrame with columns [date, strategy, benchmark, full]
                       containing cumulative log returns in percent.
          - weights_series: The lagged allocation weights used.
          - stats_df: Performance statistics table.
    """
    alloc = _clean_series(alloc, "allocation").clip(0.0, 1.0)
    px = _clean_series(target_px, target_name)
    if alloc.empty or len(px) < 2:
        return _empty_outputs()

    # Weekly log returns of target index
    wr = np.log(px).diff().replace([np.inf, -np.inf], np.nan).dropna()
    if wr.empty:
        return _empty_outputs()

    aligned_alloc = alloc.reindex(wr.index).ffill().clip(0.0, 1.0)
    if aligned_alloc.dropna().empty:
        return _empty_outputs()

    # Lag allocation by 1 week to avoid look-ahead bias
    strat_alloc = aligned_alloc.shift(1).dropna()
    common = strat_alloc.index.intersection(wr.index)
    if common.empty:
        return _empty_outputs()

    # Strategy return = allocation weight * index return
    strat_ret = (strat_alloc.loc[common] * wr.loc[common]).dropna()
    if strat_ret.empty:
        return _empty_outputs()
    bench_ret = (0.5 * wr).reindex(strat_ret.index).dropna()
    full_ret = wr.reindex(strat_ret.index).dropna()

    # Transaction costs: proportional to absolute change in allocation
    tc_rate = max(float(tc_bps), 0.0) / 10_000
    turnover = aligned_alloc.diff().abs().fillna(0).reindex(strat_ret.index).fillna(0)
    strat_ret = strat_ret.sub(turnover * tc_rate, fill_value=0.0)

    def _stats(r, label):
        if r.empty:
            return {
                "Strategy": label,
                "Ann Return (%)": 0.0,
                "Ann Vol (%)": 0.0,
                "Sharpe": 0.0,
                "Max DD (%)": 0.0,
            }
        a = r.mean() * 52 * 100
        v = r.std() * np.sqrt(52) * 100
        sr = a / v if v > 0 else 0
        cum = r.cumsum()
        dd = (cum - cum.cummax()).min() * 100 if not cum.empty else 0.0
        return {
            "Strategy": label,
            "Ann Return (%)": a,
            "Ann Vol (%)": v,
            "Sharpe": sr,
            "Max DD (%)": dd,
        }

    stats_rows = []
    for ret, label in [
        (bench_ret, "Benchmark (50/50)"),
        (strat_ret, "Regime Strategy"),
        (full_ret, f"100% {target_name}"),
    ]:
        row = _stats(ret, label)
        if label != "Benchmark (50/50)":
            excess = ret - bench_ret
            te = excess.std() * np.sqrt(52) * 100
            row["Info Ratio"] = (
                excess.mean() * 52 * 100 / te if te > 0 else 0
            )
            row["Tracking Err (%)"] = te
        else:
            row["Info Ratio"] = 0
            row["Tracking Err (%)"] = 0
        row["Ann Turnover (%)"] = (
            turnover.mean() * 52 * 100 if label == "Regime Strategy" else 0
        )
        stats_rows.append(row)

    stats_df = pd.DataFrame(stats_rows)

    # Equity curves as cumulative log returns in percent
    equity_df = pd.DataFrame(
        {
            "date": strat_ret.index,
            "strategy": strat_ret.cumsum().mul(100).values,
            "benchmark": bench_ret.cumsum().mul(100).values,
            "full": full_ret.reindex(strat_ret.index).cumsum().mul(100).values,
        }
    )

    return equity_df, strat_alloc.rename("allocation"), stats_df
