from __future__ import annotations

import pandas as pd

from ix.db.query import Series
from ix.core.transforms import StandardScalar


# Citi Economic Surprise Index codes by region
CESI_CODES = {
    "US": "USFXCESIUSD",
    "Euro Zone": "EUZFXCESIEUR",
    "UK": "GBFXCESIGBP",
    "Japan": "JPFXCESIJPY",
    "China": "CNFXCESICNY",
    "Canada": "CAFXCESICAD",
    "Australia": "AUFXCESIAUD",
    "Switzerland": "CHFXCESICHF",
    "Sweden": "SEFXCESISEK",
    "Norway": "NOFXCESINOK",
    "G10": "WDFXCESIG10",
    "EM": "WDFXCESIEM",
    "Asia Pacific": "WDFXCESIAPAC",
}


# ── Citi Surprise ────────────────────────────────────────────────────────────

def cesi_data() -> pd.DataFrame:
    """All regional CESI series as a DataFrame."""
    return pd.DataFrame(
        {name: Series(code) for name, code in CESI_CODES.items()}
    ).dropna(how="all")


def cesi_breadth(smooth: int = 20) -> pd.Series:
    """% of regions with positive Citi Surprise reading (smoothed).

    Raw daily breadth flickers as individual regions hover near zero.
    A 20-day moving average produces a clean, tradeable signal.
    """
    df = pd.DataFrame(
        {name: Series(code) for name, code in CESI_CODES.items()}
    ).dropna(how="all")
    positive = (df > 0).sum(axis=1)
    valid = df.notna().sum(axis=1)
    result = (positive / valid * 100).rolling(smooth, min_periods=1).mean().dropna()
    result.name = "CESI Breadth"
    return result


def cesi_momentum(smooth: int = 20) -> pd.Series:
    """% of regions with improving (MoM) Citi Surprise readings (smoothed).

    Uses 5-day diff instead of 1-day to reduce noise, then 20-day MA.
    """
    df = pd.DataFrame(
        {name: Series(code) for name, code in CESI_CODES.items()}
    ).dropna(how="all")
    changes = df.diff(5)
    positive = (changes > 0).sum(axis=1)
    valid = changes.notna().sum(axis=1)
    result = (positive / valid * 100).rolling(smooth, min_periods=1).mean().dropna()
    result.name = "CESI Momentum Breadth"
    return result


# ── CFTC Positioning ─────────────────────────────────────────────────────────

CFTC_ASSETS = {
    "S&P500": ("CFTNCLALLSP500EMINCMEF_US", "CFTNCSALLSP500EMINCMEF_US"),
    "USD": ("CFTNCLALLJUSDNYBTF_US", "CFTNCSALLJUSDNYBTF_US"),
    "Gold": ("CFTNCLALLGOLDCOMF_US", "CFTNCSALLGOLDCOMF_US"),
    "JPY": ("CFTNCLALLYENCMEF_US", "CFTNCSALLYENCMEF_US"),
    "UST 10Y": ("CFTNCLALLTN10YCBOTF_US", "CFTNCSALLTN10YCBOTF_US"),
}


def cftc_net() -> pd.DataFrame:
    """Net positioning (long - short) for each asset."""
    data = {
        name: Series(long_code) - Series(short_code)
        for name, (long_code, short_code) in CFTC_ASSETS.items()
    }
    return pd.DataFrame(data).dropna(how="all")


def cftc_zscore(window: int = 52) -> pd.DataFrame:
    """Rolling z-score of net positioning."""
    net = cftc_net()
    roll = net.rolling(window)
    return net.sub(roll.mean()).div(roll.std()).dropna(how="all")


def cftc_extreme_count(window: int = 52, threshold: float = 1.5) -> pd.Series:
    """Number of assets with extreme (|z| > threshold) positioning."""
    z = cftc_zscore(window)
    result = (z.abs() > threshold).sum(axis=1)
    result.name = "CFTC Extreme Count"
    return result


# ── Put/Call Ratio ───────────────────────────────────────────────────────────

def put_call_raw() -> pd.Series:
    """Total CBOE Put/Call ratio."""
    s = Series("PCRTEQTY INDEX")
    s.name = "Put/Call Ratio"
    return s.dropna()


def put_call_smoothed(window: int = 10) -> pd.Series:
    """Moving average of Put/Call ratio."""
    s = Series("PCRTEQTY INDEX").rolling(window).mean()
    s.name = f"Put/Call {window}d MA"
    return s.dropna()


def put_call_zscore(window: int = 252) -> pd.Series:
    """Rolling z-score of Put/Call ratio (high = fear)."""
    return StandardScalar(Series("PCRTEQTY INDEX"), window)
