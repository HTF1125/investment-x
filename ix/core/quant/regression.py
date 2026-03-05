"""OLS regression, rolling beta, multi-factor regression."""

import numpy as np
import pandas as pd
from scipy import stats


def ols_regression(y: pd.Series, X: pd.DataFrame) -> dict:
    """Ordinary least-squares regression (no statsmodels needed).

    Parameters
    ----------
    y : Dependent variable (returns or levels).
    X : Independent variables (DataFrame, one column per factor).

    Returns
    -------
    dict with coefficients, intercept, r_squared, residuals, fitted, p_values.
    """
    combined = pd.concat([y.rename("__y__"), X], axis=1).dropna()
    y_arr = combined["__y__"].values
    X_arr = combined.drop(columns=["__y__"]).values
    n, k = X_arr.shape

    # Add intercept column
    X_aug = np.column_stack([np.ones(n), X_arr])
    beta, residuals_ss, rank, sv = np.linalg.lstsq(X_aug, y_arr, rcond=None)

    fitted = X_aug @ beta
    resid = y_arr - fitted
    ss_res = np.sum(resid ** 2)
    ss_tot = np.sum((y_arr - y_arr.mean()) ** 2)
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # Standard errors & p-values
    dof = n - k - 1
    if dof > 0:
        mse = ss_res / dof
        try:
            cov = mse * np.linalg.inv(X_aug.T @ X_aug)
            se = np.sqrt(np.diag(cov))
            t_stat = beta / se
            p_values = 2 * (1 - stats.t.cdf(np.abs(t_stat), dof))
        except np.linalg.LinAlgError:
            p_values = np.full(k + 1, np.nan)
    else:
        p_values = np.full(k + 1, np.nan)

    return {
        "intercept": float(beta[0]),
        "coefficients": {col: float(beta[i + 1]) for i, col in enumerate(X.columns)},
        "r_squared": float(r_squared),
        "residuals": pd.Series(resid, index=combined.index, name="residuals"),
        "fitted": pd.Series(fitted, index=combined.index, name="fitted"),
        "p_values": {
            "intercept": float(p_values[0]),
            **{col: float(p_values[i + 1]) for i, col in enumerate(X.columns)},
        },
    }


def rolling_beta(
    y: pd.Series,
    x: pd.Series,
    window: int = 60,
) -> pd.Series:
    """Rolling OLS beta (cov/var) between two price series.

    Converts to returns internally.
    """
    ry = y.pct_change().dropna()
    rx = x.pct_change().dropna()
    combined = pd.concat([ry.rename("y"), rx.rename("x")], axis=1).dropna()
    cov = combined["y"].rolling(window).cov(combined["x"])
    var = combined["x"].rolling(window).var()
    beta = cov / var
    beta.name = "rolling_beta"
    return beta


def multi_factor_regression(y: pd.Series, factors: pd.DataFrame) -> dict:
    """Multi-factor regression on returns (prices → returns internally).

    Parameters
    ----------
    y : Price series (dependent).
    factors : DataFrame of price series (one column per factor).

    Returns
    -------
    Same dict as ols_regression, computed on pct-change returns.
    """
    y_ret = y.pct_change().dropna()
    X_ret = factors.pct_change().dropna()
    return ols_regression(y_ret, X_ret)
