from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series, MultiSeries
from ix.core.transforms import StandardScalar


# ── Overnight Rates ────────────────────────────────────────────────────────


def sofr_rate(freq: str = "D") -> pd.Series:
    """Secured Overnight Financing Rate (%).

    Baseline overnight funding cost, replaced LIBOR.
    Spikes indicate repo market stress (e.g., Sep 2019 event).
    """
    s = Series("SOFR", freq=freq)
    s.name = "SOFR"
    return s.dropna()


def sofr_fed_funds_spread() -> pd.Series:
    """SOFR minus Effective Fed Funds Rate (bps).

    Measures repo market pressure relative to policy rate.
    Widening = collateral scarcity or funding stress.
    Narrowing = ample reserves.
    """
    sofr = Series("SOFR")
    effr = Series("EFFR")
    if effr.empty:
        effr = Series("DFF")  # FRED daily Fed Funds
    if sofr.empty or effr.empty:
        return pd.Series(dtype=float, name="SOFR-FFR Spread")
    s = ((sofr - effr) * 100).dropna()
    s.name = "SOFR-FFR Spread (bps)"
    return s


# ── Commercial Paper & Short-Term Credit ───────────────────────────────────


def commercial_paper_spread() -> pd.Series:
    """AA Financial Commercial Paper - Treasury Bill spread (bps).

    Short-term credit stress indicator. Widens during funding crises.
    2008 blowout was early GFC warning. Normally 10-30bps.
    """
    cp = Series("DCPF3M")
    tbill = Series("DTB3")
    if cp.empty or tbill.empty:
        return pd.Series(dtype=float, name="CP-TBill Spread")
    s = ((cp - tbill) * 100).dropna()
    s.name = "CP-TBill Spread (bps)"
    return s


def commercial_paper_spread_zscore(window: int = 252) -> pd.Series:
    """Z-scored CP-TBill spread for regime detection.

    > 2σ = funding stress. < -1σ = extremely easy conditions.
    """
    spread = commercial_paper_spread()
    if spread.empty:
        return pd.Series(dtype=float, name="CP Spread Z-Score")
    s = StandardScalar(spread, window)
    s.name = "CP Spread Z-Score"
    return s.dropna()


# ── Money Market Funds ─────────────────────────────────────────────────────


def money_market_fund_assets(freq: str = "ME") -> pd.Series:
    """Total Money Market Fund Assets ($B).

    Cash on the sidelines. Record MMF assets = potential equity fuel.
    Sharp outflows from MMFs often coincide with risk-on rallies.
    """
    s = Series("MMMFFAQ027S", freq=freq)
    if not s.empty:
        s = s / 1000  # Convert to $T for consistency
    s.name = "MMF Assets ($T)"
    return s.dropna()


def money_market_fund_yoy(freq: str = "ME") -> pd.Series:
    """MMF Assets YoY growth (%).

    Rapid growth = risk aversion / flight to safety.
    Declining = money moving back to risk assets.
    """
    mmf = Series("MMMFFAQ027S", freq=freq)
    s = mmf.pct_change(12) * 100
    s.name = "MMF Assets YoY"
    return s.dropna()


def money_market_vs_equities() -> pd.Series:
    """MMF Assets / S&P 500 Market Cap ratio (proxy).

    Sideline cash relative to equity valuations.
    High ratio = potential fuel for rally. Low ratio = fully invested.
    Uses Wilshire 5000 as equity market cap proxy.
    """
    mmf = Series("MMMFFAQ027S")
    wilshire = Series("WILL5000IND")
    if mmf.empty or wilshire.empty:
        return pd.Series(dtype=float, name="MMF/Equity Ratio")
    # Normalize Wilshire to approximate $T market cap
    s = (mmf / (wilshire * 1e9 / 1e12)).dropna()
    s.name = "MMF/Equity Ratio"
    return s


# ── Reverse Repo ───────────────────────────────────────────────────────────


def reverse_repo_usage(freq: str = "D") -> pd.Series:
    """Fed Reverse Repo Facility Usage ($T).

    Measures excess liquidity in the system. Declining RRP = liquidity
    draining into T-bills (net positive for risk assets if TGA stable).
    Already used in net liquidity calc but useful standalone.
    """
    s = Series("RRPONTSYD", freq=freq)
    if not s.empty:
        s = s / 1e9  # Convert to $T
    s.name = "Reverse Repo ($T)"
    return s.dropna()


def reverse_repo_momentum(window: int = 13) -> pd.Series:
    """Reverse repo weekly change ($T).

    Rapidly declining RRP = liquidity injection into markets.
    Rising RRP = liquidity absorption.
    """
    rrp = reverse_repo_usage(freq="W")
    s = rrp.diff(window).dropna()
    s.name = "RRP Momentum"
    return s


# ── Composite ──────────────────────────────────────────────────────────────


def funding_stress_index(window: int = 252) -> pd.Series:
    """Composite funding stress index from money market signals.

    Combines CP spread, SOFR-FFR spread into a single z-scored signal.
    Positive = funding stress. Negative = easy funding conditions.
    """
    components = {}

    cp_spread = commercial_paper_spread()
    if not cp_spread.empty:
        components["CP"] = StandardScalar(cp_spread, window)

    sofr_spread = sofr_fed_funds_spread()
    if not sofr_spread.empty:
        components["SOFR"] = StandardScalar(sofr_spread, window)

    if not components:
        return pd.Series(dtype=float, name="Funding Stress Index")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Funding Stress Index"
    return s
