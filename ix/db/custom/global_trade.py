from __future__ import annotations

import pandas as pd

from ix.db.query import Series
from ix.core.transforms import StandardScalar


EXPORT_CODES = {
    "Korea": "KR.FTEXP",
    "Korea Semi": "KRFT7776001",
    "Taiwan": "TW.FTEXP",
    "Singapore": "SGFT1039935",
}


def asian_exports_yoy() -> pd.DataFrame:
    """YoY growth (%) for Korea, Taiwan, Singapore exports.

    Each column is a country's export YoY. Korea reports day 1 of
    each month — the earliest global trade pulse available.
    """
    df = pd.DataFrame(
        {name: Series(code).pct_change(12) * 100 for name, code in EXPORT_CODES.items()}
    ).dropna(how="all")
    return df


def asian_exports_diffusion() -> pd.Series:
    """% of Asian export series with positive YoY growth.

    4 series: Korea total, Korea semi, Taiwan, Singapore.
    100% = synchronized trade boom. 0% = synchronized decline.
    Historically leads global PMI inflections by 1-2 months.
    """
    df = asian_exports_yoy()
    positive = (df > 0).sum(axis=1)
    valid = df.notna().sum(axis=1)
    s = (positive / valid * 100).dropna()
    s.name = "Asian Exports Diffusion"
    return s


def asian_exports_momentum() -> pd.Series:
    """% of Asian export series with accelerating YoY growth.

    Diff of YoY: positive = acceleration.
    Breadth of acceleration signals turning points earlier than levels.
    """
    df = asian_exports_yoy()
    changes = df.diff()
    positive = (changes > 0).sum(axis=1)
    valid = changes.notna().sum(axis=1)
    s = (positive / valid * 100).dropna()
    s.name = "Asian Exports Momentum Breadth"
    return s


def korea_semi_share() -> pd.Series:
    """Korea semiconductor exports as share of total exports (%).

    Rising share = tech-cycle-driven trade.
    Falling share = old-economy/commodity recovery.
    Useful for sector allocation decisions.
    """
    semi = Series("KRFT7776001")
    total = Series("KR.FTEXP")
    s = (semi / total * 100).dropna()
    s.name = "Korea Semi Export Share"
    return s


def global_trade_composite(window: int = 160) -> pd.Series:
    """Composite global trade indicator: average z-score of all export YoY.

    Standardizes Korea, Taiwan, Singapore export YoY growth, averages.
    Single number for "how is global trade doing" relative to history.
    """
    df = asian_exports_yoy()
    z = pd.DataFrame(
        {col: StandardScalar(df[col].dropna(), window) for col in df.columns}
    )
    s = z.mean(axis=1).dropna()
    s.name = "Global Trade Composite"
    return s
