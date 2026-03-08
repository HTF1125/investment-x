"""Principal Component Analysis decomposition."""

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


def pca_decomposition(df: pd.DataFrame, n_components: int = 3) -> dict:
    """PCA on returns derived from a price DataFrame.

    Parameters
    ----------
    df : DataFrame of price series (columns = assets).
    n_components : Number of principal components to keep.

    Returns
    -------
    dict with:
      - explained_variance_ratio : list of floats
      - cumulative_variance : list of floats
      - loadings : DataFrame (assets × components)
      - components : DataFrame (dates × components)
    """
    if n_components < 1:
        raise ValueError("n_components must be at least 1.")

    prices = df.apply(pd.to_numeric, errors="coerce")
    prices = prices.replace([np.inf, -np.inf], np.nan)
    prices = prices.sort_index().dropna(how="all")
    if prices.shape[1] < 2:
        raise ValueError("Need at least 2 price series for PCA.")

    returns = prices.pct_change(fill_method=None)
    returns = returns.replace([np.inf, -np.inf], np.nan).dropna(how="any")
    if len(returns) < 2:
        raise ValueError("Need at least 2 overlapping return observations for PCA.")

    varying = returns.var(ddof=0)
    keep_columns = varying[varying > 0].index.tolist()
    dropped_columns = [col for col in returns.columns if col not in keep_columns]
    if len(keep_columns) < 1:
        raise ValueError("All series have zero return variance; PCA is undefined.")
    returns = returns[keep_columns]

    n_components = min(n_components, len(returns.columns), len(returns))
    if n_components < 1:
        raise ValueError("Not enough data left after PCA input cleaning.")

    scaler = StandardScaler()
    scaled = scaler.fit_transform(returns)

    pca = PCA(n_components=n_components)
    scores = pca.fit_transform(scaled)

    comp_names = [f"PC{i + 1}" for i in range(n_components)]

    loadings = pd.DataFrame(
        pca.components_.T,
        index=returns.columns,
        columns=comp_names,
    )

    components = pd.DataFrame(
        scores,
        index=returns.index,
        columns=comp_names,
    )

    cumvar = pca.explained_variance_ratio_.cumsum().tolist()

    return {
        "explained_variance_ratio": pca.explained_variance_ratio_.tolist(),
        "cumulative_variance": cumvar,
        "loadings": loadings,
        "components": components,
        "dropped_columns": dropped_columns,
    }
