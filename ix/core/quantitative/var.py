"""Value-at-Risk and Expected Shortfall."""

import numpy as np
import pandas as pd
from scipy import stats


def _clean_series(series: pd.Series) -> pd.Series:
    clean = pd.to_numeric(series, errors="coerce")
    clean = clean.replace([np.inf, -np.inf], np.nan).dropna()
    clean = clean.sort_index()
    return clean


def _to_returns(series: pd.Series, window: int | None = None) -> pd.Series:
    """Convert price series to returns, optionally slicing to trailing window."""
    clean = _clean_series(series)
    if len(clean) < 2:
        return pd.Series(dtype=float)
    ret = clean.pct_change(fill_method=None)
    ret = ret.replace([np.inf, -np.inf], np.nan).dropna()
    if window is not None:
        ret = ret.iloc[-int(window) :]
    return ret


def _empty_result(ret: pd.Series) -> dict:
    return {"var": float("nan"), "returns": ret}


def _is_valid_confidence(confidence: float) -> bool:
    return 0 < float(confidence) < 1


def historical_var(
    series: pd.Series,
    confidence: float = 0.95,
    window: int | None = None,
) -> dict:
    """Historical Value-at-Risk from a price series.

    Returns dict with 'var' (positive loss number) and 'returns' Series.
    """
    ret = _to_returns(series, window)
    if ret.empty or not _is_valid_confidence(confidence):
        return _empty_result(ret)
    var_value = float(max(0.0, -np.percentile(ret, (1 - confidence) * 100)))
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
    if ret.empty or not _is_valid_confidence(confidence):
        return {"var": float("nan"), "mean": float("nan"), "std": float("nan")}
    mu = float(ret.mean())
    sigma = float(ret.std())
    z = stats.norm.ppf(1 - confidence)
    if not np.isfinite(sigma):
        sigma = float("nan")
    var_value = float(max(0.0, -(mu + z * sigma))) if np.isfinite(sigma) else float("nan")
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
    if ret.empty or not _is_valid_confidence(confidence):
        return {"es": float("nan"), "var": float("nan"), "returns": ret}
    threshold = np.percentile(ret, (1 - confidence) * 100)
    tail = ret[ret <= threshold]
    var_value = float(max(0.0, -threshold))
    es_value = float(-tail.mean()) if len(tail) > 0 else var_value
    es_value = max(0.0, es_value)
    return {"es": es_value, "var": var_value, "returns": ret}


def rolling_var(
    series: pd.Series,
    confidence: float = 0.95,
    window: int = 252,
) -> pd.Series:
    """Rolling historical VaR from a price series.

    Returns a Series of VaR values (positive = loss).
    """
    if window < 2:
        raise ValueError("Rolling VaR window must be at least 2.")
    if not _is_valid_confidence(confidence):
        raise ValueError("confidence must be between 0 and 1.")
    ret = _to_returns(series)
    if ret.empty:
        return pd.Series(dtype=float, name=f"VaR_{confidence:.0%}")
    quantile = 1 - confidence
    rvar = ret.rolling(window=window, min_periods=window).quantile(quantile).mul(-1)
    rvar = rvar.clip(lower=0)
    rvar.name = f"VaR_{confidence:.0%}"
    return rvar
