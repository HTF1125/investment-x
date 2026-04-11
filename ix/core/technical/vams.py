"""VAMS (Volatility-Adjusted Momentum Signal) — 42 Macro style.

Layers price momentum and volatility confirmation to classify
index-level regimes as Bull / Neutral / Bear.

VAMS score ranges from -2 to +2:
    +2  Bullish  — rising price + low vol
    +1  Lean Bull — one component bullish
     0  Neutral  — mixed signals
    -1  Lean Bear — one component bearish
    -2  Bearish  — falling price + high vol

CACRI (Cross-Asset Correction Risk Indicator):
    Fraction of cross-asset proxies with bearish VAMS (score <= -1).
    0.0 = no cross-asset stress, 1.0 = all assets bearish.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Core VAMS computation
# ---------------------------------------------------------------------------

def compute_vams_series(
    prices: pd.Series,
    short_w: int = 4,
    medium_w: int = 13,
) -> pd.Series:
    """Vectorized walk-forward VAMS score at each point in time.

    Args:
        prices: Weekly price series (e.g. Wednesday close).
        short_w: Short-term vol lookback in weeks (default 4).
        medium_w: Medium-term SMA / vol lookback in weeks (default 13).

    Returns:
        pd.Series of integer scores in {-2, -1, 0, +1, +2}.
        First ``medium_w + short_w`` values are NA (warmup).
    """
    sma = prices.rolling(medium_w).mean()
    momentum = pd.Series(
        np.where(prices > sma, 1, -1), index=prices.index,
    )

    log_ret = np.log(prices / prices.shift(1))
    short_vol = log_ret.rolling(short_w).std() * np.sqrt(52)
    median_vol = short_vol.rolling(medium_w).median()
    vol_signal = pd.Series(
        np.where(short_vol < median_vol, 1, -1), index=prices.index,
    )

    score = (momentum + vol_signal).astype("Int64")
    min_req = medium_w + short_w
    score.iloc[:min_req] = pd.NA
    return score


# ---------------------------------------------------------------------------
# Regime helpers
# ---------------------------------------------------------------------------

def score_to_regime(score: int) -> str:
    """Map a VAMS score to a regime label."""
    if score >= 1:
        return "Bull"
    if score <= -1:
        return "Bear"
    return "Neutral"


def weeks_in_regime(vams_scores: pd.Series) -> int:
    """Count consecutive weeks the current regime has persisted."""
    valid = vams_scores.dropna()
    if valid.empty:
        return 0
    current = score_to_regime(int(valid.iloc[-1]))
    count = 0
    for s in reversed(valid.values):
        if score_to_regime(int(s)) == current:
            count += 1
        else:
            break
    return count


def period_return(prices: pd.Series, weeks: int) -> float | None:
    """Compute return over the last *weeks* weeks from a daily price series."""
    if prices.empty or len(prices) < 2:
        return None
    days = weeks * 5  # approximate trading days
    if len(prices) <= days:
        return float(prices.iloc[-1] / prices.iloc[0] - 1)
    return float(prices.iloc[-1] / prices.iloc[-days] - 1)


def compute_cacri(cross_asset_vams: dict[str, int]) -> float:
    """CACRI = fraction of cross-asset proxies with bearish VAMS (score <= -1)."""
    if not cross_asset_vams:
        return 0.0
    n_bearish = sum(1 for v in cross_asset_vams.values() if v <= -1)
    return round(n_bearish / len(cross_asset_vams), 4)
