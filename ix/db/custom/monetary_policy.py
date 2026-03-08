from __future__ import annotations

import pandas as pd

from ix.db.query import Series
from ix.core.transforms import StandardScalar


def rate_cut_expectations() -> pd.Series:
    """Expected rate change over next 12 months (bps).

    (100 - FF1) gives implied current policy rate.
    (100 - FF12) gives implied rate 12 months ahead.
    Difference: positive = market pricing cuts; negative = pricing hikes.
    Multiplied by 100 to express in basis points.
    """
    ff1 = Series("FF1 Comdty:PX_LAST")
    ff12 = Series("FF12 Comdty:PX_LAST")
    s = ((ff1 - ff12) * 100).dropna()
    s.name = "Rate Cut Expectations (bps)"
    return s


def rate_expectations_momentum(window: int = 20) -> pd.Series:
    """Velocity of repricing in rate expectations (bps change over window).

    Fast move toward cuts (positive momentum) historically precedes
    equity rallies. Fast move toward hikes precedes risk-off.
    """
    s = rate_cut_expectations().diff(window)
    s.name = "Rate Expectations Momentum"
    return s.dropna()


def rate_expectations_zscore(window: int = 252) -> pd.Series:
    """Z-score of rate cut expectations vs trailing distribution.

    Extreme readings mark inflection points for risk assets.
    """
    return StandardScalar(rate_cut_expectations(), window)


def term_premium_proxy() -> pd.Series:
    """Term premium proxy: 10Y yield minus implied 12M policy rate (%).

    Compensation for duration risk beyond rate expectations.
    Rising with stable rate expectations = bond supply concern.
    Falling = flight to quality or QE expectations.
    """
    y10 = Series("TRYUS10Y:PX_YTM")
    ff12 = Series("FF12 Comdty:PX_LAST")
    implied_rate = 100 - ff12
    s = (y10 - implied_rate).dropna()
    s.name = "Term Premium Proxy"
    return s


def policy_rate_level() -> pd.Series:
    """Implied current policy rate from FF1 (%).

    100 - FF1 price. Tracks the effective Fed Funds rate.
    """
    ff1 = Series("FF1 Comdty:PX_LAST")
    s = (100 - ff1).dropna()
    s.name = "Implied Policy Rate"
    return s
