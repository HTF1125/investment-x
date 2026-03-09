"""Portfolio attribution: Brinson-Fachler, factor decomposition, multi-period linking."""

from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# Brinson-Fachler Attribution
# ---------------------------------------------------------------------------


def brinson_fachler(
    portfolio_weights: pd.DataFrame,
    benchmark_weights: pd.DataFrame,
    portfolio_returns: pd.DataFrame,
    benchmark_returns: pd.DataFrame,
) -> dict:
    """Single-period Brinson-Fachler attribution decomposition.

    Decomposes active return (portfolio - benchmark) into allocation,
    selection, and interaction effects per asset/sector per period.

    Parameters
    ----------
    portfolio_weights : DataFrame (dates x assets) of portfolio weights.
    benchmark_weights : DataFrame (dates x assets) of benchmark weights.
    portfolio_returns : DataFrame (dates x assets) of per-asset portfolio returns.
    benchmark_returns : DataFrame (dates x assets) of per-asset benchmark returns.

    Returns
    -------
    dict with keys:
      - ``allocation`` : DataFrame (dates x assets) — allocation effect per asset.
      - ``selection`` : DataFrame (dates x assets) — selection effect per asset.
      - ``interaction`` : DataFrame (dates x assets) — interaction effect per asset.
      - ``total`` : DataFrame (dates x assets) — total active per asset.
      - ``summary`` : DataFrame with period-level aggregates and cumulative effects.
    """
    # Align all inputs to common index and columns
    common_dates = (
        portfolio_weights.index
        .intersection(benchmark_weights.index)
        .intersection(portfolio_returns.index)
        .intersection(benchmark_returns.index)
    )
    common_assets = (
        portfolio_weights.columns
        .intersection(benchmark_weights.columns)
        .intersection(portfolio_returns.columns)
        .intersection(benchmark_returns.columns)
    )

    wp = portfolio_weights.reindex(index=common_dates, columns=common_assets).fillna(0.0)
    wb = benchmark_weights.reindex(index=common_dates, columns=common_assets).fillna(0.0)
    rp = portfolio_returns.reindex(index=common_dates, columns=common_assets).fillna(0.0)
    rb = benchmark_returns.reindex(index=common_dates, columns=common_assets).fillna(0.0)

    # Total benchmark return per period
    R_b = (wb * rb).sum(axis=1)

    # Brinson-Fachler decomposition
    allocation = (wp - wb).multiply(rb.subtract(R_b, axis=0))
    selection = wb.multiply(rp - rb)
    interaction = (wp - wb).multiply(rp - rb)
    total = allocation + selection + interaction

    # Summary: aggregate across assets per period
    alloc_total = allocation.sum(axis=1)
    sel_total = selection.sum(axis=1)
    inter_total = interaction.sum(axis=1)
    active_total = total.sum(axis=1)

    summary = pd.DataFrame({
        "allocation": alloc_total,
        "selection": sel_total,
        "interaction": inter_total,
        "active_return": active_total,
        "cum_allocation": (1 + alloc_total).cumprod() - 1,
        "cum_selection": (1 + sel_total).cumprod() - 1,
        "cum_interaction": (1 + inter_total).cumprod() - 1,
        "cum_active_return": (1 + active_total).cumprod() - 1,
    })

    return {
        "allocation": allocation,
        "selection": selection,
        "interaction": interaction,
        "total": total,
        "summary": summary,
    }


def brinson_fachler_summary(
    attribution: dict,
) -> dict:
    """Aggregate Brinson-Fachler results into human-readable summaries.

    Parameters
    ----------
    attribution : Output of ``brinson_fachler()``.

    Returns
    -------
    dict with keys:
      - ``period_breakdown`` : DataFrame — period-by-period allocation/selection/interaction.
      - ``cumulative`` : DataFrame — cumulative contribution of each effect over time.
      - ``per_asset`` : DataFrame — total contribution of each asset to each effect.
    """
    summary = attribution["summary"]

    period_breakdown = summary[["allocation", "selection", "interaction", "active_return"]]

    cumulative = summary[
        ["cum_allocation", "cum_selection", "cum_interaction", "cum_active_return"]
    ].rename(columns=lambda c: c.replace("cum_", ""))

    # Per-asset totals: sum contribution across all periods
    per_asset = pd.DataFrame({
        "allocation": attribution["allocation"].sum(axis=0),
        "selection": attribution["selection"].sum(axis=0),
        "interaction": attribution["interaction"].sum(axis=0),
        "total": attribution["total"].sum(axis=0),
    })

    return {
        "period_breakdown": period_breakdown,
        "cumulative": cumulative,
        "per_asset": per_asset,
    }


