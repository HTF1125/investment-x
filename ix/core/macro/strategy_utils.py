"""Shared data-loading utilities and constants for macro strategy tools.

Both ``macro_regime_strategy.py`` (the main Streamlit strategy app) and
``scripts/factor_audit.py`` (the audit app) import from here so that
index maps, publication lags, contrarian sets, and data-loading helpers
are defined in exactly one place.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, Tuple

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Index universe
# ---------------------------------------------------------------------------

INDEX_MAP = {
    "ACWI": "ACWI US EQUITY:PX_LAST",
    "S&P 500": "SPX Index:PX_LAST",
    "DAX": "DAX Index:PX_LAST",
    "Nikkei 225": "NKY Index:PX_LAST",
    "KOSPI": "KOSPI Index:PX_LAST",
    "Hang Seng": "HSI Index:PX_LAST",
    "Shanghai Comp": "SHCOMP Index:PX_LAST",
    "Stoxx 50": "SX5E Index:PX_LAST",
    "FTSE 100": "UKX Index:PX_LAST",
    "MSCI EM": "MXEF Index:PX_LAST",
    "Nasdaq 100": "NDX Index:PX_LAST",
    "Gold": "IAU US EQUITY:PX_LAST",
}

INDEX_NAMES = list(INDEX_MAP.keys())

YF_FALLBACK = {
    "ACWI": "ACWI", "S&P 500": "^GSPC", "DAX": "^GDAXI",
    "Nikkei 225": "^N225", "KOSPI": "^KS11", "Hang Seng": "^HSI",
    "Shanghai Comp": "000001.SS", "Stoxx 50": "^STOXX50E",
    "FTSE 100": "^FTSE", "MSCI EM": "EEM", "Nasdaq 100": "^NDX",
    "Gold": "IAU",
}

# ---------------------------------------------------------------------------
# Horizons
# ---------------------------------------------------------------------------

HORIZON_MAP = {"1m": 4, "3m": 13, "6m": 26, "12m": 52}

CATEGORY_HORIZONS = {
    "Growth": 26,
    "Inflation": 13,
    "Liquidity": 13,
    "Tactical": 8,
}

# ---------------------------------------------------------------------------
# Publication lags (weeks) — shifted to avoid look-ahead bias
# ---------------------------------------------------------------------------

PUBLICATION_LAGS = {
    "OECD CLI World": 8, "OECD CLI Developed": 8, "OECD CLI Emerging": 8,
    "US OECD CLI": 8,
    "US M2": 6, "US M2 Level (Bloomberg)": 6, "Global M2 YoY": 6,
    "Global Liquidity YoY": 6,
    "China M2 YoY": 4, "China M2 Momentum": 4,
    "Credit Impulse": 8, "Bank Credit Impulse": 8,
    "China Credit Impulse": 8, "China New Loans": 6,
    "Consumer Credit Growth": 6, "Consumer Revolving Credit": 6,
    "JOLTS Job Openings": 6, "Temp Help Employment": 4,
    "Industrial Production YoY": 2, "Capacity Utilization": 2,
    "PCE Core YoY": 4, "CPI 3M Annualized": 4,
    "Sticky CPI 3M Ann": 4, "Cleveland Fed Inflation Nowcast": 2,
    "PPI Final Demand YoY": 2, "PPI Core YoY": 2,
    "ECI YoY": 12,
    "Housing Starts": 4, "Building Permits": 4,
    "New Home Sales": 4, "Case-Shiller Home Prices": 8,
    "Retail Sales ex-Auto": 2, "Durable Goods YoY": 4,
    "NFP MoM Change": 1, "Initial Claims": 1,
    "Senior Loan Officer Survey": 2, "Margin Debt YoY": 6,
    "Avg Hourly Earnings": 4, "Atlanta Fed Wage Growth": 4,
    "NFIB Small Biz Optimism": 2, "NFIB Price Plans": 2, "NFIB Higher Prices": 2,
    "UMich 1Y Inflation Expect": 1, "UMich 5Y Inflation Expect": 1,
    "Eurozone HICP YoY": 4, "Import Prices YoY": 2,
    "China IP YoY": 4, "China Official Mfg PMI": 1,
    "GDPNow": 0, "Weekly Economic Index": 0,
    "Philly Fed Mfg": 0, "Empire State Mfg": 0,
}

DEFAULT_TXCOST_BPS = 10

# ---------------------------------------------------------------------------
# Contrarian indicators — use empirical IC sign, not theory sign
# ---------------------------------------------------------------------------

CONTRARIAN_INDICATORS = {
    "VIX", "VXN (Nasdaq Vol)", "RVX (Russell Vol)", "OVX (Oil Vol)", "GVZ (Gold Vol)",
    "VIX Term Structure", "VIX Term Spread", "VIX-Realized Vol Spread",
    "Vol Risk Premium Z", "SKEW Index", "SKEW Z-Score", "VVIX/VIX Ratio",
    "Gamma Exposure Proxy", "Realized Vol Regime",
    "HY Spread", "IG Spread", "BBB Spread", "HY/IG Ratio",
    "HY Spread Momentum", "HY Spread Velocity", "Credit Stress Index",
    "IG/HY Compression", "Credit Cycle Phase",
    "Bloomberg HY OAS", "Bloomberg IG OAS", "CMBS OAS", "MBS OAS",
    "FCI US", "FCI Stress", "Financial Conditions Credit",
    "Chicago Fed NFCI", "Chicago Fed NFCI Credit", "Bloomberg US FCI",
    "Put/Call Z-Score", "CBOE Put Volume",
    "Safe Haven Demand", "Tail Risk Index",
    "Cross-Asset Correlation", "Eq/Bond Correlation Z", "Correlation Surprise",
    "Credit-Equity Divergence",
    "Citi Macro Risk ST", "Citi Macro Risk LT", "Citi EM Macro Risk",
    "EM Sovereign Spread", "EMBI Global Spread",
    "NYSE Down Volume", "Dollar Index",
}


# ---------------------------------------------------------------------------
# Pure utility functions (no Streamlit dependency)
# ---------------------------------------------------------------------------


def load_index(index_name: str) -> pd.Series:
    """Load daily price series for an index from DB, falling back to yfinance."""
    from ix.db.query import Series as DBSeries

    db_code = INDEX_MAP.get(index_name, "ACWI US EQUITY:PX_LAST")
    s = DBSeries(db_code)
    if s.empty:
        yf_ticker = YF_FALLBACK.get(index_name, "ACWI")
        try:
            import yfinance as yf
            df = yf.download(yf_ticker, period="max", auto_adjust=True)
            s = df["Close"].squeeze()
        except Exception:
            return pd.Series(dtype=float)
    s.name = index_name
    return s.dropna()


def load_all_indicators(
    selected_categories: tuple | None = None,
) -> Dict[str, Tuple[pd.Series, str, str, bool]]:
    """Load all macro indicators in parallel.

    Returns dict of name -> (series, category, description, invert).
    Filters to *selected_categories* if provided (tuple for hashability).
    """
    from ix.core.macro.taxonomy import build_macro_registry

    registry = build_macro_registry()
    if selected_categories:
        registry = [r for r in registry if r[2] in selected_categories]
    results: Dict[str, Tuple[pd.Series, str, str, bool]] = {}

    def _load_one(name: str, fn: Callable) -> Tuple[str, pd.Series | None]:
        try:
            raw = fn()
            if isinstance(raw, pd.DataFrame):
                raw = raw.iloc[:, 0] if raw.shape[1] == 1 else raw.sum(axis=1)
            if raw is None or (isinstance(raw, pd.Series) and raw.empty):
                return name, None
            return name, raw.dropna()
        except Exception:
            return name, None

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {}
        meta = {}
        for name, fn, cat, desc, inv in registry:
            futures[executor.submit(_load_one, name, fn)] = name
            meta[name] = (cat, desc, inv)
        for future in as_completed(futures):
            name, series = future.result()
            if series is not None and len(series) > 52:
                cat, desc, inv = meta[name]
                results[name] = (series, cat, desc, inv)
    return results


def resample_to_freq(s: pd.Series, freq: str) -> pd.Series:
    """Resample a series to the given frequency, forward-filling gaps."""
    if s.empty:
        return s
    try:
        return s.resample(freq).last().ffill().dropna()
    except Exception:
        return s


def compute_forward_returns(price: pd.Series, periods: int) -> pd.Series:
    """Compute N-period forward returns from a price series."""
    fwd = price.shift(-periods) / price - 1
    fwd.name = f"Fwd {periods}w Return"
    return fwd.dropna()


def rolling_zscore(s: pd.Series, window: int) -> pd.Series:
    """Compute rolling z-score with a given lookback window."""
    roll = s.rolling(window, min_periods=max(window // 2, 10))
    z = (s - roll.mean()) / roll.std().replace(0, np.nan)
    return z.replace([np.inf, -np.inf], np.nan).dropna()
