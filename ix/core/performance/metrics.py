# Robert Han

import numpy as np
import pandas as pd

from ix.core.transforms import daily_ffill



def get_period_performances(pxs):

    pxs = daily_ffill(pxs)

    # Determine the as-of date
    asofdate = pxs.index[-1]

    # Define date offsets
    date_offsets = {
        "1D": pd.offsets.BusinessDay(1),
        "1W": pd.DateOffset(days=7),
        "1M": pd.DateOffset(months=1),
        "3M": pd.DateOffset(months=3),
        "6M": pd.DateOffset(months=6),
        "1Y": pd.DateOffset(years=1),
        "3Y": pd.DateOffset(years=3),
        "MTD": pd.offsets.MonthBegin(),
        "YTD": pd.offsets.YearBegin()
    }

    # Calculate reference dates
    dates = {key: asofdate - offset for key, offset in date_offsets.items()}

    # Get as-of-date prices
    asofdate_px = pxs.loc[asofdate]

    # Calculate performance
    performance = pd.DataFrame({
        key: (asofdate_px / pxs.loc[date] - 1) * 100
        for key, date in dates.items()
    }).T

    # Add as-of-date prices as the top row
    performance = pd.concat([
        pd.DataFrame(asofdate_px).T.rename(index={asofdate: 'level'}),
        performance
    ])

    return performance


def to_pri_return(
    px: pd.Series,
    periods: int = 1,
    forward: bool = False,
) -> pd.Series:
    """Calculate price return as a percentage change."""
    pct_return = px.dropna().pct_change(periods=periods)
    if forward:
        pct_return = pct_return.shift(periods=-periods)
    return pct_return


def to_log_return(
    px: pd.Series,
    periods: int = 1,
    forward: bool = False,
) -> pd.Series:
    """Calculate logarithmic price return."""
    pct_return = to_pri_return(px=px, periods=periods, forward=forward)
    log_return = pct_return.apply(np.log1p)
    return log_return


def to_cum_return(
    px: pd.Series,
) -> pd.Series:
    """Calculate cumulative return."""
    px = px.dropna()
    cumulative_return = px.iloc[-1] / px.iloc[0] - 1
    return cumulative_return


def to_ann_return(
    px: pd.Series,
    ann_factor: float = 252.0,
) -> float:
    """Calculate annualized return."""
    ann_log_return = to_log_return(px).mean() * ann_factor
    ann_return = np.exp(ann_log_return) - 1
    return ann_return


def to_ann_volatility(
    px: pd.Series,
    ann_factor: float = 252.0,
) -> float:
    """Calculate annualized volatility."""
    log_returns = to_log_return(px=px)
    std = log_returns.std()
    ann_volatility = std * np.sqrt(ann_factor)
    return ann_volatility


def to_ann_sharpe(
    px: pd.Series,
    risk_free: float = 0.0,
    ann_factor: float = 252.0,
) -> float:
    """Calculate annualized Sharpe ratio."""
    ann_return = to_ann_return(px, ann_factor=ann_factor)
    ann_volatility = to_ann_volatility(px, ann_factor=ann_factor)
    sharpe_ratio = (ann_return - risk_free) / ann_volatility
    return sharpe_ratio


def to_drawdown(px: pd.Series | pd.DataFrame) -> pd.Series | pd.DataFrame:
    """Calculate the drawdown of a price series."""
    if isinstance(px, pd.DataFrame):
        return px.aggregate(to_drawdown)

    cumulative_max = px.expanding().max()
    drawdown = (px / cumulative_max) - 1
    return drawdown


def to_max_drawdown(px: pd.Series) -> float:
    """Calculate the maximum drawdown of a price series."""
    drawdown = to_drawdown(px)
    max_drawdown = abs(drawdown.min())
    return max_drawdown


def to_calmar_ratio(
    px: pd.Series,
    ann_factor: float = 252.0,
) -> float:
    """Calculate the Calmar Ratio of a price series."""
    ann_return = to_ann_return(px, ann_factor=ann_factor)
    drawdown = to_drawdown(px)
    max_drawdown = drawdown.min()

    if max_drawdown == 0:
        return np.nan

    calmar_ratio = ann_return / abs(max_drawdown)
    return calmar_ratio