# ---------------------------------------------------------------------------
# Multi-Period Attribution (Carino Smoothing)
# ---------------------------------------------------------------------------


def multi_period_attribution(
    attribution: dict,
) -> dict:
    """Link single-period Brinson-Fachler results across time using Carino smoothing.

    Ensures that period-level attribution effects compound correctly to the
    total multi-period active return, resolving the compounding mismatch
    inherent in summing single-period effects.

    Parameters
    ----------
    attribution : Output of ``brinson_fachler()``.

    Returns
    -------
    dict with keys:
      - ``linked_allocation`` : Series — Carino-adjusted cumulative allocation effect.
      - ``linked_selection`` : Series — Carino-adjusted cumulative selection effect.
      - ``linked_interaction`` : Series — Carino-adjusted cumulative interaction effect.
      - ``linked_total`` : float — total linked active return.
      - ``scaling_factors`` : Series — per-period Carino scaling coefficients.
    """
    summary = attribution["summary"]

    alloc = summary["allocation"].values
    sel = summary["selection"].values
    inter = summary["interaction"].values
    active = summary["active_return"].values

    n = len(active)
    if n == 0:
        empty = pd.Series(dtype=float)
        return {
            "linked_allocation": empty,
            "linked_selection": empty,
            "linked_interaction": empty,
            "linked_total": 0.0,
            "scaling_factors": empty,
        }

    # Total compounded active return
    total_active = np.prod(1 + active) - 1

    # Carino smoothing factors
    # k_t = ln(1 + r_t) / r_t  for each period
    # K = ln(1 + R) / R         for the total
    # scaling_t = k_t / K
    # If r_t ~= 0, k_t -> 1 (L'Hopital)
    def _log_ratio(r: float) -> float:
        if abs(r) < 1e-12:
            return 1.0
        return np.log(1 + r) / r

    k_t = np.array([_log_ratio(r) for r in active])
    K = _log_ratio(total_active)

    if abs(K) < 1e-12:
        # If total active return is essentially zero, use equal scaling
        scaling = np.ones(n)
    else:
        scaling = k_t / K

    # Linked effects: scale each period's effect and sum
    linked_alloc = np.cumsum(alloc * scaling)
    linked_sel = np.cumsum(sel * scaling)
    linked_inter = np.cumsum(inter * scaling)

    idx = summary.index

    return {
        "linked_allocation": pd.Series(linked_alloc, index=idx, name="linked_allocation"),
        "linked_selection": pd.Series(linked_sel, index=idx, name="linked_selection"),
        "linked_interaction": pd.Series(linked_inter, index=idx, name="linked_interaction"),
        "linked_total": float(linked_alloc[-1] + linked_sel[-1] + linked_inter[-1]),
        "scaling_factors": pd.Series(scaling, index=idx, name="carino_scaling"),
    }


# ---------------------------------------------------------------------------
# Factor-Based Return Decomposition
# ---------------------------------------------------------------------------


