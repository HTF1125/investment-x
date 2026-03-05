"""Cross-asset correlation analysis."""

import numpy as np
import pandas as pd
from scipy.cluster.hierarchy import linkage


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
    returns = df.pct_change().dropna()
    if window is not None:
        returns = returns.iloc[-window:]
    return returns.corr(method=method)


def rolling_correlation(
    s1: pd.Series,
    s2: pd.Series,
    window: int = 60,
) -> pd.Series:
    """Pairwise rolling correlation between two price series.

    Converts to returns internally.
    """
    r1 = s1.pct_change().dropna()
    r2 = s2.pct_change().dropna()
    combined = pd.concat([r1, r2], axis=1).dropna()
    return combined.iloc[:, 0].rolling(window).corr(combined.iloc[:, 1])


def hierarchical_cluster(
    corr: pd.DataFrame,
    method: str = "ward",
) -> dict:
    """Hierarchical clustering on a correlation matrix.

    Returns dict with 'linkage' (ndarray) and 'labels' (list of str).
    Ward method requires a distance matrix: d = sqrt(0.5 * (1 - corr)).
    """
    dist = np.sqrt(0.5 * (1 - corr.values))
    np.fill_diagonal(dist, 0)
    # condensed distance vector (upper triangle)
    from scipy.spatial.distance import squareform

    condensed = squareform(dist, checks=False)
    Z = linkage(condensed, method=method)
    return {"linkage": Z, "labels": list(corr.columns)}