def to_sortino_ratio(
    px: pd.Series,
    risk_free: float = 0.0,
    ann_factor: float = 252.0,
) -> float:
    """Calculate the Sortino Ratio of a price series."""
    ann_return = to_ann_return(px, ann_factor=ann_factor)
    pct_return = to_pri_return(px=px)
    neg_return = pct_return.apply(lambda x: x if x < 0 else np.nan)
    neg_volatility = neg_return.std() * np.sqrt(ann_factor)
    excess_return = ann_return - risk_free
    sortino_ratio = excess_return / neg_volatility
    return sortino_ratio



def rebase(px: pd.Series) -> pd.Series:
    return px / px.dropna().iloc[0]


# ---------------------------------------------------------------------------
# Returns-based analytics (ported from DWS PerformanceAnalytics)
# These accept return series (R) rather than price series (px).
# ---------------------------------------------------------------------------

def drawdown(R: pd.Series | pd.DataFrame) -> pd.Series | pd.DataFrame:
    if isinstance(R, pd.DataFrame):
        return R.apply(drawdown)
    prices = (1 + R).cumprod()
    previous_peaks = prices.cummax()
    return (prices - previous_peaks) / previous_peaks


def max_drawdown(R: pd.Series | pd.DataFrame) -> float | pd.Series:
    dd = drawdown(R)
    return dd.min()


def rolling_sharpe(
    R: pd.Series | pd.DataFrame,
    window: int = 252,
    rf: float = 0.0,
    ann_factor: float = 252.0,
) -> pd.Series | pd.DataFrame:
    ann_ret = R.rolling(window).mean() * ann_factor
    ann_vol = R.rolling(window).std() * np.sqrt(ann_factor)
    return (ann_ret - rf) / ann_vol


def calmar_ratio(
    R: pd.Series,
    ann_factor: float = 252.0,
) -> float:
    ann_ret = R.mean() * ann_factor
    mdd = drawdown(R).min()
    if mdd == 0:
        return np.nan
    return ann_ret / abs(mdd)


def sortino_ratio(
    R: pd.Series,
    target: float = 0.0,
    ann_factor: float = 252.0,
) -> float:
    excess = R.mean() - target / ann_factor
    downside = R[R < target / ann_factor]
    downside_std = downside.std() * np.sqrt(ann_factor)
    if downside_std == 0:
        return np.nan
    return (excess * ann_factor) / downside_std


def cumulative_contribution(
    R: pd.DataFrame,
    weights: pd.DataFrame,
) -> pd.DataFrame:
    contribution = R.multiply(weights)
    portfolio_return = contribution.sum(axis=1)
    compounding_factor = (1 + portfolio_return).cumprod().shift(1).fillna(1)
    return contribution.multiply(compounding_factor, axis=0).cumsum()


def information_ratio(
    R: pd.Series,
    benchmark: pd.Series,
    ann_factor: float = 252.0,
) -> float:
    active = R - benchmark
    tracking_error = active.std() * np.sqrt(ann_factor)
    if tracking_error == 0:
        return np.nan
    return (active.mean() * ann_factor) / tracking_error


def return_portfolio(
    R: pd.DataFrame,
    weights: pd.Series | pd.DataFrame | None = None,
    rebalance_on: str | None = "months",
) -> pd.Series:
    freq_map = {
        "years": "YE", "quarters": "QE", "months": "ME",
        "weeks": "W", "days": "D",
    }
    n_assets = R.shape[1]

    if weights is None:
        w = np.full(n_assets, 1.0 / n_assets)
    elif isinstance(weights, pd.Series):
        w = weights.values
    else:
        w = weights.iloc[0].values

    if rebalance_on is None or rebalance_on not in freq_map:
        # buy-and-hold: apply initial weights, let them drift
        asset_values = pd.DataFrame(index=R.index, columns=R.columns, dtype=float)
        asset_values.iloc[0] = w
        for i in range(1, len(R)):
            asset_values.iloc[i] = asset_values.iloc[i - 1] * (1 + R.iloc[i])
        port_value = asset_values.sum(axis=1)
        return port_value.pct_change().dropna()

    freq = freq_map[rebalance_on]
    rebal_dates = R.resample(freq).last().index

    asset_values = pd.DataFrame(index=R.index, columns=R.columns, dtype=float)
    asset_values.iloc[0] = w
    for i in range(1, len(R)):
        grown = asset_values.iloc[i - 1] * (1 + R.iloc[i])
        if R.index[i] in rebal_dates:
            total = grown.sum()
            asset_values.iloc[i] = w * total
        else:
            asset_values.iloc[i] = grown
    port_value = asset_values.sum(axis=1)
    return port_value.pct_change().dropna()


