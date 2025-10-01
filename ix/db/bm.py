import numpy as np
import pandas as pd
from ix.db.query import Series
from ix.misc.date import today


def ConstantReturnBenchmark(
    annual_return: float = 0.01, start: str = "2000-1-1", end: str | None = None
):
    if end is None:
        end = today().strftime("%Y-%m-%d")
    # Generate all calendar days
    dates = pd.date_range(start=start, end=end, freq="D")
    n_days = len(dates)
    # Convert annual return to daily compounded return (365-day year)
    daily_return = (1 + annual_return) ** (1 / 365) - 1
    # Cumulative return path
    cumulative_returns = np.cumprod(np.full(n_days, 1 + daily_return))
    # Scale by initial value
    benchmark_series = pd.Series(
        data=100 * cumulative_returns, index=dates, name="Benchmark"
    )
    return benchmark_series


def MezzAlpha():
    d = ConstantReturnBenchmark(0.02).pct_change().mul(0.70)
    b = (
        Series("KOSPI Index:PX_LAST")
        .resample("D")
        .last()
        .ffill()
        .pct_change()
        .mul(0.30)
    )
    x = (d + b).add(1).cumprod()
    x.name = "MezzAlpha"
    return x.dropna()
