"""Cross-asset correlation analysis."""

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage

_VALID_METHODS = {"pearson", "spearman", "kendall"}


def _clean_price_frame(df: pd.DataFrame) -> pd.DataFrame:
    clean = df.apply(pd.to_numeric, errors="coerce")
    clean = clean.replace([np.inf, -np.inf], np.nan)
    clean = clean.sort_index()
    clean = clean.dropna(how="all")
    if clean.shape[1] < 2:
        raise ValueError("Need at least 2 price series for correlation analysis.")
    return clean


def _to_returns(df: pd.DataFrame, window: int | None = None) -> pd.DataFrame:
    returns = _clean_price_frame(df).pct_change(fill_method=None)
    returns = returns.replace([np.inf, -np.inf], np.nan).dropna(how="any")
    if window is not None:
        returns = returns.iloc[-int(window) :]
    if len(returns) < 2:
        raise ValueError("Need at least 2 overlapping return observations.")
    return returns


def correlation_matrix(
    df: pd.DataFrame,
    window: int | None = None,
    method: str = "pearson",
) -> pd.DataFrame:
    """Full-sample or trailing-window correlation matrix from price levels.

    Parameters
    ----------
    df : DataFrame of price series (columns = assets).
    window : If provided, use only the last *window* observations.
    method : "pearson", "spearman", or "kendall".

    Returns
    -------
    DataFrame – correlation matrix computed on log-returns.
    """
    if method not in _VALID_METHODS:
        raise ValueError(f"Unsupported correlation method '{method}'.")
    returns = _to_returns(df, window=window)
    corr = returns.corr(method=method)
    corr = corr.replace([np.inf, -np.inf], np.nan).fillna(0.0).clip(-1.0, 1.0)
    np.fill_diagonal(corr.values, 1.0)
    return corr


def rolling_correlation(
    s1: pd.Series,
    s2: pd.Series,
    window: int = 60,
) -> pd.Series:
    """Pairwise rolling correlation between two price series.

    Converts to returns internally.
    """
    if window < 2:
        raise ValueError("Rolling correlation window must be at least 2.")
    r1 = pd.to_numeric(s1, errors="coerce").replace([np.inf, -np.inf], np.nan)
    r2 = pd.to_numeric(s2, errors="coerce").replace([np.inf, -np.inf], np.nan)
    r1 = r1.sort_index().pct_change(fill_method=None)
    r2 = r2.sort_index().pct_change(fill_method=None)
    combined = pd.concat([r1, r2], axis=1)
    combined = combined.replace([np.inf, -np.inf], np.nan).dropna()
    if combined.empty:
        return pd.Series(dtype=float, name="rolling_correlation")
    result = combined.iloc[:, 0].rolling(window=window, min_periods=window).corr(
        combined.iloc[:, 1]
    )
    result = result.replace([np.inf, -np.inf], np.nan)
    result.name = "rolling_correlation"
    return result


def hierarchical_cluster(
    corr: pd.DataFrame,
    method: str = "ward",
) -> dict:
    """Hierarchical clustering on a correlation matrix.

    Returns dict with 'linkage' (ndarray) and 'labels' (list of str).
    Ward method requires a distance matrix: d = sqrt(0.5 * (1 - corr)).
    """
    if corr.shape[0] < 2 or corr.shape[1] < 2:
        raise ValueError("Need at least 2 series to build a correlation cluster.")
    clean_corr = corr.copy()
    clean_corr = clean_corr.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    clean_corr = clean_corr.clip(-1.0, 1.0)
    np.fill_diagonal(clean_corr.values, 1.0)

    dist = np.sqrt(np.clip(0.5 * (1 - clean_corr.values), 0.0, None))
    np.fill_diagonal(dist, 0)
    # condensed distance vector (upper triangle)
    from scipy.spatial.distance import squareform

    condensed = squareform(dist, checks=False)
    Z = linkage(condensed, method=method)
    return {"linkage": Z, "labels": list(clean_corr.columns)}