# ---------------------------------------------------------------------------
# Extended analytics (from ffn / empyrical)
# ---------------------------------------------------------------------------


def omega_ratio(
    R: pd.Series,
    threshold: float = 0.0,
    ann_factor: float = 252.0,
) -> float:
    """Omega ratio: probability-weighted gain/loss ratio vs threshold.

    Captures the entire return distribution, not just mean/variance.
    Superior to Sharpe for non-normal (skewed, fat-tailed) returns.
    > 1 = gains outweigh losses at threshold. Higher = better.
    """
    daily_threshold = threshold / ann_factor
    excess = R - daily_threshold
    gains = excess[excess > 0].sum()
    losses = abs(excess[excess <= 0].sum())
    if losses == 0:
        return np.nan
    return gains / losses


def stability_of_timeseries(R: pd.Series) -> float:
    """R-squared of cumulative log returns vs time (linear fit).

    Measures how smooth/linear the equity curve is.
    1.0 = perfectly smooth compounding. Near 0 = erratic.
    Quick quality metric for any return stream.
    """
    if R.empty or len(R) < 2:
        return np.nan
    cum_log = np.log1p(R).cumsum()
    cum_log = cum_log.dropna()
    if len(cum_log) < 2:
        return np.nan
    x = np.arange(len(cum_log))
    ss_res = np.sum((cum_log.values - np.polyval(np.polyfit(x, cum_log.values, 1), x)) ** 2)
    ss_tot = np.sum((cum_log.values - cum_log.values.mean()) ** 2)
    if ss_tot == 0:
        return np.nan
    return 1.0 - ss_res / ss_tot


def tail_ratio(R: pd.Series, percentile: float = 95.0) -> float:
    """Ratio of right tail to left tail magnitude.

    tail_ratio = abs(percentile_return) / abs((100-percentile)_return)
    > 1.0 = fatter right tail (favorable asymmetry).
    < 1.0 = fatter left tail (unfavorable, crash-prone).
    Intuitive skewness proxy.
    """
    r = R.dropna()
    if r.empty:
        return np.nan
    right = np.percentile(r, percentile)
    left = np.percentile(r, 100 - percentile)
    if left == 0:
        return np.nan
    return abs(right / left)


def ulcer_index(R: pd.Series) -> float:
    """Ulcer Index: root-mean-square of drawdown series.

    Penalizes both depth AND duration of drawdowns.
    Lower = better. Captures sustained pain that max drawdown misses.
    """
    dd = drawdown(R)
    return np.sqrt(np.mean(dd ** 2))


def ulcer_performance_index(
    R: pd.Series,
    rf: float = 0.0,
    ann_factor: float = 252.0,
) -> float:
    """Martin ratio: annualized excess return / Ulcer Index.

    More sophisticated risk-adjusted measure than Sharpe.
    Penalizes persistent drawdowns rather than all volatility.
    """
    ui = ulcer_index(R)
    if ui == 0:
        return np.nan
    ann_ret = R.mean() * ann_factor
    return (ann_ret - rf) / ui


# ── Capture Ratios ──────────────────────────────────────────────────────────


def capture(
    R: pd.Series,
    benchmark: pd.Series,
    ann_factor: float = 252.0,
) -> float:
    """Total capture ratio: strategy CAGR / benchmark CAGR."""
    aligned = pd.concat([R, benchmark], axis=1).dropna()
    if aligned.empty:
        return np.nan
    r, b = aligned.iloc[:, 0], aligned.iloc[:, 1]
    strat_cagr = r.mean() * ann_factor
    bench_cagr = b.mean() * ann_factor
    if bench_cagr == 0:
        return np.nan
    return strat_cagr / bench_cagr


