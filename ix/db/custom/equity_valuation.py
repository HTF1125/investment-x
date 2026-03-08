from __future__ import annotations

import pandas as pd

from ix.db.query import Series
from ix.core.transforms import StandardScalar


def spx_earnings_yield() -> pd.Series:
    """S&P 500 forward earnings yield (%).

    EPS_NTMA / Price * 100. The inverse of forward P/E.
    """
    eps = Series("SPX INDEX:EPS_NTMA", freq="W-Fri")
    px = Series("SPX INDEX:PX_LAST", freq="W-Fri")
    s = (eps / px * 100).dropna()
    s.name = "SPX Forward Earnings Yield"
    return s


def spx_erp_nominal() -> pd.Series:
    """S&P 500 equity risk premium vs nominal 10Y Treasury (%).

    Forward earnings yield minus nominal 10Y yield.
    When negative, bonds offer higher yield than stocks.
    """
    ey = spx_earnings_yield()
    y10 = Series("FRNTRSYLD100", freq="W-Fri")
    s = (ey - y10).dropna()
    s.name = "SPX ERP (Nominal)"
    return s


def spx_erp_real() -> pd.Series:
    """S&P 500 equity risk premium vs real 10Y TIPS yield (%).

    Forward earnings yield minus TIPS real yield.
    The theoretically correct ERP measure — adjusts for inflation.
    """
    ey = spx_earnings_yield()
    tips = Series("FRNTIPYLD010", freq="W-Fri")
    s = (ey - tips).dropna()
    s.name = "SPX ERP (Real)"
    return s


def erp_zscore(window: int = 252) -> pd.Series:
    """Z-score of real ERP vs trailing distribution.

    Extreme low = equities expensive vs bonds.
    Extreme high = equities cheap vs bonds.
    """
    return StandardScalar(spx_erp_real(), window)


def erp_momentum(window: int = 20) -> pd.Series:
    """Rate of change in real ERP (pp over window).

    Rapidly falling = rates rising faster than earnings = headwind.
    Rapidly rising = rates falling or earnings rising = tailwind.
    """
    s = spx_erp_real().diff(window)
    s.name = "ERP Momentum"
    return s.dropna()


def nasdaq_spx_relative_valuation() -> pd.Series:
    """NASDAQ forward earnings yield minus SPX forward earnings yield (pp).

    When NASDAQ is cheaper on forward yield than SPX, growth trades
    at a discount (rare, historically attractive). Wide premium =
    growth expensive vs broad market.
    """
    ndx_eps = Series("CCMP INDEX:EPS_NTMA", freq="W-Fri").ffill()
    ndx_px = Series("CCMP INDEX:PX_LAST", freq="W-Fri")
    ndx_ey = ndx_eps / ndx_px * 100

    spx_ey = spx_earnings_yield()
    s = (ndx_ey - spx_ey).dropna()
    s.name = "NASDAQ vs SPX Earnings Yield Gap"
    return s
