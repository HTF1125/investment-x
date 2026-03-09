from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series
from ix.core.transforms import StandardScalar


# ── China Credit Impulse ────────────────────────────────────────────────────


def china_credit_impulse(freq: str = "ME") -> pd.Series:
    """China credit impulse from M2 growth acceleration.

    Proxy for Total Social Financing (TSF) impulse. China's credit cycle
    leads global growth and commodity demand by 6-12 months.
    Positive = credit expanding at accelerating rate.
    """
    m2_cn = Series("CN.MAM2", freq=freq)
    if m2_cn.empty:
        return pd.Series(dtype=float, name="China Credit Impulse")
    yoy = m2_cn.pct_change(12) * 100
    impulse = yoy.diff(3)
    impulse.name = "China Credit Impulse"
    return impulse.dropna()


def china_m2_yoy(freq: str = "ME") -> pd.Series:
    """China M2 year-over-year growth (%).

    PBoC's primary monetary aggregate. Acceleration/deceleration
    signals monetary policy stance shifts.
    """
    m2_cn = Series("CN.MAM2", freq=freq)
    s = m2_cn.pct_change(12) * 100
    s.name = "China M2 YoY"
    return s.dropna()


def china_m2_momentum(freq: str = "ME") -> pd.Series:
    """3-month momentum of China M2 YoY growth.

    Positive = M2 growth accelerating (easing). Negative = decelerating (tightening).
    """
    yoy = china_m2_yoy(freq)
    s = yoy.diff(3)
    s.name = "China M2 Momentum"
    return s.dropna()


# ── China PMI ───────────────────────────────────────────────────────────────


def china_pmi_composite() -> pd.Series:
    """China composite PMI (manufacturing + services average).

    > 50 = expansion. < 50 = contraction.
    Uses available China PMI series from the database.
    """
    mfg = Series("CPMINDX INDEX:PX_LAST")  # Caixin Manufacturing PMI
    if mfg.empty:
        mfg = Series("CN.PMI.MFG")
    svc = Series("CPMISVCS INDEX:PX_LAST")  # Caixin Services PMI
    if svc.empty:
        svc = Series("CN.PMI.SVC")

    if not mfg.empty and not svc.empty:
        s = (mfg + svc) / 2
    elif not mfg.empty:
        s = mfg
    elif not svc.empty:
        s = svc
    else:
        return pd.Series(dtype=float, name="China PMI Composite")

    s.name = "China PMI Composite"
    return s.dropna()


def china_pmi_momentum(window: int = 3) -> pd.Series:
    """China PMI momentum (change over window months)."""
    pmi = china_pmi_composite()
    s = pmi.diff(window).dropna()
    s.name = "China PMI Momentum"
    return s


# ── PBoC Policy Proxy ──────────────────────────────────────────────────────


def pboc_easing_proxy(freq: str = "ME") -> pd.Series:
    """PBoC easing proxy from M2 growth minus GDP growth.

    Rising = excess money creation (easing). Falling = tightening.
    Historically predicts China A-share rallies by 3-6 months.
    """
    m2_yoy = china_m2_yoy(freq)
    # Use industrial production as GDP proxy (more frequent)
    ip_cn = Series("CN.IP.YOY", freq=freq)
    if ip_cn.empty:
        # Return just M2 momentum as fallback
        return china_m2_momentum(freq)
    s = (m2_yoy - ip_cn).dropna()
    s.name = "PBoC Easing Proxy"
    return s


# ── EM Sovereign Spreads ────────────────────────────────────────────────────


def em_sovereign_spread() -> pd.Series:
    """EM sovereign spread proxy from EMBI+ or HY-IG differential.

    Measures risk premium for emerging market sovereign debt.
    Rising = EM stress. Falling = EM risk appetite.
    """
    embi = Series("JPEMCOMP:PX_LAST")  # JPMorgan EMBI+ Composite
    if embi.empty:
        # Proxy from HY-IG differential (correlated ~0.85 with EMBI)
        hy = Series("BAMLH0A0HYM2")
        ig = Series("BAMLC0A4CBBB")
        if hy.empty or ig.empty:
            return pd.Series(dtype=float, name="EM Sovereign Spread")
        embi = hy - ig
    embi.name = "EM Sovereign Spread"
    return embi.dropna()


def em_sovereign_spread_zscore(window: int = 252) -> pd.Series:
    """Z-score of EM sovereign spread."""
    return StandardScalar(em_sovereign_spread(), window)


def em_sovereign_spread_momentum(window: int = 60) -> pd.Series:
    """EM spread momentum (change over window days)."""
    s = em_sovereign_spread().diff(window).dropna()
    s.name = "EM Spread Momentum"
    return s


# ── USD/CNY ─────────────────────────────────────────────────────────────────


def usdcny(freq: str = "D") -> pd.Series:
    """USD/CNY exchange rate.

    Rising = CNY weakening (capital outflow signal).
    PBoC manages the rate — sharp moves signal policy shifts.
    """
    s = Series("USDCNY Curncy:PX_LAST", freq=freq)
    s.name = "USD/CNY"
    return s.dropna()


def usdcny_momentum(window: int = 60) -> pd.Series:
    """USD/CNY change over window days (%).

    Rapid CNY weakening (> +3% in 60d) historically destabilizes EM.
    """
    fx = usdcny()
    s = fx.pct_change(window).dropna() * 100
    s.name = "USD/CNY Momentum"
    return s


# ── EM vs DM Momentum ──────────────────────────────────────────────────────


def em_dm_relative_momentum(window: int = 60) -> pd.Series:
    """EM vs DM relative momentum (% outperformance over window).

    Positive = EM outperforming. Negative = DM outperforming.
    Persistent trends last 12-18 months.
    """
    em = Series("891800:FG_TOTAL_RET_IDX")
    dm = Series("990100:FG_TOTAL_RET_IDX")
    ratio = (em / dm).dropna()
    s = ratio.pct_change(window).dropna() * 100
    s.name = "EM-DM Relative Momentum"
    return s


def em_composite_indicator(window: int = 120) -> pd.Series:
    """EM composite health indicator.

    Combines China credit impulse, EM spread, EM relative performance,
    and USD strength into a single EM health score.
    Positive = favorable for EM. Negative = headwinds.
    """
    components = {}

    # China credit impulse (leads EM by 6mo)
    cci = china_credit_impulse()
    if not cci.empty:
        components["China Credit"] = StandardScalar(cci.dropna(), window)

    # EM spread (inverted — low spread = healthy)
    em_sprd = em_sovereign_spread()
    if not em_sprd.empty:
        components["EM Spread"] = -StandardScalar(em_sprd, window)

    # EM relative performance
    em_mom = em_dm_relative_momentum()
    if not em_mom.empty:
        components["EM Relative"] = StandardScalar(em_mom, window)

    # USD weakness is good for EM
    dxy = Series("DXY INDEX:PX_LAST")
    if not dxy.empty:
        components["USD"] = -StandardScalar(dxy.dropna(), window)

    if not components:
        return pd.Series(dtype=float, name="EM Composite")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "EM Composite"
    return s