def up_capture(
    R: pd.Series,
    benchmark: pd.Series,
    ann_factor: float = 252.0,
) -> float:
    """Up-market capture: strategy return / benchmark return during positive benchmark periods.

    100% = matches benchmark upside. >100% = amplifies upside.
    """
    aligned = pd.concat([R, benchmark], axis=1).dropna()
    if aligned.empty:
        return np.nan
    r, b = aligned.iloc[:, 0], aligned.iloc[:, 1]
    up_mask = b > 0
    if up_mask.sum() == 0:
        return np.nan
    return (r[up_mask].mean() / b[up_mask].mean()) * 100


def down_capture(
    R: pd.Series,
    benchmark: pd.Series,
    ann_factor: float = 252.0,
) -> float:
    """Down-market capture: strategy return / benchmark return during negative benchmark periods.

    100% = falls as much as benchmark. <100% = protects on downside (good).
    The most important single metric for downside protection.
    """
    aligned = pd.concat([R, benchmark], axis=1).dropna()
    if aligned.empty:
        return np.nan
    r, b = aligned.iloc[:, 0], aligned.iloc[:, 1]
    down_mask = b < 0
    if down_mask.sum() == 0:
        return np.nan
    return (r[down_mask].mean() / b[down_mask].mean()) * 100


def up_down_capture(
    R: pd.Series,
    benchmark: pd.Series,
    ann_factor: float = 252.0,
) -> float:
    """Up/Down capture ratio. > 1 = asymmetric upside capture (ideal)."""
    uc = up_capture(R, benchmark, ann_factor)
    dc = down_capture(R, benchmark, ann_factor)
    if dc == 0 or np.isnan(dc):
        return np.nan
    return uc / dc


# ── Jensen's Alpha ──────────────────────────────────────────────────────────


def alpha(
    R: pd.Series,
    benchmark: pd.Series,
    rf: float = 0.0,
    ann_factor: float = 252.0,
) -> float:
    """Annualized Jensen's alpha: excess return after adjusting for beta.

    alpha = ann(R - rf) - beta * ann(benchmark - rf)
    Positive = genuine skill. Negative = underperformance vs beta exposure.
    """
    aligned = pd.concat([R, benchmark], axis=1).dropna()
    if aligned.empty or len(aligned) < 2:
        return np.nan
    r, b = aligned.iloc[:, 0], aligned.iloc[:, 1]
    daily_rf = rf / ann_factor
    r_excess = r - daily_rf
    b_excess = b - daily_rf
    cov = r_excess.cov(b_excess)
    var = b_excess.var()
    if var == 0:
        return np.nan
    beta_val = cov / var
    return (r_excess.mean() - beta_val * b_excess.mean()) * ann_factor


# ── Rolling Analytics ───────────────────────────────────────────────────────


def roll_max_drawdown(
    R: pd.Series,
    window: int = 252,
) -> pd.Series:
    """Rolling maximum drawdown over trailing window."""
    def _mdd(x):
        prices = (1 + x).cumprod()
        return (prices / prices.cummax() - 1).min()

    result = R.rolling(window).apply(_mdd, raw=False)
    result.name = "Rolling Max DD"
    return result


def roll_cagr(
    R: pd.Series,
    window: int = 252,
    ann_factor: float = 252.0,
) -> pd.Series:
    """Rolling annualized return (CAGR) over trailing window."""
    result = R.rolling(window).mean() * ann_factor
    result.name = "Rolling CAGR"
    return result


def roll_sortino(
    R: pd.Series,
    window: int = 252,
    target: float = 0.0,
    ann_factor: float = 252.0,
) -> pd.Series:
    """Rolling Sortino ratio over trailing window."""
    def _sortino(x):
        excess = x.mean() - target / ann_factor
        downside = x[x < target / ann_factor]
        ds = downside.std() * np.sqrt(ann_factor)
        if ds == 0:
            return np.nan
        return (excess * ann_factor) / ds

    result = R.rolling(window).apply(_sortino, raw=False)
    result.name = "Rolling Sortino"
    return result


