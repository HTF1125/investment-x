from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series, MultiSeries
from ix.core.transforms import StandardScalar


# ── Major Sovereign Yields ─────────────────────────────────────────────────


def german_10y(freq: str = "D") -> pd.Series:
    """German 10Y Bund Yield (%).

    European rate benchmark. Risk-free rate for Eurozone.
    Negative yields (pre-2022) were historic anomaly.
    """
    s = Series("GDBR10 INDEX:PX_LAST", freq=freq)
    if s.empty:
        s = Series("IRLTLT01DEM156N", freq=freq)  # FRED German 10Y
    s.name = "German 10Y"
    return s.dropna()


def japan_10y(freq: str = "D") -> pd.Series:
    """Japan 10Y JGB Yield (%).

    BOJ yield curve control anchor. Movements above/below
    YCC band signal major policy shifts. Carry trade driver.
    """
    s = Series("TRYJP10Y:PX_YTM", freq=freq)
    if s.empty:
        s = Series("IRLTLT01JPM156N", freq=freq)  # FRED Japan 10Y
    s.name = "Japan 10Y"
    return s.dropna()


def uk_10y(freq: str = "D") -> pd.Series:
    """UK 10Y Gilt Yield (%).

    Gilt market stress indicator. 2022 gilt crisis showed
    how fast sovereign bond markets can destabilize.
    """
    s = Series("GUKG10 INDEX:PX_LAST", freq=freq)
    if s.empty:
        s = Series("IRLTLT01GBM156N", freq=freq)  # FRED UK 10Y
    s.name = "UK 10Y Gilt"
    return s.dropna()


# ── Sovereign Spreads ──────────────────────────────────────────────────────


def us_germany_spread(freq: str = "D") -> pd.Series:
    """US 10Y - German 10Y Bund spread (pp).

    Capital flow / USD direction signal. Widening = USD strength
    (US rates more attractive). Narrowing = EUR recovery.
    """
    us10 = Series("TRYUS10Y:PX_YTM", freq=freq)
    if us10.empty:
        us10 = Series("DGS10", freq=freq)
    de10 = german_10y(freq=freq)
    if us10.empty or de10.empty:
        return pd.Series(dtype=float, name="US-DE Spread")
    s = (us10 - de10).dropna()
    s.name = "US-DE 10Y Spread"
    return s


def us_japan_spread(freq: str = "D") -> pd.Series:
    """US 10Y - Japan 10Y JGB spread (pp).

    Carry trade profitability. Widening = stronger yen carry trade
    incentive. Rapid narrowing = carry unwind risk (JPY squeeze).
    """
    us10 = Series("TRYUS10Y:PX_YTM", freq=freq)
    if us10.empty:
        us10 = Series("DGS10", freq=freq)
    jp10 = japan_10y(freq=freq)
    if us10.empty or jp10.empty:
        return pd.Series(dtype=float, name="US-JP Spread")
    s = (us10 - jp10).dropna()
    s.name = "US-JP 10Y Spread"
    return s


# ── Global Rate Convergence ────────────────────────────────────────────────


def g4_yield_dispersion(window: int = 60) -> pd.Series:
    """G4 (US, Germany, UK, Japan) 10Y yield standard deviation.

    Measures global rate divergence. Rising = monetary policy
    divergence (USD strength). Falling = convergence (coordinated easing).
    """
    us10 = Series("TRYUS10Y:PX_YTM")
    if us10.empty:
        us10 = Series("DGS10")
    de10 = german_10y()
    uk10 = uk_10y()
    jp10 = japan_10y()

    df = pd.concat([us10, de10, uk10, jp10], axis=1).ffill().dropna()
    if df.empty or df.shape[1] < 3:
        return pd.Series(dtype=float, name="G4 Yield Dispersion")
    s = df.rolling(window).std().mean(axis=1).dropna()
    s.name = "G4 Yield Dispersion"
    return s


def global_real_rate_composite() -> pd.Series:
    """Simple global real rate proxy: US 10Y real + Germany real + Japan real.

    Uses inflation-adjusted yields where available.
    Rising global real rates = tightening financial conditions.
    Falling = accommodative (risk-on).
    """
    us_real = Series("DFII10")  # US TIPS
    if us_real.empty:
        us10 = Series("DGS10")
        bei = Series("T10YIE")
        if not us10.empty and not bei.empty:
            us_real = (us10 - bei).dropna()
    if us_real.empty:
        return pd.Series(dtype=float, name="Global Real Rate")

    # For Germany and Japan, subtract inflation proxies
    de10 = german_10y()
    de_cpi = Series("FPCPITOTLZGDEU")  # Germany CPI YoY
    jp10 = japan_10y()
    jp_cpi = Series("FPCPITOTLZGJPN")  # Japan CPI YoY

    components = {"US": us_real}
    if not de10.empty and not de_cpi.empty:
        df_de = pd.concat([de10, de_cpi], axis=1).ffill().dropna()
        if not df_de.empty:
            components["DE"] = df_de.iloc[:, 0] - df_de.iloc[:, 1]
    if not jp10.empty and not jp_cpi.empty:
        df_jp = pd.concat([jp10, jp_cpi], axis=1).ffill().dropna()
        if not df_jp.empty:
            components["JP"] = df_jp.iloc[:, 0] - df_jp.iloc[:, 1]

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Global Real Rate"
    return s


# ── EM Sovereign ───────────────────────────────────────────────────────────


def embi_spread(freq: str = "D") -> pd.Series:
    """EMBI+ Spread proxy (EM sovereign risk premium, bps).

    EM sovereign stress aggregate. Widening = EM crisis risk.
    Uses BofA EM sovereign OAS or FRED proxy.
    """
    s = Series("BAMEMHBHYCRSP", freq=freq)
    if s.empty:
        s = Series("BAMEMOBCRSP", freq=freq)
    s.name = "EMBI Spread"
    return s.dropna()


def embi_spread_zscore(window: int = 252) -> pd.Series:
    """Z-scored EMBI spread for stress regime detection."""
    spread = embi_spread()
    if spread.empty:
        return pd.Series(dtype=float, name="EMBI Z-Score")
    s = StandardScalar(spread, window)
    s.name = "EMBI Z-Score"
    return s.dropna()
