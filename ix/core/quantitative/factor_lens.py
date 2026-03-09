"""Residualization-based factor decomposition.

Implements the Two Sigma / DWS-style Factor Lens approach: builds orthogonal
factor returns by sequentially regressing out systematic exposures using
rolling regressions. Each derived factor captures marginal risk after removing
overlap with previously-defined factors.

All functions accept pre-loaded DataFrames — no data fetching or
hardcoded tickers.
"""

import warnings
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Lasso, LassoCV


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _align_index(*frames: pd.DataFrame | pd.Series) -> pd.DatetimeIndex:
    """Return the common DatetimeIndex across all inputs."""
    idx = frames[0].index
    for f in frames[1:]:
        idx = idx.intersection(f.index)
    return idx


def _pct_change(series: pd.Series | pd.DataFrame) -> pd.Series | pd.DataFrame:
    """Simple percent-change with NaN fill for the first row."""
    return series.pct_change().fillna(0.0)


def _exponential_weights(
    length: int,
    halflife: Optional[int] = None,
    span: Optional[float] = None,
) -> Optional[np.ndarray]:
    """Exponential decay sample weights (most recent = highest weight).

    Returns None if neither halflife nor span is provided.
    """
    if halflife is not None:
        alpha = 1.0 - np.exp(-np.log(2) / halflife)
    elif span is not None:
        alpha = 2.0 / (span + 1.0)
    else:
        return None
    weights = np.array([(1.0 - alpha) ** i for i in range(length)])[::-1]
    return weights


# ---------------------------------------------------------------------------
# Standalone helper functions
# ---------------------------------------------------------------------------

def rolling_factor_regression(
    y: pd.Series,
    X: pd.DataFrame,
    window: int = 252,
    model: str = "ols",
    fit_intercept: bool = False,
    halflife: Optional[int] = None,
) -> pd.DataFrame:
    """Rolling regression of *y* on *X*, returning beta time-series.

    Parameters
    ----------
    y : Dependent variable (return series).
    X : Independent variables (factor return series).
    window : Rolling window size (observations).
    model : ``'ols'`` or ``'lasso'`` (LassoCV with automatic alpha selection).
    fit_intercept : Whether to fit an intercept term.
    halflife : If provided, apply exponential weighting within each window.

    Returns
    -------
    DataFrame of rolling betas, indexed by date, one column per factor.
    """
    idx = _align_index(y, X)
    y = y.reindex(idx)
    X = X.reindex(idx)

    if model == "ols":
        regressor_cls = lambda: LinearRegression(fit_intercept=fit_intercept)
    elif model == "lasso":
        regressor_cls = lambda: LassoCV(fit_intercept=fit_intercept, cv=5)
    else:
        raise ValueError(f"Unsupported model '{model}'. Use 'ols' or 'lasso'.")

    results: dict[pd.Timestamp, pd.Series] = {}
    y_arr = y.values
    X_arr = X.values

    for i in range(window, len(y_arr) + 1):
        y_win = y_arr[i - window:i]
        X_win = X_arr[i - window:i]

        # Skip windows with NaN
        mask = np.isfinite(y_win) & np.all(np.isfinite(X_win), axis=1)
        if mask.sum() < max(10, X.shape[1] + 1):
            continue

        y_w = y_win[mask]
        X_w = X_win[mask]

        sample_weight = _exponential_weights(len(y_w), halflife=halflife)

        reg = regressor_cls()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            reg.fit(X_w, y_w, sample_weight=sample_weight)

        results[y.index[i - 1]] = pd.Series(reg.coef_, index=X.columns)

    if not results:
        return pd.DataFrame(columns=X.columns)
    return pd.DataFrame(results).T


def factor_attribution(
    returns: pd.Series,
    factor_returns: pd.DataFrame,
    window: int = 252,
    smoothing: int = 5,
) -> dict:
    """Quick factor attribution — returns contribution breakdown.

    Parameters
    ----------
    returns : Asset/portfolio return series.
    factor_returns : Factor return series (columns = factors).
    window : Rolling regression window.
    smoothing : Smoothing window applied to rolling betas.

    Returns
    -------
    dict with keys:
      - ``exposures`` : DataFrame of rolling betas
      - ``contributions`` : DataFrame of factor return contributions
      - ``residual`` : Series of unexplained returns
      - ``r_squared`` : float, full-sample R-squared
    """
    idx = _align_index(returns, factor_returns)
    y = returns.reindex(idx)
    X = factor_returns.reindex(idx)

    betas = rolling_factor_regression(y, X, window=window)
    if betas.empty:
        return {
            "exposures": betas,
            "contributions": pd.DataFrame(columns=X.columns),
            "residual": y,
            "r_squared": 0.0,
        }

    if smoothing and smoothing > 1:
        betas = betas.rolling(window=smoothing, min_periods=1).mean()

    # Align betas and factor returns
    common = _align_index(betas, X)
    betas_a = betas.reindex(common)
    X_a = X.reindex(common)
    y_a = y.reindex(common)

    contributions = betas_a * X_a
    explained = contributions.sum(axis=1)
    residual = y_a - explained

    # Full-sample R-squared
    ss_res = (residual ** 2).sum()
    ss_tot = ((y_a - y_a.mean()) ** 2).sum()
    r_sq = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return {
        "exposures": betas,
        "contributions": contributions,
        "residual": residual,
        "r_squared": float(r_sq),
    }