def factor_return_decomposition(
    portfolio_returns: pd.Series,
    factor_returns: pd.DataFrame,
    window: int = 252,
    rf: float = 0.0,
    ann_factor: float = 252.0,
) -> dict:
    """Rolling factor decomposition of portfolio returns (Fama-French style).

    Runs rolling OLS of portfolio excess returns on factor returns to estimate
    time-varying exposures, factor contributions, alpha, and residuals.

    Parameters
    ----------
    portfolio_returns : Series of portfolio returns.
    factor_returns : DataFrame with factor return columns (e.g. Mkt-RF, SMB, HML).
    window : Rolling regression window (default 252 = 1 year).
    rf : Annualized risk-free rate for alpha calculation.
    ann_factor : Annualization factor (252 for daily).

    Returns
    -------
    dict with keys:
      - ``exposures`` : DataFrame of rolling factor betas.
      - ``contributions`` : DataFrame of factor contributions (beta * factor_return).
      - ``alpha`` : Series of rolling annualized alpha (intercept).
      - ``residual`` : Series of unexplained returns.
      - ``r_squared`` : Series of rolling R-squared.
      - ``summary`` : dict of full-sample regression stats.
    """
    # Align inputs
    common_idx = portfolio_returns.dropna().index.intersection(factor_returns.dropna(how="all").index)
    y = portfolio_returns.reindex(common_idx).fillna(0.0)
    X = factor_returns.reindex(common_idx).fillna(0.0)

    daily_rf = rf / ann_factor
    y_excess = y - daily_rf

    n = len(y_excess)
    factors = X.columns.tolist()
    n_factors = len(factors)

    # Rolling OLS with intercept
    exposures_data = {}
    alpha_data = {}
    r_squared_data = {}

    for i in range(window, n):
        y_win = y_excess.iloc[i - window:i].values
        X_win = X.iloc[i - window:i].values

        # Add intercept
        X_aug = np.column_stack([np.ones(window), X_win])

        # Check for degenerate windows
        valid = np.isfinite(y_win) & np.all(np.isfinite(X_aug), axis=1)
        if valid.sum() < n_factors + 2:
            continue

        y_v = y_win[valid]
        X_v = X_aug[valid]

        # OLS: (X'X)^-1 X'y
        try:
            XtX = X_v.T @ X_v
            Xty = X_v.T @ y_v
            betas = np.linalg.solve(XtX, Xty)
        except np.linalg.LinAlgError:
            continue

        date = y_excess.index[i - 1]
        alpha_data[date] = betas[0] * ann_factor  # annualized intercept
        exposures_data[date] = pd.Series(betas[1:], index=factors)

        # R-squared
        y_hat = X_v @ betas
        ss_res = np.sum((y_v - y_hat) ** 2)
        ss_tot = np.sum((y_v - y_v.mean()) ** 2)
        r_squared_data[date] = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    if not exposures_data:
        empty_df = pd.DataFrame(columns=factors)
        empty_s = pd.Series(dtype=float)
        return {
            "exposures": empty_df,
            "contributions": empty_df,
            "alpha": empty_s,
            "residual": y_excess,
            "r_squared": empty_s,
            "summary": {},
        }

    exposures = pd.DataFrame(exposures_data).T
    alpha_series = pd.Series(alpha_data, name="alpha")
    r_squared = pd.Series(r_squared_data, name="r_squared")

    # Contributions: beta * factor_return (on overlapping dates)
    common = exposures.index.intersection(X.index)
    contributions = exposures.reindex(common) * X.reindex(common)

    # Residual: actual return - explained
    explained = contributions.sum(axis=1) + alpha_series.reindex(common) / ann_factor
    residual = y_excess.reindex(common) - explained
    residual.name = "residual"

    # Full-sample regression for summary stats
    summary = _full_sample_regression(y_excess, X, rf=rf, ann_factor=ann_factor)

    return {
        "exposures": exposures,
        "contributions": contributions,
        "alpha": alpha_series,
        "residual": residual,
        "r_squared": r_squared,
        "summary": summary,
    }


