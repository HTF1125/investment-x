from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series
from ix.common.data.transforms import StandardScalar

from ix.core.indicators.cross_asset import baltic_dry_index, copper_gold_ratio


# ── Korea Leading Indicators ─────────────────────────────────────────────────


def korea_oecd_cli(freq: str = "ME") -> pd.Series:
    """OECD Composite Leading Indicator for Korea."""
    s = Series("KOR.LOLITOAA.STSA:PX_LAST", freq=freq).ffill()
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "OECD CLI Korea"
    return s.dropna()


def korea_pmi_manufacturing(freq: str = "ME") -> pd.Series:
    """S&P Global Korea Manufacturing PMI."""
    s = Series("NTCPMIMFGSA_KR:PX_LAST", freq=freq).ffill()
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "Korea PMI Mfg"
    return s.dropna()


def korea_exports_yoy(freq: str = "ME") -> pd.Series:
    """Korean exports year-over-year growth (%)."""
    s = Series("KR.FTEXP:PX_LAST", freq=freq).pct_change(12).mul(100)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "Korea Exports YoY"
    return s.dropna()


def korea_semi_exports_yoy(freq: str = "ME") -> pd.Series:
    """Korean semiconductor exports year-over-year growth (%)."""
    s = Series("KRFT7776001:PX_LAST", freq=freq).pct_change(12).mul(100)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "Korea Semi Exports"
    return s.dropna()


def korea_consumer_confidence(freq: str = "ME") -> pd.Series:
    """OECD Consumer Confidence Indicator for Korea."""
    s = Series("KOR.CSCICP03.IXNSA:PX_LAST", freq=freq).ffill()
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "Korea Consumer Confidence"
    return s.dropna()


# ── Korea Financial Indicators ───────────────────────────────────────────────


