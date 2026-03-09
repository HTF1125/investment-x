from __future__ import annotations

import pandas as pd

from ix.db.query import Series


def dollar_index(freq: str = "W") -> pd.Series:
    """DXY Dollar Index."""
    s = Series("DXY INDEX:PX_LAST", freq=freq)
    s.name = "Dollar Index"
    return s.dropna()


def copper_gold_ratio(freq: str = "W") -> pd.Series:
    """Copper / Gold price ratio. Rising = growth optimism."""
    copper = Series("COPPER CURNCY:PX_LAST", freq=freq)
    gold = Series("GOLDCOMP:PX_LAST", freq=freq)
    s = (copper / gold).dropna()
    s.name = "Copper/Gold Ratio"
    return s


def em_vs_dm(freq: str = "W") -> pd.Series:
    """MSCI EM vs MSCI World total return ratio."""
    em = Series("891800:FG_TOTAL_RET_IDX", freq=freq)
    dm = Series("990100:FG_TOTAL_RET_IDX", freq=freq)
    s = (em / dm).dropna()
    s.name = "EM vs DM Relative"
    return s


def china_sse(freq: str = "W") -> pd.Series:
    """Shanghai Composite Index."""
    s = Series("SHCOMP INDEX:PX_LAST", freq=freq)
    s.name = "China SSE"
    return s.dropna()


def nikkei(freq: str = "W") -> pd.Series:
    """Nikkei 225 Index."""
    s = Series("NKY INDEX:PX_LAST", freq=freq)
    s.name = "Nikkei 225"
    return s.dropna()


def vix(freq: str = "W") -> pd.Series:
    """CBOE VIX Index."""
    s = Series("VIX INDEX:PX_LAST", freq=freq)
    s.name = "VIX"
    return s.dropna()


def commodities_crb(freq: str = "W") -> pd.Series:
    """Bloomberg Commodity Index."""
    s = Series("BCOM-CME:PX_LAST", freq=freq)
    s.name = "Commodities CRB"
    return s.dropna()


def baltic_dry_index(freq: str = "W") -> pd.Series:
    """Baltic Dry Index — leads global trade by 2-3 months."""
    s = Series("BDI-BAX:PX_LAST", freq=freq)
    s.name = "Baltic Dry Index"
    return s.dropna()


def real_rate_differential(target_bond: str, freq: str = "W") -> pd.Series:
    """Real rate differential: US real yield minus target region real yield.

    Positive = capital flows toward US = headwind for target.
    Uses nominal yields as proxy (breakevens not available for all regions).
    """
    us_10y = Series("TRYUS10Y:PX_YTM", freq=freq)
    target_10y = Series(target_bond, freq=freq)
    diff = (us_10y - target_10y).dropna()
    diff.name = "Real Rate Differential"
    return diff
