"""Quantitative analytics: correlation, regression, PCA, VaR, preprocessing, statistics, estimators, optimization, factor lens."""

from .correlation import correlation_matrix, rolling_correlation, hierarchical_cluster
from .regression import ols_regression, rolling_beta, multi_factor_regression
from .pca import pca_decomposition
from .var import historical_var, parametric_var, expected_shortfall, rolling_var
from .preprocessing import BaseScaler, StandardScaler, RobustScaler, MinMaxScaler
from .statistics import (
    Offset, StandardScaler as StandardScalerFunc, Cycle,
    VAR, STDEV, ENTP, CV, Winsorize, empirical_cov,
)
from .estimators import (
    exponential_weight,
    empirical_cov as empirical_cov_matrix,
    exponential_cov,
    ledoit_wolf_cov,
    oas_cov,
    min_cov_determinant,
    graphical_lasso_cov,
    empirical_mu,
    exponential_mu,
    rolling_regression,
    black_litterman,
)
from .optimizer import (
    PortfolioOptimizer,
    portfolio_return,
    portfolio_variance,
    portfolio_volatility,
    portfolio_sharpe,
    risk_contribution,
    inverse_variance_weights,
    tracking_error,
)
from .factor_lens import (
    FactorLens,
    rolling_factor_regression,
    factor_attribution,
    excess_performance,
    risk_weighted_performance,
)

__all__ = [
    # Correlation
    "correlation_matrix",
    "rolling_correlation",
    "hierarchical_cluster",
    # Regression
    "ols_regression",
    "rolling_beta",
    "multi_factor_regression",
    # PCA
    "pca_decomposition",
    # VaR
    "historical_var",
    "parametric_var",
    "expected_shortfall",
    "rolling_var",
    # Preprocessing
    "BaseScaler",
    "StandardScaler",
    "RobustScaler",
    "MinMaxScaler",
    # Statistics
    "Offset",
    "Cycle",
    "VAR",
    "STDEV",
    "ENTP",
    "CV",
    "Winsorize",
    "empirical_cov",
    # Estimators
    "exponential_weight",
    "empirical_cov_matrix",
    "exponential_cov",
    "ledoit_wolf_cov",
    "oas_cov",
    "min_cov_determinant",
    "graphical_lasso_cov",
    "empirical_mu",
    "exponential_mu",
    "rolling_regression",
    "black_litterman",
    # Optimizer
    "PortfolioOptimizer",
    "portfolio_return",
    "portfolio_variance",
    "portfolio_volatility",
    "portfolio_sharpe",
    "risk_contribution",
    "inverse_variance_weights",
    "tracking_error",
    # Factor Lens
    "FactorLens",
    "rolling_factor_regression",
    "factor_attribution",
    "excess_performance",
    "risk_weighted_performance",
]