def korea_usdkrw(freq: str = "W") -> pd.Series:
    """USDKRW exchange rate."""
    s = Series("USDKRW CURNCY:PX_LAST", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "USDKRW"
    return s.dropna()


def korea_bond_10y(freq: str = "W") -> pd.Series:
    """Korean 10-year government bond yield."""
    s = Series("TRYKR10Y:PX_YTM", freq=freq)
    if s.empty:
        return pd.Series(dtype=float)
    s.name = "Korea 10Y Yield"
    return s.dropna()


def korea_lei() -> pd.Series:
    """Conference Board Leading Economic Index for Korea (2016=100).

    10-component leading indicator for the Korean economy.
    Monthly, 604 pts from 1975.  Korea's LEI is particularly
    sensitive to semiconductor/export cycles and China demand.

    Source: The Conference Board (KRLEI).
    """
    s = Series("KRLEI")
    if s.empty:
        return pd.Series(dtype=float, name="Korea LEI")
    s.name = "Korea LEI"
    return s.dropna()


def korea_lei_yoy() -> pd.Series:
    """Korea LEI year-over-year change (%).

    Negative YoY readings below -3% have preceded Korean recessions.
    Useful as an EM bellwether — Korea's export-driven economy often
    leads broader Asian and EM equity markets by 3-6 months.

    Source: Computed from Conference Board KRLEI.
    """
    lei = Series("KRLEI")
    if lei.empty:
        return pd.Series(dtype=float, name="Korea LEI YoY %")
    s = lei.pct_change(12) * 100
    s.name = "Korea LEI YoY %"
    return s.dropna()


def korea_recession_risk(window: int = 120) -> pd.Series:
    """Korea recession risk composite (z-score).

    Aggregates 5 Korean macro indicators into a single risk score.
    Higher = more recession risk for Korea.

    Components:
    1. Korea LEI YoY (INVERTED — lower = more risk)
    2. OECD CLI Korea (INVERTED — lower = more risk)
    3. Korea Exports YoY (INVERTED — lower = more risk)
    4. Korea Consumer Confidence (INVERTED — lower = more risk)
    5. USD/KRW (higher = KRW weakness = more risk)

    EMA-smoothed (halflife=8 weeks) to reduce monthly data noise.

    Useful for KOSPI/KOSDAQ allocation decisions.
    z > +1.5 = elevated risk, z > +2.0 = high risk.

    Source: Composite of Conference Board, OECD, FactSet indicators.
    """
    components = {}

    # Korea LEI YoY — INVERTED (lower = more risk)
    lei = Series("KRLEI")
    if not lei.empty:
        lei_yoy_s = lei.pct_change(12).dropna()
        components["LEI"] = -StandardScalar(lei_yoy_s, window)

    # OECD CLI Korea — INVERTED (lower = more risk)
    cli = Series("KOR.LOLITOAA.STSA")
    if not cli.empty:
        cli_mom = cli.pct_change(6).dropna()
        components["CLI"] = -StandardScalar(cli_mom, window)

    # Korea Exports YoY — INVERTED (lower = more risk)
    exp = Series("KR.FTEXP")
    if not exp.empty:
        exp_yoy = exp.pct_change(12).dropna()
        components["Exports"] = -StandardScalar(exp_yoy, window)

    # Korea Consumer Confidence — INVERTED (lower = more risk)
    cci = Series("KOR.CSCICP03.IXNSA")
    if not cci.empty:
        components["CCI"] = -StandardScalar(cci.dropna(), window)

    # USD/KRW — higher KRW weakness = more risk (resample to weekly)
    krw = Series("USDKRW CURNCY:PX_LAST", freq="W")
    if not krw.empty:
        krw_mom = krw.pct_change(13).dropna()
        components["KRW"] = StandardScalar(krw_mom, window)

    if not components:
        return pd.Series(dtype=float, name="Korea Recession Risk")

    raw = pd.DataFrame(components).mean(axis=1).dropna()
    # EMA smooth to reduce mixed-frequency noise
    s = raw.ewm(halflife=4).mean()
    s.name = "Korea Recession Risk"
    return s.dropna()


# ── China & Emerging Markets ─────────────────────────────────────────────────


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
    yoy = m2_cn.pct_change(12, fill_method=None) * 100
    impulse = yoy.diff(3)
    impulse.name = "China Credit Impulse"
    return impulse.dropna()


def china_m2_yoy(freq: str = "ME") -> pd.Series:
    """China M2 year-over-year growth (%).

    PBoC's primary monetary aggregate. Acceleration/deceleration
    signals monetary policy stance shifts.
    """
    m2_cn = Series("CN.MAM2", freq=freq)
    if m2_cn.empty:
        return pd.Series(dtype=float)
    s = m2_cn.pct_change(12, fill_method=None) * 100
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
    if s.empty:
        return pd.Series(dtype=float)
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
    if em.empty or dm.empty:
        return pd.Series(dtype=float)
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


# ── Li Keqiang Index (Proxy) ────────────────────────────────────────────


def li_keqiang_proxy(window: int = 78) -> pd.Series:
    """Modified Li Keqiang Index using available China data.

    Original: 40% electricity + 35% bank loans + 25% rail freight.
    Proxy: 40% China PMI + 35% China M2 YoY + 25% China Credit Impulse.
    Source: Li Keqiang (2007), modified for data availability.
    """
    components = {}

    pmi = china_pmi_composite()
    if not pmi.empty:
        components["PMI"] = StandardScalar(pmi, window) * 0.40

    m2 = china_m2_yoy()
    if not m2.empty:
        components["M2"] = StandardScalar(m2, window) * 0.35

    credit = china_credit_impulse()
    if not credit.empty:
        components["Credit"] = StandardScalar(credit, window) * 0.25

    if not components:
        return pd.Series(dtype=float, name="Li Keqiang Proxy")

    result = pd.DataFrame(components).sum(axis=1).dropna()
    result.name = "Li Keqiang Proxy"
    return result


def li_keqiang_momentum(window: int = 13) -> pd.Series:
    """Li Keqiang Proxy momentum (13-week change).

    Rising = China growth accelerating. Falling = decelerating.
    Source: Derived from Modified Li Keqiang Index.
    """
    lk = li_keqiang_proxy()
    if lk.empty:
        return pd.Series(dtype=float)
    mom = lk.diff(window)
    mom.name = "Li Keqiang Momentum"
    return mom.dropna()


# ── Global Trade ─────────────────────────────────────────────────────────────

EXPORT_CODES = {
    "Korea": "KR.FTEXP",
    "Korea Semi": "KRFT7776001",
    "Taiwan": "TW.FTEXP",
    "Singapore": "SGFT1039935",
}


def asian_exports_yoy() -> pd.DataFrame:
    """YoY growth (%) for Korea, Taiwan, Singapore exports.

    Each column is a country's export YoY. Korea reports day 1 of
    each month — the earliest global trade pulse available.
    """
    data = {}
    for name, code in EXPORT_CODES.items():
        s = Series(code)
        if not s.empty:
            data[name] = s.pct_change(12) * 100
    if not data:
        return pd.DataFrame()
    df = pd.DataFrame(data).dropna(how="all")
    return df


def asian_exports_diffusion() -> pd.Series:
    """% of Asian export series with positive YoY growth.

    4 series: Korea total, Korea semi, Taiwan, Singapore.
    100% = synchronized trade boom. 0% = synchronized decline.
    Historically leads global PMI inflections by 1-2 months.
    """
    df = asian_exports_yoy()
    positive = (df > 0).sum(axis=1)
    valid = df.notna().sum(axis=1)
    s = (positive / valid * 100).dropna()
    s.name = "Asian Exports Diffusion"
    return s


def asian_exports_momentum() -> pd.Series:
    """% of Asian export series with accelerating YoY growth.

    Diff of YoY: positive = acceleration.
    Breadth of acceleration signals turning points earlier than levels.
    """
    df = asian_exports_yoy()
    changes = df.diff()
    positive = (changes > 0).sum(axis=1)
    valid = changes.notna().sum(axis=1)
    s = (positive / valid * 100).dropna()
    s.name = "Asian Exports Momentum Breadth"
    return s


def korea_semi_share() -> pd.Series:
    """Korea semiconductor exports as share of total exports (%).

    Rising share = tech-cycle-driven trade.
    Falling share = old-economy/commodity recovery.
    Useful for sector allocation decisions.
    """
    semi = Series("KRFT7776001")
    total = Series("KR.FTEXP")
    if semi.empty or total.empty:
        return pd.Series(dtype=float)
    s = (semi / total * 100).dropna()
    s.name = "Korea Semi Export Share"
    return s


def global_trade_composite(window: int = 160) -> pd.Series:
    """Composite global trade indicator: average z-score of all export YoY.

    Standardizes Korea, Taiwan, Singapore export YoY growth, averages.
    Single number for "how is global trade doing" relative to history.
    """
    df = asian_exports_yoy()
    z = pd.DataFrame(
        {col: StandardScalar(df[col].dropna(), window) for col in df.columns}
    )
    s = z.mean(axis=1).dropna()
    s.name = "Global Trade Composite"
    return s


# ── IFO / Tankan ──────────────────────────────────────────────────────────


def ifo_business_climate() -> pd.Series:
    """IFO Business Climate Index for Germany.

    Key indicator of German and Eurozone economic sentiment.
    Combines current assessment and expectations. Monthly survey
    of ~9,000 firms across manufacturing, services, trade, construction.

    Source: IFO Institute (DESU7502637).
    """
    s = Series("DESU7502637")
    if s.empty:
        return pd.Series(dtype=float, name="IFO Business Climate")
    s.name = "IFO Business Climate"
    return s.dropna()


def tankan_large_manufacturing() -> pd.Series:
    """Bank of Japan Tankan Large Manufacturing DI.

    Quarterly survey of large manufacturers' business conditions.
    Positive = favorable conditions. Negative = unfavorable.
    Leading indicator for Japanese industrial production and exports.

    Source: Bank of Japan Tankan Survey (JPSU0353978).
    """
    s = Series("JPSU0353978")
    if s.empty:
        return pd.Series(dtype=float, name="Tankan Large Mfg DI")
    s.name = "Tankan Large Mfg DI"
    return s.dropna()


def global_trade_cycle(window: int = 78) -> pd.Series:
    """Global trade cycle composite: z-score average of Korea exports YoY,
    Baltic Dry Index YoY, and Copper/Gold ratio.

    Captures real global trade activity from multiple angles.
    Rising = trade expansion. Falling = contraction.

    Source: Custom composite
    """
    components = {}

    # Korea exports YoY
    kr_exp = korea_exports_yoy()
    if not kr_exp.empty:
        components["Korea Exports YoY"] = StandardScalar(kr_exp, window)

    # Baltic Dry YoY
    bdi = baltic_dry_index()
    if not bdi.empty:
        bdi_yoy = bdi.pct_change(252) * 100
        components["Baltic Dry YoY"] = StandardScalar(bdi_yoy.dropna(), window)

    # Copper/Gold
    cg = copper_gold_ratio()
    if not cg.empty:
        components["Copper/Gold"] = StandardScalar(cg, window)

    if not components:
        return pd.Series(dtype=float, name="Global Trade Cycle")

    s = pd.DataFrame(components).ffill().mean(axis=1)
    s.name = "Global Trade Cycle"
    return s.dropna()
