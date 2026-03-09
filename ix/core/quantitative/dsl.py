"""Quantitative analytics DSL wrappers.

These accept series codes (strings) so they work naturally in the custom chart
editor DSL, converting to price DataFrames/Series internally via Series().
"""
from __future__ import annotations

import pandas as pd


def Correlation(
    *codes: str,
    window: int | None = None,
    method: str = "pearson",
) -> pd.DataFrame:
    """Correlation matrix from series codes.

    Usage: ``Correlation("SPY", "TLT", "GLD", window=120)``
    """
    from ix.core.quantitative import correlation_matrix
    from ix.db.query import Series

    df = pd.DataFrame({c: Series(c) for c in codes}).dropna()
    return correlation_matrix(df, window=window, method=method)


def RollingCorrelation(
    code1: str,
    code2: str,
    window: int = 60,
) -> pd.Series:
    """Rolling correlation between two series codes.

    Usage: ``RollingCorrelation("SPY", "TLT", window=90)``
    """
    from ix.core.quantitative import rolling_correlation
    from ix.db.query import Series

    return rolling_correlation(Series(code1), Series(code2), window=window)


def Regression(
    y_code: str,
    *x_codes: str,
) -> dict:
    """Multi-factor regression (prices → returns internally).

    Usage: ``Regression("SPY", "TLT", "GLD")``
    """
    from ix.core.quantitative import multi_factor_regression
    from ix.db.query import Series

    y = Series(y_code)
    factors = pd.DataFrame({c: Series(c) for c in x_codes}).dropna()
    return multi_factor_regression(y, factors)


def RollingBeta(
    y_code: str,
    x_code: str,
    window: int = 60,
) -> pd.Series:
    """Rolling beta between two series codes.

    Usage: ``RollingBeta("AAPL", "SPY", window=120)``
    """
    from ix.core.quantitative import rolling_beta
    from ix.db.query import Series

    return rolling_beta(Series(y_code), Series(x_code), window=window)


def PCA(
    *codes: str,
    n_components: int = 3,
) -> dict:
    """PCA decomposition from series codes.

    Usage: ``PCA("SPY", "TLT", "GLD", "EEM", n_components=3)``
    """
    from ix.core.quantitative import pca_decomposition
    from ix.db.query import Series

    df = pd.DataFrame({c: Series(c) for c in codes}).dropna()
    return pca_decomposition(df, n_components=n_components)


def VaR(
    code: str,
    confidence: float = 0.95,
    window: int | None = None,
    method: str = "historical",
) -> dict:
    """Value-at-Risk for a series code.

    Usage: ``VaR("SPY", confidence=0.99, method="parametric")``
    """
    from ix.core.quantitative import historical_var, parametric_var
    from ix.db.query import Series

    s = Series(code)
    if method == "parametric":
        return parametric_var(s, confidence=confidence, window=window)
    return historical_var(s, confidence=confidence, window=window)


def ExpectedShortfall(
    code: str,
    confidence: float = 0.95,
    window: int | None = None,
) -> dict:
    """Expected Shortfall (CVaR) for a series code.

    Usage: ``ExpectedShortfall("SPY", confidence=0.99)``
    """
    from ix.core.quantitative import expected_shortfall
    from ix.db.query import Series

    return expected_shortfall(Series(code), confidence=confidence, window=window)
