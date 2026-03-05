"""Principal Component Analysis decomposition."""

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
    returns = df.pct_change().dropna()
    n_components = min(n_components, len(returns.columns), len(returns))

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
    }
