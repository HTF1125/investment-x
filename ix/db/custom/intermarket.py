from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series
from ix.core.transforms import StandardScalar


def equity_bond_correlation(window: int = 60) -> pd.Series:
    """Rolling correlation between SPX daily returns and 10Y yield changes.

    Positive = "good news is good news" (growth-driven market).
    Negative = "bad news is good news" (inflation/flight-to-safety regime).
    Regime shifts in this correlation are among the most important
    signals for portfolio construction and hedging.
    """
    spx = Series("SPX INDEX:PX_LAST").pct_change()
    y10 = Series("TRYUS10Y:PX_YTM").diff()
    s = spx.rolling(window).corr(y10).dropna()
    s.name = "Equity-Bond Correlation"
    return s


def risk_on_off_breadth(window: int = 160) -> pd.Series:
    """Breadth of risk-on vs risk-off signals across asset classes (%).

    Checks z-scored direction of 6 cross-asset signals:
    SPX (up=risk-on), VIX (down=risk-on), HY spread (down=risk-on),
    copper/gold (up=risk-on), DXY (down=risk-on), 2s10s (up=risk-on).

    100% = all risk-on. 0% = all risk-off.
    Consensus extremes (>80% or <20%) mark fragile positioning.
    """
    from ix.db.custom.rates import us_2s10s

    signals = {
        "SPX": StandardScalar(Series("SPX INDEX:PX_LAST"), window),
        "VIX": -StandardScalar(Series("VIX INDEX:PX_LAST"), window),
        "HY": -StandardScalar(Series("BAMLH0A0HYM2"), window),
        "Cu/Au": StandardScalar(
            (Series("COPPER CURNCY:PX_LAST") / Series("GOLDCOMP:PX_LAST")).dropna(),
            window,
        ),
        "DXY": -StandardScalar(Series("DXY INDEX:PX_LAST"), window),
        "Curve": StandardScalar(us_2s10s(), window),
    }
    df = pd.DataFrame(signals).dropna(how="all")
    risk_on = (df > 0).sum(axis=1)
    valid = df.notna().sum(axis=1)
    s = (risk_on / valid * 100).dropna()
    s.name = "Risk-On Breadth"
    return s


def small_large_cap_ratio(freq: str = "W") -> pd.Series:
    """Russell 2000 / S&P 500 relative performance ratio.

    Rising = broadening rally, improving growth outlook.
    Falling = narrowing leadership, late-cycle or risk-off.
    """
    rty = Series("RTY INDEX:PX_LAST", freq=freq)
    spx = Series("SPX INDEX:PX_LAST", freq=freq)
    s = (rty / spx).dropna()
    s.name = "Small/Large Cap Ratio"
    return s


def cyclical_defensive_ratio(freq: str = "W") -> pd.Series:
    """SPY / XLP relative performance (cyclical vs defensive).

    Rising = cyclical outperformance = growth confidence.
    Falling = defensive rotation = late-cycle caution.
    """
    spy = Series("SPY US EQUITY:PX_LAST", freq=freq)
    xlp = Series("XLP US EQUITY:PX_LAST", freq=freq)
    s = (spy / xlp).dropna()
    s.name = "Cyclical/Defensive Ratio"
    return s


def credit_equity_divergence(window: int = 60) -> pd.Series:
    """Divergence between equity momentum and credit spread momentum.

    When SPX rises but HY spreads also widen, credit is not confirming
    the equity rally — bearish divergence.
    Computed as: z(SPX momentum) + z(inverted HY spread momentum).
    Large negative values = dangerous divergence.
    """
    spx_mom = Series("SPX INDEX:PX_LAST").pct_change(window).mul(100)
    hy_mom = Series("BAMLH0A0HYM2").diff(window)

    z_spx = StandardScalar(spx_mom.dropna(), window * 4)
    z_hy = -StandardScalar(hy_mom.dropna(), window * 4)

    s = pd.concat([z_spx, z_hy], axis=1).mean(axis=1).dropna()
    s.name = "Credit-Equity Divergence"
    return s


def vix_realized_vol_spread(window: int = 20) -> pd.Series:
    """VIX minus SPX realized volatility (annualized, %).

    Positive = VIX elevated vs realized = fear premium (contrarian bullish).
    Negative = VIX depressed vs realized = complacency (contrarian bearish).
    """
    vix = Series("VIX INDEX:PX_LAST")
    spx = Series("SPX INDEX:PX_LAST")
    realized = spx.pct_change().rolling(window).std() * np.sqrt(252) * 100
    s = (vix - realized).dropna()
    s.name = "VIX-Realized Vol Spread"
    return s
