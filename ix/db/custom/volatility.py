from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series
from ix.core.transforms import StandardScalar


# ── VIX Term Structure ──────────────────────────────────────────────────────


def vix_term_structure(freq: str = "D") -> pd.Series:
    """VIX / VIX3M ratio — measures vol term structure slope.

    < 1 = contango (normal, calm markets). > 1 = backwardation (fear/stress).
    Persistent backwardation is one of the strongest tactical bearish signals.
    """
    vix = Series("VIX INDEX:PX_LAST", freq=freq)
    vix3m = Series("VIX3M INDEX:PX_LAST", freq=freq)
    s = (vix / vix3m).dropna()
    s.name = "VIX Term Structure"
    return s


def vix_term_spread(freq: str = "D") -> pd.Series:
    """VIX3M minus VIX (contango spread in vol points).

    Positive = contango (normal). Negative = backwardation (stress).
    Large positive = complacency / vol selling crowded.
    """
    vix = Series("VIX INDEX:PX_LAST", freq=freq)
    vix3m = Series("VIX3M INDEX:PX_LAST", freq=freq)
    s = (vix3m - vix).dropna()
    s.name = "VIX Term Spread"
    return s


def skew_index(freq: str = "D") -> pd.Series:
    """CBOE SKEW Index — measures perceived tail risk.

    Higher SKEW = market pricing more left-tail (crash) risk.
    Typical range: 100-150. Above 140 = elevated tail hedging demand.
    """
    s = Series("SKEW INDEX:PX_LAST", freq=freq)
    s.name = "SKEW Index"
    return s.dropna()


def skew_zscore(window: int = 252) -> pd.Series:
    """Rolling z-score of SKEW index."""
    return StandardScalar(skew_index(), window)


# ── Volatility Risk Premium ─────────────────────────────────────────────────


def vol_risk_premium(window: int = 20) -> pd.Series:
    """VIX / Realized Vol ratio — measures implied vol richness.

    > 1 = VIX is rich vs realized (normal, vol sellers earn premium).
    < 1 = VIX is cheap vs realized (unusual, vol regime shift).
    Extremely high = fear premium (contrarian bullish).
    """
    vix_level = Series("VIX INDEX:PX_LAST")
    spx = Series("SPX INDEX:PX_LAST")
    realized = spx.pct_change().rolling(window).std() * np.sqrt(252) * 100
    s = (vix_level / realized).dropna()
    s.name = "Vol Risk Premium"
    return s


def vol_risk_premium_zscore(window: int = 252) -> pd.Series:
    """Z-score of vol risk premium — extreme readings flag regime shifts."""
    vrp = vol_risk_premium()
    return StandardScalar(vrp.dropna(), window)


# ── Vol of Vol ──────────────────────────────────────────────────────────────


def vol_of_vol(freq: str = "D") -> pd.Series:
    """CBOE VVIX — volatility of VIX (vol of vol).

    High VVIX = market uncertain about volatility direction.
    Spikes often precede large market moves in either direction.
    """
    s = Series("VVIX INDEX:PX_LAST", freq=freq)
    s.name = "VVIX"
    return s.dropna()


def vvix_vix_ratio(freq: str = "D") -> pd.Series:
    """VVIX / VIX ratio — normalized vol-of-vol.

    High ratio with low VIX = building instability under calm surface.
    Low ratio with high VIX = vol spike may be peaking.
    """
    vvix = Series("VVIX INDEX:PX_LAST", freq=freq)
    vix_level = Series("VIX INDEX:PX_LAST", freq=freq)
    s = (vvix / vix_level).dropna()
    s.name = "VVIX/VIX Ratio"
    return s


# ── Gamma Exposure Proxy ────────────────────────────────────────────────────


def gamma_exposure_proxy(window: int = 20) -> pd.Series:
    """Gamma exposure proxy from VIX term structure + put/call dynamics.

    Combines VIX backwardation signal with put/call ratio to estimate
    whether dealer hedging flows amplify or dampen moves.
    Positive = positive gamma (dealers dampen moves).
    Negative = negative gamma (dealers amplify moves / vol selling unwind).
    """
    vix_level = Series("VIX INDEX:PX_LAST")
    vix3m = Series("VIX3M INDEX:PX_LAST")
    pcr = Series("PCRTEQTY INDEX")

    # Term structure component (contango = positive gamma environment)
    ts = StandardScalar((vix3m - vix_level).dropna(), window * 5)
    # Put/call component (low pcr = call heavy = positive gamma)
    pc = -StandardScalar(pcr.dropna(), window * 5)

    s = pd.concat([ts, pc], axis=1).mean(axis=1).dropna()
    s.name = "Gamma Exposure Proxy"
    return s


# ── Realized Vol Regimes ────────────────────────────────────────────────────


def realized_vol_regime(window_short: int = 20, window_long: int = 120) -> pd.Series:
    """Realized vol regime: ratio of short-term to long-term realized vol.

    > 1 = vol expanding (risk-off). < 1 = vol compressing (risk-on).
    Extreme compression often precedes vol explosions.
    """
    spx = Series("SPX INDEX:PX_LAST")
    rets = spx.pct_change().dropna()
    short_vol = rets.rolling(window_short).std() * np.sqrt(252)
    long_vol = rets.rolling(window_long).std() * np.sqrt(252)
    s = (short_vol / long_vol).dropna()
    s.name = "Realized Vol Regime"
    return s
