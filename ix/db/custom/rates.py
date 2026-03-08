from __future__ import annotations

import pandas as pd

from ix.db.query import Series
from ix.core.transforms import StandardScalar


# ── Yield Curve ──────────────────────────────────────────────────────────────

def us_2s10s() -> pd.Series:
    """US 2s10s yield curve spread (10Y - 2Y)."""
    spread = Series("FRNTRSYLD100") - Series("FRNTRSYLD020")
    spread.name = "US 2s10s"
    return spread.dropna()


def us_3m10y() -> pd.Series:
    """US 3m10y yield curve spread (10Y - 3M)."""
    spread = Series("TRYUS10Y:PX_YTM") - Series("TRYUS3M:PX_YTM")
    spread.name = "US 3m10y"
    return spread.dropna()


def us_2s30s() -> pd.Series:
    """US 2s30s yield curve spread (30Y - 2Y)."""
    spread = Series("FRNTRSYLD300") - Series("FRNTRSYLD020")
    spread.name = "US 2s30s"
    return spread.dropna()


def kr_2s10s() -> pd.Series:
    """Korea 2s10s yield curve spread."""
    spread = Series("BONDAVG01@10Y:PX_YTM") - Series("BONDAVG01@2Y:PX_YTM")
    spread.name = "KR 2s10s"
    return spread.dropna()


# ── Real Rates ───────────────────────────────────────────────────────────────

def us_10y_real() -> pd.Series:
    """US 10Y TIPS real yield."""
    s = Series("FRNTIPYLD010")
    s.name = "US 10Y Real Yield"
    return s.dropna()


def us_10y_breakeven() -> pd.Series:
    """US 10Y breakeven inflation (nominal - TIPS)."""
    bei = Series("FRNTRSYLD100") - Series("FRNTIPYLD010")
    bei.name = "US 10Y Breakeven"
    return bei.dropna()


# ── Credit Spreads ───────────────────────────────────────────────────────────

def hy_spread() -> pd.Series:
    """ICE BofA US High Yield OAS."""
    s = Series("BAMLH0A0HYM2")
    s.name = "US HY OAS"
    return s.dropna()


def ig_spread() -> pd.Series:
    """ICE BofA US Investment Grade OAS."""
    s = Series("BAMLC0A0CM")
    s.name = "US IG OAS"
    return s.dropna()


def bbb_spread() -> pd.Series:
    """ICE BofA BBB US Corporate OAS."""
    s = Series("BAMLC0A4CBBB")
    s.name = "US BBB OAS"
    return s.dropna()


def hy_ig_ratio() -> pd.Series:
    """HY/IG spread ratio — rises in stress."""
    hy = Series("BAMLH0A0HYM2")
    ig = Series("BAMLC0A0CM")
    ratio = (hy / ig).dropna()
    ratio.name = "HY/IG Ratio"
    return ratio


def spread_zscore(window: int = 252) -> pd.DataFrame:
    """Rolling z-scores of HY, IG, BBB spreads."""
    df = pd.DataFrame({
        "HY": Series("BAMLH0A0HYM2"),
        "IG": Series("BAMLC0A0CM"),
        "BBB": Series("BAMLC0A4CBBB"),
    }).dropna()
    roll = df.rolling(window)
    return df.sub(roll.mean()).div(roll.std()).dropna()


# ── Risk Appetite ────────────────────────────────────────────────────────────

def risk_appetite(window: int = 160) -> pd.Series:
    """Risk appetite index: inverted average z-score of vol + spreads.

    Higher = more risk appetite (tighter spreads, lower vol).
    """
    components = [
        StandardScalar(Series("VIX INDEX:PX_LAST"), window),
        StandardScalar(Series("MOVE INDEX:PX_LAST"), window),
        StandardScalar(Series("BAMLH0A0HYM2"), window),
        StandardScalar(Series("BAMLC0A0CM"), window),
    ]
    result = -pd.concat(components, axis=1).ffill().mean(axis=1)
    result.name = "Risk Appetite"
    return result.dropna()
