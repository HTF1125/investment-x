# Robert Han

import numpy as np
import pandas as pd



def get_period_performances(pxs):

    pxs = pxs.resample("D").last().ffill()

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
    """
    Calculate price return as a percentage change.

    Parameters:
        px (pd.Series): The price series.
        periods (int): Number of periods to shift for calculation.
        forward (bool): If True, shifts the result forward instead of backward.

    Returns:
        pd.Series: Series containing the calculated percentage price returns.
    """
    pct_return = px.pct_change(periods=periods)
    if forward:
        pct_return = pct_return.shift(periods=-periods)
    return pct_return


def to_log_return(
    px: pd.Series,
    periods: int = 1,
    forward: bool = False,
) -> pd.Series:
    """
    Calculate logarithmic price return.

    Parameters:
        px (pd.Series): The price series.
        periods (int): Number of periods to shift for calculation.
        forward (bool): If True, shifts the result forward instead of backward.

    Returns:
        pd.Series: Series containing the calculated logarithmic price returns.
    """
    pct_return = to_pri_return(px=px, periods=periods, forward=forward)
    log_return = pct_return.apply(np.log1p)
    return log_return


def to_cum_return(
    px: pd.Series,
) -> pd.Series:
    """
    Calculate cumulative return.

    Parameters:
        px (pd.Series): The price series.

    Returns:
        pd.Series: Series containing the calculated cumulative return.
    """
    px = px.dropna()  # Remove NaN values
    cumulative_return = px.iloc[-1] / px.iloc[0] - 1
    return cumulative_return


def to_ann_return(
    px: pd.Series,
    ann_factor: float = 252.0,
) -> float:
    """
    Calculate annualized return.

    Parameters:
        px (pd.Series): The price series.
        ann_factor (float): Annualization factor, default is 252.0 for daily data.

    Returns:
        float: Annualized return as a percentage.
    """
    ann_log_return = to_log_return(px).mean() * ann_factor
    ann_return = np.exp(ann_log_return) - 1
    return ann_return


def to_ann_volatility(
    px: pd.Series,
    ann_factor: float = 252.0,
) -> float:
    """
    Calculate annualized volatility.

    Parameters:
        px (pd.Series): The price series.
        ann_factor (float): Annualization factor, default is 252.0 for daily data.

    Returns:
        float: Annualized volatility.
    """
    log_returns = to_log_return(px=px)
    std = log_returns.std()
    ann_volatility = std * np.sqrt(ann_factor)
    return ann_volatility


def to_ann_sharpe(
    px: pd.Series,
    risk_free: float = 0.0,
    ann_factor: float = 252.0,
) -> float:
    """
    Calculate annualized Sharpe ratio.

    Parameters:
        px (pd.Series): The price series.
        risk_free (float): Risk-free rate, default is 0.0.
        ann_factor (float): Annualization factor, default is 252.0 for daily data.

    Returns:
        float: Annualized Sharpe ratio.
    """
    ann_return = to_ann_return(px, ann_factor=ann_factor)
    ann_volatility = to_ann_volatility(px, ann_factor=ann_factor)
    sharpe_ratio = (ann_return - risk_free) / ann_volatility
    return sharpe_ratio


def to_drawdown(px: pd.Series | pd.DataFrame) -> pd.Series | pd.DataFrame:
    """
    Calculate the drawdown of a price series.

    Drawdown is the peak-to-trough decline during a specific period of investment,
    typically measured from the highest point to the lowest point before a new peak is reached.

    Parameters:
        px (pd.Series): The price series.

    Returns:
        pd.Series: Series containing the drawdown values.
    """
    if isinstance(px, pd.DataFrame):
        return px.aggregate(to_drawdown)

    cumulative_max = px.expanding().max()  # Cumulative maximum up to each point
    drawdown = (px / cumulative_max) - 1  # Calculate drawdown
    return drawdown


def to_max_drawdown(px: pd.Series) -> float:
    """
    Calculate the maximum drawdown of a price series.

    Maximum drawdown is the maximum observed loss from a peak to a trough
    of a portfolio, before a new peak is achieved.

    Parameters:
        px (pd.Series): The price series.

    Returns:
        float: Maximum drawdown as a percentage.
    """
    drawdown = to_drawdown(px)
    max_drawdown = abs(
        drawdown.min()
    )  # Minimum (most negative) drawdown, absolute value
    return max_drawdown


def to_calmar_ratio(
    px: pd.Series,
    ann_factor: float = 252.0,
) -> float:
    """
    Calculate the Calmar Ratio of a price series.

    The Calmar Ratio is defined as the ratio of the annualized return
    to the maximum drawdown.

    Parameters:
        px (pd.Series): The price series.
        ann_factor (float): Annualization factor, default is 252.0 for daily data.

    Returns:
        float: Calmar Ratio.
    """
    ann_return = to_ann_return(px, ann_factor=ann_factor)
    drawdown = to_drawdown(px)
    max_drawdown = drawdown.min()

    # Handling case where max_drawdown is 0 to avoid division by zero
    if max_drawdown == 0:
        return np.nan

    calmar_ratio = ann_return / abs(max_drawdown)
    return calmar_ratio


def to_sortino_ratio(
    px: pd.Series,
    risk_free: float = 0.0,
    ann_factor: float = 252.0,
) -> float:
    """
    Calculate the Sortino Ratio of a price series.

    The Sortino Ratio is defined as the ratio of the excess return
    over the risk-free rate to the downside semi-deviation.

    Parameters:
        px (pd.Series): The price series.
        risk_free (float): Risk-free rate, default is 0.0.
        ann_factor (float): Annualization factor, default is 252.0 for daily data.

    Returns:
        float: Sortino Ratio.
    """
    ann_return = to_ann_return(px, ann_factor=ann_factor)
    pct_return = to_pri_return(px=px)
    neg_return = pct_return.apply(lambda x: x if x < 0 else np.nan)
    neg_volatility = neg_return.std() * np.sqrt(ann_factor)  # Downside semi-deviation
    excess_return = ann_return - risk_free
    sortino_ratio = excess_return / neg_volatility
    return sortino_ratio
