"""Value-at-Risk and Expected Shortfall."""

import numpy as np
import pandas as pd
from scipy import stats


def _to_returns(series: pd.Series, window: int | None = None) -> pd.Series:
    """Convert price series to returns, optionally slicing to trailing window."""
    ret = series.pct_change().dropna()
    if window is not None:
        ret = ret.iloc[-window:]
    return ret


def historical_var(
    series: pd.Series,
    confidence: float = 0.95,
    window: int | None = None,
) -> dict:
    """Historical Value-at-Risk from a price series.

    Returns dict with 'var' (positive loss number) and 'returns' Series.
    """
    ret = _to_returns(series, window)
    var_value = float(-np.percentile(ret, (1 - confidence) * 100))
    return {"var": var_value, "returns": ret}


def parametric_var(
    series: pd.Series,
    confidence: float = 0.95,
    window: int | None = None,
) -> dict:
    """Parametric (Gaussian) VaR.

    Returns dict with 'var', 'mean', 'std'.
    """
    ret = _to_returns(series, window)
    mu = float(ret.mean())
    sigma = float(ret.std())
    z = stats.norm.ppf(1 - confidence)
    var_value = float(-(mu + z * sigma))
    return {"var": var_value, "mean": mu, "std": sigma}


def expected_shortfall(
    series: pd.Series,
    confidence: float = 0.95,
    window: int | None = None,
) -> dict:
    """Expected Shortfall (CVaR) — average loss beyond VaR.

    Returns dict with 'es', 'var', 'returns'.
    """
    ret = _to_returns(series, window)
    threshold = np.percentile(ret, (1 - confidence) * 100)
    tail = ret[ret <= threshold]
    var_value = float(-threshold)
    es_value = float(-tail.mean()) if len(tail) > 0 else var_value
    return {"es": es_value, "var": var_value, "returns": ret}


def rolling_var(
    series: pd.Series,
    confidence: float = 0.95,
    window: int = 252,
) -> pd.Series:
    """Rolling historical VaR from a price series.

    Returns a Series of VaR values (positive = loss).
    """
    ret = series.pct_change().dropna()
    quantile = 1 - confidence
    rvar = ret.rolling(window).quantile(quantile).mul(-1)
    rvar.name = f"VaR_{confidence:.0%}"
    return rvar