def excess_performance(
    returns: pd.Series | pd.DataFrame,
    benchmark: pd.Series,
) -> pd.Series | pd.DataFrame:
    """Compute excess return series (cumulative).

    Both inputs should be *price-level* (cumulative) series.
    Returns a cumulative excess performance index starting at 1.
    """
    if isinstance(returns, pd.Series):
        returns = returns.to_frame()
        squeeze = True
    else:
        squeeze = False

    idx = _align_index(returns, benchmark)
    r = returns.reindex(idx)
    b = benchmark.reindex(idx)

    ret_r = _pct_change(r)
    ret_b = _pct_change(b)

    excess = ret_r.subtract(ret_b, axis=0)
    result = excess.add(1).cumprod()

    if squeeze:
        return result.squeeze()
    return result


def risk_weighted_performance(
    prices: pd.DataFrame,
    window: int = 252,
) -> pd.Series:
    """Inverse-volatility weighted composite return series.

    Weights each column by its inverse rolling volatility, then compounds
    the weighted returns into a single performance index.
    """
    rets = _pct_change(prices)
    vol = rets.rolling(window=window).std().dropna(thresh=2, axis=0)
    inv_vol = 1.0 / vol.replace(0, np.nan)
    weight = inv_vol.div(inv_vol.sum(axis=1), axis=0)

    start = weight.index[0]
    weighted_ret = rets.loc[start:].multiply(weight).sum(axis=1)
    return weighted_ret.add(1).cumprod()


# ---------------------------------------------------------------------------
# FactorLens class
# ---------------------------------------------------------------------------

