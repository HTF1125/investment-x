from __future__ import annotations

import pandas as pd

from ix.db.query import Series, MultiSeries


# Regional forward EPS codes (EPS_NTMA = next-twelve-months aggregate)
EPS_REGION_CODES = {
    "World": "FR0000R1:EPS_NTMA",
    "North America": "FR0000R4:EPS_NTMA",
    "Europe": "FR0000R3:EPS_NTMA",
    "Asia Pacific": "FR0000R2:EPS_NTMA",
    "Emerging": "FR0000R5:EPS_NTMA",
    "Developed": "FR0000R6:EPS_NTMA",
    "Developed x US": "FR0000R7:EPS_NTMA",
}

# SPX sector forward EPS codes
EPS_SECTOR_CODES = {
    "Cons Disc": "S5COND INDEX:EPS_NTMA",
    "Cons Staples": "S5CONS INDEX:EPS_NTMA",
    "Energy": "S5ENRS INDEX:EPS_NTMA",
    "Financials": "S5FINL INDEX:EPS_NTMA",
    "Health Care": "S5HLTH INDEX:EPS_NTMA",
    "Industrials": "S5INDU INDEX:EPS_NTMA",
    "Info Tech": "S5INFT INDEX:EPS_NTMA",
    "Materials": "S5MATR INDEX:EPS_NTMA",
    "Comm Svc": "S5TELS INDEX:EPS_NTMA",
    "Utilities": "S5UTIL INDEX:EPS_NTMA",
}


def regional_eps_momentum(periods: int = 1) -> pd.DataFrame:
    """MoM (or period-over-period) % change in forward EPS by region."""
    EPS_REGION_CODES = {
        "World": "FR0000R1:EPS_NTMA",
        "North America": "FR0000R4:EPS_NTMA",
        "Europe": "FR0000R3:EPS_NTMA",
        "Asia Pacific": "FR0000R2:EPS_NTMA",
        "Emerging": "FR0000R5:EPS_NTMA",
        "Developed": "FR0000R6:EPS_NTMA",
        "Developed x US": "FR0000R7:EPS_NTMA",
    }
        
    df = pd.DataFrame(
        {name: Series(code) for name, code in EPS_REGION_CODES.items()}
    ).dropna(how="all")
    return df.pct_change(periods=periods).dropna(how="all") * 100


def sector_eps_momentum(periods: int = 1) -> pd.DataFrame:
    """MoM % change in forward EPS by S&P 500 sector."""
    df = pd.DataFrame(
        {name: Series(code) for name, code in EPS_SECTOR_CODES.items()}
    ).dropna(how="all")
    return df.pct_change(periods=periods).dropna(how="all") * 100


def regional_eps_breadth(lookback: int = 4, smooth: int = 4) -> pd.Series:
    """% of regions with positive forward EPS momentum.

    Uses 4-week pct_change (not 1-day) to avoid noise from tiny daily
    estimate moves, then smooths with a 4-week moving average.
    """
    df = pd.DataFrame(
        {name: Series(code) for name, code in EPS_REGION_CODES.items()}
    ).dropna(how="all")
    changes = df.pct_change(lookback)
    positive = (changes > 0).sum(axis=1)
    valid = changes.notna().sum(axis=1)
    result = (positive / valid * 100).rolling(smooth, min_periods=1).mean().dropna()
    result.name = "EPS Breadth (Regions)"
    return result


def sector_eps_breadth(lookback: int = 4, smooth: int = 4) -> pd.Series:
    """% of S&P 500 sectors with positive forward EPS momentum.

    Uses 4-week pct_change and 4-week smoothing to reduce noise.
    """
    df = pd.DataFrame(
        {name: Series(code) for name, code in EPS_SECTOR_CODES.items()}
    ).dropna(how="all")
    changes = df.pct_change(lookback)
    positive = (changes > 0).sum(axis=1)
    valid = changes.notna().sum(axis=1)
    result = (positive / valid * 100).rolling(smooth, min_periods=1).mean().dropna()
    result.name = "EPS Breadth (Sectors)"
    return result


def spx_revision_ratio() -> pd.Series:
    """S&P 500 earnings revision ratio: up / (up + down)."""
    up = Series("SPX INDEX:EARNINGS_REVISION_UP_1M")
    down = Series("SPX INDEX:EARNINGS_REVISION_DO_1M")
    total = up + down
    ratio = (up / total * 100).dropna()
    ratio.name = "SPX Revision Ratio"
    return ratio


def spx_revision_breadth() -> pd.Series:
    """S&P 500 net revision breadth: (up - down) / (up + down)."""
    up = Series("SPX INDEX:EARNINGS_REVISION_UP_1M")
    down = Series("SPX INDEX:EARNINGS_REVISION_DO_1M")
    total = up + down
    breadth = ((up - down) / total * 100).dropna()
    breadth.name = "SPX Net Revision Breadth"
    return breadth


def EarningsGrowth_NTMA() -> pd.DataFrame:
    """Earnings growth: (NTMA / LTMA - 1) * 100 for major indices."""
    return MultiSeries(
        **{
            "S&P 500": (
                Series("SPX INDEX:EPS_NTMA", freq="W-Fri")
                / Series("SPX INDEX:EPS_LTMA", freq="W-Fri")
                - 1
            )
            * 100,
            "NASDAQ": (
                Series("CCMP INDEX:EPS_NTMA", freq="W-Fri").ffill()
                / Series("CCMP INDEX:EPS_LTMA", freq="W-Fri").ffill()
                - 1
            )
            * 100,
            "EUROSTOXX 600": (
                Series("SXXP INDEX:EPS_NTMA", freq="W-Fri")
                / Series("SXXP INDEX:EPS_LTMA", freq="W-Fri")
                - 1
            )
            * 100,
        }
    ).iloc[-52 * 10 :]
