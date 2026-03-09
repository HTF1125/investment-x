"""Covariance, return, and Black-Litterman estimators for portfolio construction."""

from typing import Optional, Union
import numpy as np
import pandas as pd
from sklearn.covariance import (
    EmpiricalCovariance,
    LedoitWolf,
    MinCovDet,
    OAS,
    GraphicalLassoCV,
)
from sklearn.linear_model import LinearRegression, LassoCV


# ---------------------------------------------------------------------------
# Weighting
# ---------------------------------------------------------------------------

def exponential_weight(
    n: int,
    span: Optional[float] = None,
    halflife: Optional[float] = None,
) -> np.ndarray:
    """Generate an array of *n* exponential decay weights (oldest first).

    Exactly one of *span* or *halflife* must be provided.

    Args:
        n: Number of observations.
        span: Decay expressed as span (α = 2 / (span + 1)).
        halflife: Decay expressed as half-life (α = 1 − exp(−ln2 / halflife)).

    Returns:
        1-D ``np.ndarray`` of length *n*, normalised to sum to 1.
    """
    if halflife is not None:
        alpha = 1 - np.exp(-np.log(2) / halflife)
    elif span is not None:
        alpha = 2 / (span + 1)
    else:
        raise ValueError("Provide either `span` or `halflife`.")

    raw = np.array([(1 - alpha) ** i for i in range(n)], dtype=float)
    raw = raw[::-1]  # oldest weight first
    return raw / raw.sum()


# ---------------------------------------------------------------------------
# Covariance estimators  (returns → pd.DataFrame covariance matrix)
# ---------------------------------------------------------------------------

def empirical_cov(
    returns: pd.DataFrame,
    assume_centered: bool = False,
) -> pd.DataFrame:
    """Maximum-likelihood covariance estimator (sklearn ``EmpiricalCovariance``).

    Args:
        returns: T × N DataFrame of asset returns.
        assume_centered: If True, data is assumed to have zero mean.

    Returns:
        N × N covariance matrix as a ``pd.DataFrame``.
    """
    cov = EmpiricalCovariance(assume_centered=assume_centered).fit(returns).covariance_
    return pd.DataFrame(cov, index=returns.columns, columns=returns.columns)


def exponential_cov(
    returns: pd.DataFrame,
    span: int = 180,
) -> pd.DataFrame:
    """Exponentially-weighted moving average (EWMA) covariance matrix.

    Uses ``pandas.DataFrame.ewm`` for efficient computation.

    Args:
        returns: T × N DataFrame of asset returns.
        span: Span parameter for the exponential weighting.

    Returns:
        N × N covariance matrix as a ``pd.DataFrame``.
    """
    demeaned = returns - returns.mean()
    n = len(returns.columns)
    cov = np.empty((n, n))
    for i in range(n):
        for j in range(i, n):
            ewma_val = (demeaned.iloc[:, i] * demeaned.iloc[:, j]).ewm(span=span).mean().iloc[-1]
            cov[i, j] = ewma_val
            cov[j, i] = ewma_val
    return pd.DataFrame(cov, index=returns.columns, columns=returns.columns)


def ledoit_wolf_cov(
    returns: pd.DataFrame,
    assume_centered: bool = False,
) -> pd.DataFrame:
    """Ledoit-Wolf shrinkage covariance estimator.

    Automatically determines the optimal shrinkage coefficient that minimises
    the mean squared error between the estimated and the true covariance matrix.

    Args:
        returns: T × N DataFrame of asset returns.
        assume_centered: If True, data is assumed to have zero mean.

    Returns:
        N × N covariance matrix as a ``pd.DataFrame``.
    """
    cov = LedoitWolf(assume_centered=assume_centered).fit(returns).covariance_
    return pd.DataFrame(cov, index=returns.columns, columns=returns.columns)


def oas_cov(
    returns: pd.DataFrame,
    assume_centered: bool = False,
) -> pd.DataFrame:
    """Oracle Approximating Shrinkage (OAS) covariance estimator.

    Under the assumption that the data are Gaussian, OAS yields a smaller
    mean squared error than the Ledoit-Wolf formula.

    Args:
        returns: T × N DataFrame of asset returns.
        assume_centered: If True, data is assumed to have zero mean.

    Returns:
        N × N covariance matrix as a ``pd.DataFrame``.
    """
    cov = OAS(assume_centered=assume_centered).fit(returns).covariance_
    return pd.DataFrame(cov, index=returns.columns, columns=returns.columns)


def min_cov_determinant(
    returns: pd.DataFrame,
    assume_centered: bool = False,
    support_fraction: Optional[float] = None,
    random_state: Optional[int] = None,
) -> pd.DataFrame:
    """Minimum Covariance Determinant (MCD) — robust covariance estimator.

    Finds the subset of observations whose empirical covariance has the
    smallest determinant, making it resilient to outliers.

    Args:
        returns: T × N DataFrame of asset returns.
        assume_centered: If True, data is assumed to have zero mean.
        support_fraction: Proportion of points included in the MCD estimate.
            ``None`` uses the default ``(n + p + 1) / 2``.
        random_state: Seed for reproducibility.

    Returns:
        N × N covariance matrix as a ``pd.DataFrame``.
    """
    cov = MinCovDet(
        assume_centered=assume_centered,
        support_fraction=support_fraction,
        random_state=random_state,
    ).fit(returns).covariance_
    return pd.DataFrame(cov, index=returns.columns, columns=returns.columns)


