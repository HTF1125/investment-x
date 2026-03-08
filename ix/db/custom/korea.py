from __future__ import annotations

import pandas as pd

from ix.db.query import Series


# ── Korea Leading Indicators ─────────────────────────────────────────────────

def korea_oecd_cli(freq: str = "ME") -> pd.Series:
    """OECD Composite Leading Indicator for Korea."""
    s = Series("KOR.LOLITOAA.STSA:PX_LAST", freq=freq).ffill()
    s.name = "OECD CLI Korea"
    return s.dropna()


def korea_pmi_manufacturing(freq: str = "ME") -> pd.Series:
    """S&P Global Korea Manufacturing PMI."""
    s = Series("NTCPMIMFGSA_KR:PX_LAST", freq=freq).ffill()
    s.name = "Korea PMI Mfg"
    return s.dropna()


def korea_exports_yoy(freq: str = "ME") -> pd.Series:
    """Korean exports year-over-year growth (%)."""
    s = Series("KR.FTEXP:PX_LAST", freq=freq).pct_change(12).mul(100)
    s.name = "Korea Exports YoY"
    return s.dropna()


def korea_semi_exports_yoy(freq: str = "ME") -> pd.Series:
    """Korean semiconductor exports year-over-year growth (%)."""
    s = Series("KRFT7776001:PX_LAST", freq=freq).pct_change(12).mul(100)
    s.name = "Korea Semi Exports"
    return s.dropna()


def korea_consumer_confidence(freq: str = "ME") -> pd.Series:
    """OECD Consumer Confidence Indicator for Korea."""
    s = Series("KOR.CSCICP03.IXNSA:PX_LAST", freq=freq).ffill()
    s.name = "Korea Consumer Confidence"
    return s.dropna()


# ── Korea Financial Indicators ───────────────────────────────────────────────

def korea_usdkrw(freq: str = "W") -> pd.Series:
    """USDKRW exchange rate."""
    s = Series("USDKRW CURNCY:PX_LAST", freq=freq)
    s.name = "USDKRW"
    return s.dropna()


def korea_bond_10y(freq: str = "W") -> pd.Series:
    """Korean 10-year government bond yield."""
    s = Series("TRYKR10Y:PX_YTM", freq=freq)
    s.name = "Korea 10Y Yield"
    return s.dropna()