class FactorLens:
    """Residualization-based factor decomposition.

    Decomposes portfolio/asset returns into orthogonal factor contributions
    using rolling regression and sequential residualization.

    The approach follows Two Sigma's Factor Lens methodology:

    1. **Rates** and **Equity** are treated as observable base factors.
    2. Additional factors (credit, commodity, EM, etc.) are *residualized*
       against previously-defined factors so each captures only marginal,
       orthogonal risk.
    3. Rolling regressions (default 756 days / 3 years) with optional
       beta smoothing keep exposures adaptive.

    Parameters
    ----------
    returns : DataFrame of asset/portfolio return series (columns = assets).
        These are the *price-level* series to be decomposed.
    factor_returns : DataFrame of factor *price-level* series (columns = factors).
        Already-orthogonalized factor performance indices.
    window : Rolling regression window for exposure estimation.
    smoothing : Smoothing window applied to rolling betas to reduce noise.
    """

    def __init__(
        self,
        returns: pd.DataFrame,
        factor_returns: pd.DataFrame,
        window: int = 756,
        smoothing: int = 5,
    ):
        if isinstance(returns, pd.Series):
            returns = returns.to_frame()
        self._returns = returns
        self._factor_returns = factor_returns
        self._window = window
        self._smoothing = smoothing

        # Lazily computed
        self._betas: Optional[dict[str, pd.DataFrame]] = None
        self._contribs: Optional[dict[str, pd.DataFrame]] = None
        self._residuals: Optional[dict[str, pd.Series]] = None

    # ------------------------------------------------------------------
    # Core computation
    # ------------------------------------------------------------------

    def rolling_exposure(
        self,
        y: pd.Series,
        X: pd.DataFrame,
        window: Optional[int] = None,
    ) -> pd.DataFrame:
        """Compute rolling beta exposures of *y* to factors *X*.

        Parameters
        ----------
        y : Dependent return series.
        X : Independent factor return series.
        window : Override instance window if provided.

        Returns
        -------
        DataFrame of rolling betas (dates x factors).
        """
        w = window or self._window
        betas = rolling_factor_regression(y, X, window=w)
        if self._smoothing and self._smoothing > 1 and not betas.empty:
            betas = betas.rolling(window=self._smoothing, min_periods=1).mean()
        return betas

    def residualize(
        self,
        prices: pd.Series,
        factor_prices: pd.DataFrame,
        window: Optional[int] = None,
    ) -> pd.Series:
        """Remove systematic factor exposure from a price series.

        Computes rolling betas of *prices* against *factor_prices*, builds the
        factor-implied performance, then returns the excess (residual)
        performance.

        Parameters
        ----------
        prices : Price-level series to residualize.
        factor_prices : Factor price-level series to regress against.
        window : Override instance window.

        Returns
        -------
        Series — residualized cumulative performance.
        """
        idx = _align_index(prices, factor_prices)
        prices = prices.reindex(idx)
        factor_prices = factor_prices.reindex(idx)

        ret_y = _pct_change(prices)
        ret_x = _pct_change(factor_prices)

        w = window or self._window
        betas = rolling_factor_regression(ret_y, ret_x, window=w)
        if betas.empty:
            return prices / prices.iloc[0]

        if self._smoothing and self._smoothing > 1:
            betas = betas.rolling(window=self._smoothing, min_periods=1).mean()

        # Factor-implied performance
        common = _align_index(betas, factor_prices)
        betas_a = betas.reindex(common)
        fp_a = factor_prices.reindex(common)
        fp_ret = _pct_change(fp_a)
        implied_ret = (betas_a * fp_ret).sum(axis=1)
        implied_perf = implied_ret.add(1).cumprod()

        # Excess over implied
        prices_a = prices.reindex(common)
        return excess_performance(prices_a, implied_perf)

    def decompose(self) -> dict:
        """Full factor decomposition for every asset in ``self._returns``.

        For each asset column, computes rolling exposures to all factors,
        factor return contributions, and the residual (alpha) component.

        Returns
        -------
        dict with keys:
          - ``exposures`` : dict[asset_name, DataFrame of rolling betas]
          - ``contributions`` : dict[asset_name, DataFrame of factor contributions]
          - ``residual`` : dict[asset_name, Series of residual returns]
          - ``r_squared`` : dict[asset_name, float]
        """
        ret_y = _pct_change(self._returns)
        ret_x = _pct_change(self._factor_returns)

        exposures = {}
        contributions = {}
        residuals = {}
        r_squared = {}

        for col in self._returns.columns:
            result = factor_attribution(
                ret_y[col], ret_x,
                window=self._window,
                smoothing=self._smoothing,
            )
            exposures[col] = result["exposures"]
            contributions[col] = result["contributions"]
            residuals[col] = result["residual"]
            r_squared[col] = result["r_squared"]

        self._betas = exposures
        self._contribs = contributions
        self._residuals = residuals

        return {
            "exposures": exposures,
            "contributions": contributions,
            "residual": residuals,
            "r_squared": r_squared,
        }

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def exposures(self) -> pd.DataFrame:
        """Current factor exposures (latest betas) for each asset.

        Returns a DataFrame with assets as rows, factors as columns,
        containing the most recent rolling beta estimate.
        """
        if self._betas is None:
            self.decompose()

        rows = {}
        for asset, beta_df in self._betas.items():
            if not beta_df.empty:
                rows[asset] = beta_df.iloc[-1]
        if not rows:
            return pd.DataFrame()
        return pd.DataFrame(rows).T

    @property
    def contributions(self) -> pd.DataFrame:
        """Factor return contributions over time (first asset if multiple).

        If the lens was built for a single asset, returns its contribution
        DataFrame directly. For multiple assets, returns the first.
        """
        if self._contribs is None:
            self.decompose()

        first_key = next(iter(self._contribs))
        return self._contribs[first_key]

    @property
    def residual(self) -> pd.Series:
        """Unexplained (alpha) component for the first asset."""
        if self._residuals is None:
            self.decompose()

        first_key = next(iter(self._residuals))
        return self._residuals[first_key]

    # ------------------------------------------------------------------
    # Static factory: build orthogonal factor set from raw price data
    # ------------------------------------------------------------------

    @staticmethod
    def build_orthogonal_factors(
        factor_prices: pd.DataFrame,
        residualize_order: Optional[list[tuple[str, list[str]]]] = None,
        window: int = 756,
        smoothing: int = 5,
    ) -> pd.DataFrame:
        """Build orthogonal factor performance indices via sequential residualization.

        This is the core of the Two Sigma Factor Lens construction. Each
        factor in ``residualize_order`` is residualized against its listed
        predecessors so the resulting set is approximately orthogonal.

        Parameters
        ----------
        factor_prices : DataFrame with columns for each raw factor price series.
        residualize_order : List of ``(factor_name, [predecessors])`` tuples.
            If a factor has no predecessors (empty list), its raw price is used.
            If None, all columns are returned as-is (no residualization).
        window : Rolling regression window.
        smoothing : Beta smoothing window.

        Returns
        -------
        DataFrame of orthogonal factor performance indices.

        Example
        -------
        >>> order = [
        ...     ("rates", []),                          # base factor
        ...     ("equity", []),                         # base factor
        ...     ("credit", ["rates", "equity"]),        # residualized
        ...     ("commodity", ["rates", "equity"]),     # residualized
        ... ]
        >>> ortho = FactorLens.build_orthogonal_factors(prices, order)
        """
        if residualize_order is None:
            return factor_prices.copy()

        lens = FactorLens(
            returns=pd.DataFrame(),  # not used for building
            factor_returns=pd.DataFrame(),
            window=window,
            smoothing=smoothing,
        )

        built: dict[str, pd.Series] = {}

        for factor_name, predecessors in residualize_order:
            if factor_name not in factor_prices.columns:
                continue

            raw = factor_prices[factor_name].dropna()

            if not predecessors:
                built[factor_name] = raw
                continue

            # Collect previously-built factor prices as regressors
            pred_cols = [p for p in predecessors if p in built]
            if not pred_cols:
                built[factor_name] = raw
                continue

            pred_df = pd.concat(
                [built[p] for p in pred_cols], axis=1
            ).dropna()

            residualized = lens.residualize(raw, pred_df)
            residualized.name = factor_name
            built[factor_name] = residualized

        return pd.DataFrame(built)