def roll_alpha(
    R: pd.Series,
    benchmark: pd.Series,
    window: int = 252,
    rf: float = 0.0,
    ann_factor: float = 252.0,
) -> pd.Series:
    """Rolling Jensen's alpha over trailing window."""
    aligned = pd.concat({"R": R, "B": benchmark}, axis=1).dropna()
    if aligned.empty:
        return pd.Series(dtype=float, name="Rolling Alpha")
    daily_rf = rf / ann_factor

    def _alpha(idx):
        sub = aligned.loc[idx]
        r_ex = sub["R"] - daily_rf
        b_ex = sub["B"] - daily_rf
        var = b_ex.var()
        if var == 0:
            return np.nan
        beta_val = r_ex.cov(b_ex) / var
        return (r_ex.mean() - beta_val * b_ex.mean()) * ann_factor

    result = pd.Series(index=aligned.index, dtype=float)
    for i in range(window, len(aligned)):
        idx = aligned.index[i - window:i]
        result.iloc[i] = _alpha(idx)
    result.name = "Rolling Alpha"
    return result


# ── Drawdown Details ────────────────────────────────────────────────────────


def drawdown_details(R: pd.Series) -> pd.DataFrame:
    """Decompose drawdown series into individual episodes.

    Returns DataFrame with columns: start, end, recovery, duration,
    max_drawdown, max_drawdown_date for each drawdown episode.
    """
    dd = drawdown(R)
    is_in_dd = dd < 0

    episodes = []
    in_episode = False
    start = None

    for i in range(len(dd)):
        if is_in_dd.iloc[i] and not in_episode:
            in_episode = True
            start = dd.index[i]
        elif not is_in_dd.iloc[i] and in_episode:
            in_episode = False
            end = dd.index[i]
            episode_dd = dd.loc[start:end]
            min_idx = episode_dd.idxmin()
            episodes.append({
                "start": start,
                "end": end,
                "duration": (end - start).days,
                "max_drawdown": episode_dd.min(),
                "max_drawdown_date": min_idx,
            })

    # Handle ongoing drawdown
    if in_episode and start is not None:
        episode_dd = dd.loc[start:]
        min_idx = episode_dd.idxmin()
        episodes.append({
            "start": start,
            "end": dd.index[-1],
            "duration": (dd.index[-1] - start).days,
            "max_drawdown": episode_dd.min(),
            "max_drawdown_date": min_idx,
        })

    if not episodes:
        return pd.DataFrame(columns=["start", "end", "duration", "max_drawdown", "max_drawdown_date"])

    return pd.DataFrame(episodes).sort_values("max_drawdown").reset_index(drop=True)


# ── Aggregate Returns ───────────────────────────────────────────────────────


def aggregate_returns(
    R: pd.Series,
    convert_to: str = "monthly",
) -> pd.Series:
    """Aggregate daily returns to lower frequency with correct compounding.

    convert_to: 'monthly', 'quarterly', 'yearly', 'weekly'
    """
    freq_map = {
        "weekly": "W",
        "monthly": "ME",
        "quarterly": "QE",
        "yearly": "YE",
    }
    freq = freq_map.get(convert_to, convert_to)

    def _compound(x):
        return (1 + x).prod() - 1

    return R.resample(freq).apply(_compound)


# ── Probabilistic Momentum ──────────────────────────────────────────────────


def prob_momentum(
    R1: pd.Series,
    R2: pd.Series,
    window: int = 252,
    n_samples: int = 1000,
) -> float:
    """Probability that R1 outperforms R2 over a random window-length sample.

    Uses bootstrap resampling to estimate probability of outperformance.
    > 0.5 = R1 likely outperforms. < 0.5 = R2 likely outperforms.
    """
    aligned = pd.concat([R1, R2], axis=1).dropna()
    if len(aligned) < window:
        return np.nan
    r1, r2 = aligned.iloc[:, 0].values, aligned.iloc[:, 1].values
    n = len(r1)
    wins = 0
    rng = np.random.default_rng(42)
    for _ in range(n_samples):
        start = rng.integers(0, n - window)
        cum1 = np.prod(1 + r1[start:start + window]) - 1
        cum2 = np.prod(1 + r2[start:start + window]) - 1
        if cum1 > cum2:
            wins += 1
    return wins / n_samples