def graphical_lasso_cov(
    returns: pd.DataFrame,
    assume_centered: bool = False,
) -> pd.DataFrame:
    """Sparse inverse covariance via cross-validated Graphical Lasso.

    Estimates a sparse precision (inverse covariance) matrix, which is useful
    when the number of features is large relative to the number of samples.

    Args:
        returns: T × N DataFrame of asset returns.
        assume_centered: If True, data is assumed to have zero mean.

    Returns:
        N × N covariance matrix as a ``pd.DataFrame``.
    """
    cov = GraphicalLassoCV(assume_centered=assume_centered).fit(returns).covariance_
    return pd.DataFrame(cov, index=returns.columns, columns=returns.columns)


# ---------------------------------------------------------------------------
# Return estimators
# ---------------------------------------------------------------------------

def empirical_mu(returns: pd.DataFrame) -> pd.Series:
    """Mean (arithmetic) expected return for each asset.

    Args:
        returns: T × N DataFrame of asset returns.

    Returns:
        Series of expected returns indexed by asset name.
    """
    return returns.mean()


def exponential_mu(
    returns: pd.DataFrame,
    span: int = 252,
) -> pd.Series:
    """Exponentially-weighted mean return for each asset.

    More recent observations receive higher weight, which can better capture
    regime changes in expected returns.

    Args:
        returns: T × N DataFrame of asset returns.
        span: Span parameter for the exponential weighting.

    Returns:
        Series of expected returns indexed by asset name.
    """
    return returns.ewm(span=span).mean().iloc[-1]


# ---------------------------------------------------------------------------
# Rolling regression
# ---------------------------------------------------------------------------

def rolling_regression(
    y: pd.Series,
    X: pd.DataFrame,
    window: int = 252,
    model: str = "linear",
) -> pd.DataFrame:
    """Rolling factor regression returning time-varying betas.

    At each step the model is fit on the trailing *window* of observations.

    Args:
        y: Dependent variable (e.g. asset returns), T × 1.
        X: Independent variables (e.g. factor returns), T × K.
        window: Lookback window in observations.
        model: ``'linear'`` for OLS or ``'lasso'`` for LassoCV.

    Returns:
        DataFrame of shape (T − window + 1) × (K + 1) with columns for each
        factor beta plus ``'intercept'``.
    """
    if window < 2:
        raise ValueError("Rolling regression window must be >= 2.")

    # Align indices
    combined = pd.concat([y.rename("__y__"), X], axis=1).dropna()
    if len(combined) < window:
        raise ValueError(
            f"Not enough overlapping observations ({len(combined)}) for window={window}."
        )

    factor_cols = [c for c in combined.columns if c != "__y__"]
    results: dict[pd.Timestamp, dict] = {}

    for end in range(window, len(combined) + 1):
        chunk = combined.iloc[end - window : end]
        y_arr = chunk["__y__"].to_numpy(dtype=float)
        X_arr = chunk[factor_cols].to_numpy(dtype=float)

        if model == "linear":
            reg = LinearRegression(fit_intercept=True)
        elif model == "lasso":
            reg = LassoCV(fit_intercept=True, cv=min(5, window // 2))
        else:
            raise ValueError(f"Unsupported model: {model!r}. Use 'linear' or 'lasso'.")

        reg.fit(X_arr, y_arr)

        row = {col: float(reg.coef_[i]) for i, col in enumerate(factor_cols)}
        row["intercept"] = float(reg.intercept_)
        row["r_squared"] = float(reg.score(X_arr, y_arr))
        results[chunk.index[-1]] = row

    return pd.DataFrame.from_dict(results, orient="index")


# ---------------------------------------------------------------------------
# Black-Litterman
# ---------------------------------------------------------------------------

def black_litterman(
    mu: Union[pd.Series, np.ndarray],
    cov: Union[pd.DataFrame, np.ndarray],
    views_P: np.ndarray,
    views_Q: np.ndarray,
    tau: float = 0.05,
    omega: Optional[np.ndarray] = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Black-Litterman posterior expected returns and covariance.

    Combines a prior equilibrium return vector with investor views to produce
    a posterior estimate.

    Args:
        mu: N-length prior expected return vector (e.g. CAPM implied returns).
        cov: N × N prior covariance matrix.
        views_P: K × N pick matrix encoding which assets each view references.
        views_Q: K-length vector of view returns.
        tau: Scalar indicating uncertainty in the prior (typically 0.01–0.10).
        omega: K × K diagonal matrix of view uncertainty. If ``None``, computed
            as ``diag(P @ (τΣ) @ P')``, the He-Litterman default.

    Returns:
        Tuple of (posterior_mu, posterior_cov).
        - posterior_mu: N-length array of adjusted expected returns.
        - posterior_cov: N × N posterior covariance matrix.
    """
    mu_arr = np.asarray(mu, dtype=float)
    cov_arr = np.asarray(cov, dtype=float)
    P = np.asarray(views_P, dtype=float)
    Q = np.asarray(views_Q, dtype=float)

    scaled_cov = tau * cov_arr

    if omega is None:
        omega = np.diag(np.diag(P @ scaled_cov @ P.T))

    # Posterior expected return:
    #   μ_post = μ_prior + τΣ Pᵀ (P τΣ Pᵀ + Ω)⁻¹ (Q − P μ_prior)
    A = P @ scaled_cov @ P.T + omega
    posterior_mu = mu_arr + scaled_cov @ P.T @ np.linalg.solve(A, Q - P @ mu_arr)

    # Posterior covariance:
    #   Σ_post = Σ + τΣ − τΣ Pᵀ (P τΣ Pᵀ + Ω)⁻¹ P τΣ
    prec_p = scaled_cov @ P.T
    posterior_cov = cov_arr + scaled_cov - prec_p @ np.linalg.solve(A, prec_p.T)

    return posterior_mu, posterior_cov