def _full_sample_regression(
    y_excess: pd.Series,
    X: pd.DataFrame,
    rf: float = 0.0,
    ann_factor: float = 252.0,
) -> dict:
    """Run full-sample OLS and return coefficient table + diagnostics."""
    y_arr = y_excess.values
    X_arr = X.values
    n = len(y_arr)
    k = X_arr.shape[1]

    valid = np.isfinite(y_arr) & np.all(np.isfinite(X_arr), axis=1)
    y_v = y_arr[valid]
    X_v = np.column_stack([np.ones(valid.sum()), X_arr[valid]])
    n_valid = len(y_v)

    if n_valid < k + 2:
        return {}

    try:
        XtX = X_v.T @ X_v
        Xty = X_v.T @ y_v
        betas = np.linalg.solve(XtX, Xty)
    except np.linalg.LinAlgError:
        return {}

    y_hat = X_v @ betas
    residuals = y_v - y_hat

    # Standard errors
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y_v - y_v.mean()) ** 2)
    r_sq = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    dof = n_valid - k - 1
    if dof <= 0:
        return {"r_squared": r_sq, "coefficients": dict(zip(["alpha"] + X.columns.tolist(), betas))}

    mse = ss_res / dof
    try:
        var_beta = mse * np.linalg.inv(XtX)
    except np.linalg.LinAlgError:
        var_beta = np.full((k + 1, k + 1), np.nan)

    se = np.sqrt(np.diag(var_beta))
    t_stats = betas / se
    p_values = 2 * (1 - stats.t.cdf(np.abs(t_stats), dof))

    names = ["alpha"] + X.columns.tolist()
    coefficients = {n: float(b) for n, b in zip(names, betas)}
    t_stat_dict = {n: float(t) for n, t in zip(names, t_stats)}
    p_value_dict = {n: float(p) for n, p in zip(names, p_values)}
    se_dict = {n: float(s) for n, s in zip(names, se)}

    ann_alpha = float(betas[0] * ann_factor)

    # Variance explained by each factor
    total_var = ss_tot if ss_tot > 0 else 1.0
    factor_var_explained = {}
    for i, fname in enumerate(X.columns):
        factor_contrib = betas[i + 1] * X_v[:, i + 1]
        factor_var_explained[fname] = float(np.var(factor_contrib) / np.var(y_v)) if np.var(y_v) > 0 else 0.0

    return {
        "coefficients": coefficients,
        "t_stats": t_stat_dict,
        "p_values": p_value_dict,
        "std_errors": se_dict,
        "r_squared": float(r_sq),
        "adj_r_squared": float(1.0 - (1.0 - r_sq) * (n_valid - 1) / dof),
        "annualized_alpha": ann_alpha,
        "alpha_t_stat": float(t_stats[0]),
        "alpha_p_value": float(p_values[0]),
        "variance_explained": factor_var_explained,
        "n_observations": n_valid,
    }


def factor_decomposition_report(
    portfolio_returns: pd.Series,
    factor_returns: pd.DataFrame,
    window: int = 252,
    rf: float = 0.0,
    ann_factor: float = 252.0,
) -> dict:
    """Comprehensive factor decomposition report.

    Runs ``factor_return_decomposition`` and adds cumulative contribution
    analysis plus formatted summary statistics.

    Parameters
    ----------
    portfolio_returns : Series of portfolio returns.
    factor_returns : DataFrame of factor returns.
    window : Rolling regression window.
    rf : Annualized risk-free rate.
    ann_factor : Annualization factor.

    Returns
    -------
    dict with keys:
      - ``regression`` : Full-sample regression results (coefficients, t-stats, R-squared).
      - ``annualized_alpha`` : Float — annualized alpha with significance info.
      - ``variance_explained`` : dict — pct of variance explained by each factor.
      - ``cumulative_contributions`` : DataFrame — cumulative factor contributions over time.
      - ``rolling`` : dict — rolling exposures, alpha, r_squared from decomposition.
    """
    decomp = factor_return_decomposition(
        portfolio_returns, factor_returns,
        window=window, rf=rf, ann_factor=ann_factor,
    )

    summary = decomp.get("summary", {})

    # Cumulative factor contributions
    contributions = decomp["contributions"]
    if not contributions.empty:
        cum_contributions = contributions.cumsum()
    else:
        cum_contributions = contributions.copy()

    return {
        "regression": {
            "coefficients": summary.get("coefficients", {}),
            "t_stats": summary.get("t_stats", {}),
            "p_values": summary.get("p_values", {}),
            "r_squared": summary.get("r_squared", 0.0),
            "adj_r_squared": summary.get("adj_r_squared", 0.0),
            "n_observations": summary.get("n_observations", 0),
        },
        "annualized_alpha": {
            "value": summary.get("annualized_alpha", 0.0),
            "t_stat": summary.get("alpha_t_stat", 0.0),
            "p_value": summary.get("alpha_p_value", 1.0),
            "significant_5pct": summary.get("alpha_p_value", 1.0) < 0.05,
        },
        "variance_explained": summary.get("variance_explained", {}),
        "cumulative_contributions": cum_contributions,
        "rolling": {
            "exposures": decomp["exposures"],
            "alpha": decomp["alpha"],
            "r_squared": decomp["r_squared"],
        },
    }
