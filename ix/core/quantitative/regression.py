"""OLS regression, rolling beta, multi-factor regression."""

import numpy as np
import pandas as pd
from scipy import stats


def _clean_series(series: pd.Series, name: str) -> pd.Series:
    clean = pd.to_numeric(series, errors="coerce")
    clean = clean.replace([np.inf, -np.inf], np.nan).dropna()
    clean = clean.sort_index()
    clean.name = name
    return clean


def _clean_frame(frame: pd.DataFrame) -> pd.DataFrame:
    clean = frame.apply(pd.to_numeric, errors="coerce")
    clean = clean.replace([np.inf, -np.inf], np.nan)
    clean = clean.sort_index()
    return clean


def _prepare_regression_inputs(y: pd.Series, X: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    if X is None or X.empty:
        raise ValueError("At least one factor series is required for regression.")

    combined = pd.concat([_clean_series(y, "__y__"), _clean_frame(X)], axis=1).dropna()
    if len(combined) < 2:
        raise ValueError("Need at least 2 overlapping observations for regression.")

    valid_columns = [
        col for col in X.columns if combined[col].nunique(dropna=True) > 1
    ]
    if not valid_columns:
        raise ValueError("All factor series are constant after alignment.")

    dropped_columns = [col for col in X.columns if col not in valid_columns]
    return combined[["__y__", *valid_columns]], dropped_columns


def ols_regression(y: pd.Series, X: pd.DataFrame) -> dict:
    """Ordinary least-squares regression (no statsmodels needed)."""
    combined, dropped_columns = _prepare_regression_inputs(y, X)
    y_arr = combined["__y__"].to_numpy(dtype=float)
    factor_columns = [col for col in combined.columns if col != "__y__"]
    X_arr = combined[factor_columns].to_numpy(dtype=float)
    n, k = X_arr.shape

    X_aug = np.column_stack([np.ones(n), X_arr])
    beta, _residuals_ss, rank, _sv = np.linalg.lstsq(X_aug, y_arr, rcond=None)

    fitted = X_aug @ beta
    resid = y_arr - fitted
    ss_res = float(np.sum(resid**2))
    ss_tot = float(np.sum((y_arr - y_arr.mean()) ** 2))
    r_squared = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    dof = n - k - 1
    p_values = np.full(k + 1, np.nan)
    if dof > 0 and rank == X_aug.shape[1]:
        mse = ss_res / dof
        xtx = X_aug.T @ X_aug
        try:
            cov = mse * np.linalg.inv(xtx)
            se = np.sqrt(np.diag(cov))
            with np.errstate(divide="ignore", invalid="ignore"):
                t_stat = np.divide(
                    beta,
                    se,
                    out=np.full_like(beta, np.nan, dtype=float),
                    where=se > 0,
                )
            p_values = 2 * (1 - stats.t.cdf(np.abs(t_stat), dof))
        except np.linalg.LinAlgError:
            p_values = np.full(k + 1, np.nan)

    cond_number = float(np.linalg.cond(X_aug)) if n > 0 else float("nan")

    return {
        "intercept": float(beta[0]),
        "coefficients": {
            col: float(beta[i + 1]) for i, col in enumerate(factor_columns)
        },
        "r_squared": float(r_squared),
        "residuals": pd.Series(resid, index=combined.index, name="residuals"),
        "fitted": pd.Series(fitted, index=combined.index, name="fitted"),
        "p_values": {
            "intercept": float(p_values[0]),
            **{
                col: float(p_values[i + 1]) for i, col in enumerate(factor_columns)
            },
        },
        "observations": int(n),
        "rank": int(rank),
        "condition_number": cond_number,
        "dropped_factors": dropped_columns,
    }


def rolling_beta(
    y: pd.Series,
    x: pd.Series,
    window: int = 60,
) -> pd.Series:
    """Rolling OLS beta (cov/var) between two price series."""
    window = int(window)
    if window < 2:
        raise ValueError("Rolling beta window must be at least 2.")

    ry = _clean_series(y, "y").pct_change(fill_method=None)
    rx = _clean_series(x, "x").pct_change(fill_method=None)
    combined = pd.concat([ry.rename("y"), rx.rename("x")], axis=1)
    combined = combined.replace([np.inf, -np.inf], np.nan).dropna()
    if combined.empty:
        return pd.Series(dtype=float, name="rolling_beta")

    cov = combined["y"].rolling(window=window, min_periods=window).cov(combined["x"])
    var = combined["x"].rolling(window=window, min_periods=window).var()
    beta = cov.div(var.replace(0, np.nan))
    beta = beta.replace([np.inf, -np.inf], np.nan)
    beta.name = "rolling_beta"
    return beta


def multi_factor_regression(y: pd.Series, factors: pd.DataFrame) -> dict:
    """Multi-factor regression on returns (prices → returns internally)."""
    y_ret = _clean_series(y, "__y__").pct_change(fill_method=None)
    X_ret = _clean_frame(factors).pct_change(fill_method=None)
    y_ret = y_ret.replace([np.inf, -np.inf], np.nan).dropna()
    X_ret = X_ret.replace([np.inf, -np.inf], np.nan).dropna(how="all")
    return ols_regression(y_ret, X_ret)
