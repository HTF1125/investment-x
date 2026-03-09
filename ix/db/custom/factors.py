from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series
from ix.core.transforms import StandardScalar


# ── Cross-Asset Momentum ────────────────────────────────────────────────────

# Asset universe for factor construction
MOMENTUM_UNIVERSE = {
    "US Equity": "SPX INDEX:PX_LAST",
    "Europe Equity": "SXXP INDEX:PX_LAST",
    "Japan Equity": "NKY INDEX:PX_LAST",
    "EM Equity": "891800:FG_TOTAL_RET_IDX",
    "US Bonds": "TLT US EQUITY:PX_LAST",
    "Gold": "GOLDCOMP:PX_LAST",
    "Commodities": "BCOM-CME:PX_LAST",
    "USD": "DXY INDEX:PX_LAST",
}


def cross_asset_momentum(lookback: int = 252, skip: int = 21) -> pd.DataFrame:
    """12-1 month momentum across major asset classes.

    Classic Asness/Moskowitz/Pedersen time-series momentum.
    Uses 12-month return skipping the most recent month
    to avoid short-term reversal contamination.
    """
    data = {}
    for name, code in MOMENTUM_UNIVERSE.items():
        s = Series(code, freq="W")
        if not s.empty:
            mom = s.pct_change(lookback).shift(skip) * 100
            data[name] = mom.dropna()
    return pd.DataFrame(data).dropna(how="all")


def momentum_breadth(lookback: int = 252, skip: int = 21) -> pd.Series:
    """% of assets with positive 12-1 month momentum.

    High breadth (>75%) = broad risk-on. Low breadth (<25%) = broad risk-off.
    Breadth divergences (price up, breadth down) are powerful reversals.
    """
    mom = cross_asset_momentum(lookback, skip)
    if mom.empty:
        return pd.Series(dtype=float, name="Momentum Breadth")
    positive = (mom > 0).sum(axis=1)
    valid = mom.notna().sum(axis=1)
    s = (positive / valid * 100).dropna()
    s.name = "Momentum Breadth"
    return s


def momentum_composite(lookback: int = 252, skip: int = 21) -> pd.Series:
    """Average z-scored momentum across all assets.

    Positive = broad momentum tailwind. Negative = momentum headwind.
    """
    mom = cross_asset_momentum(lookback, skip)
    if mom.empty:
        return pd.Series(dtype=float, name="Momentum Composite")
    z = mom.apply(lambda x: (x - x.rolling(252, min_periods=52).mean())
                  / x.rolling(252, min_periods=52).std())
    s = z.mean(axis=1).dropna()
    s.name = "Momentum Composite"
    return s


# ── Cross-Asset Carry ───────────────────────────────────────────────────────

CARRY_PAIRS = {
    "US Equity Carry": ("SPX INDEX:EPS_NTMA", "SPX INDEX:PX_LAST", "TRYUS10Y:PX_YTM"),
    # Equity carry = earnings yield - bond yield (ERP)
}


def equity_carry() -> pd.Series:
    """Equity carry: S&P 500 earnings yield minus 10Y Treasury yield.

    Positive = equities cheap vs bonds (carry favors stocks).
    Negative = bonds cheap vs equities (carry favors bonds).
    This is the classic equity risk premium.
    """
    eps = Series("SPX INDEX:EPS_NTMA")
    px = Series("SPX INDEX:PX_LAST")
    y10 = Series("TRYUS10Y:PX_YTM")
    if eps.empty or px.empty or y10.empty:
        return pd.Series(dtype=float, name="Equity Carry")
    ey = (eps / px * 100).dropna()
    s = (ey - y10).dropna()
    s.name = "Equity Carry"
    return s


def bond_carry() -> pd.Series:
    """Bond carry: 10Y yield minus 2Y yield (term premium).

    Positive = positive carry for holding duration.
    Negative (inverted curve) = negative carry, recession signal.
    """
    y10 = Series("TRYUS10Y:PX_YTM")
    y2 = Series("TRYUS2Y:PX_YTM")
    s = (y10 - y2).dropna()
    s.name = "Bond Carry"
    return s


def fx_carry() -> pd.Series:
    """FX carry proxy: EM-DM rate differential.

    Uses US rates vs weighted EM rates. Positive = EM carry attractive.
    Carry trades work until they don't (vulnerable to sudden stops).
    """
    us = Series("TRYUS2Y:PX_YTM")
    # Use EM sovereign spread as carry proxy
    hy = Series("BAMLH0A0HYM2")
    if us.empty:
        return pd.Series(dtype=float, name="FX Carry")
    if hy.empty:
        return pd.Series(dtype=float, name="FX Carry")
    s = hy.dropna()  # HY spread approximates EM carry above risk-free
    s.name = "FX Carry Proxy"
    return s


def commodity_carry() -> pd.Series:
    """Commodity carry proxy: roll yield from BDI momentum.

    In backwardation (supply tight), rolling futures forward earns positive carry.
    Uses BDI as proxy for commodity supply-demand balance.
    Positive = backwardation (positive carry). Negative = contango (negative carry).
    """
    bdi = Series("BDI-BAX:PX_LAST")
    if bdi.empty:
        return pd.Series(dtype=float, name="Commodity Carry")
    ma = bdi.rolling(120).mean()
    s = ((bdi / ma) - 1).dropna() * 100
    s.name = "Commodity Carry Proxy"
    return s


def carry_composite(window: int = 120) -> pd.Series:
    """Composite carry signal across asset classes.

    Combines equity, bond, FX, and commodity carry into a single score.
    Positive = carry environment favorable for risk. Negative = unfavorable.
    """
    components = {}
    ec = equity_carry()
    if not ec.empty:
        components["Equity"] = StandardScalar(ec, window)
    bc = bond_carry()
    if not bc.empty:
        components["Bond"] = StandardScalar(bc, window)
    fc = fx_carry()
    if not fc.empty:
        components["FX"] = StandardScalar(fc, window)
    cc = commodity_carry()
    if not cc.empty:
        components["Commodity"] = StandardScalar(cc, window)

    if not components:
        return pd.Series(dtype=float, name="Carry Composite")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Carry Composite"
    return s


# ── Cross-Asset Value ───────────────────────────────────────────────────────


def equity_value() -> pd.Series:
    """Equity value: CAPE-based z-score (inverted — low CAPE = high value).

    Uses P/E ratio as CAPE proxy. Z-scored over 10-year window.
    Positive = cheap (value opportunity). Negative = expensive.
    """
    pe = Series("SPX INDEX:PE_RATIO")
    if pe.empty:
        # Construct from EPS and price
        eps = Series("SPX INDEX:EPS_NTMA")
        px = Series("SPX INDEX:PX_LAST")
        if eps.empty or px.empty:
            return pd.Series(dtype=float, name="Equity Value")
        pe = px / eps
    s = -StandardScalar(pe.dropna(), 520)  # ~10 year window
    s.name = "Equity Value"
    return s.dropna()


def bond_value() -> pd.Series:
    """Bond value: real yield z-score (high real yield = cheap bonds).

    Uses 10Y TIPS yield or nominal minus breakeven as real yield proxy.
    """
    real = Series("DFII10")  # 10Y TIPS yield
    if real.empty:
        y10 = Series("TRYUS10Y:PX_YTM")
        be = Series("T10YIE")  # 10Y breakeven
        if y10.empty or be.empty:
            return pd.Series(dtype=float, name="Bond Value")
        real = (y10 - be).dropna()
    s = StandardScalar(real.dropna(), 520)
    s.name = "Bond Value"
    return s.dropna()


def fx_value() -> pd.Series:
    """Dollar value: mean-reversion signal from DXY z-score (inverted).

    Extremely strong dollar = overvalued = expect reversion.
    Uses 5-year z-score.
    """
    dxy = Series("DXY INDEX:PX_LAST")
    s = -StandardScalar(dxy.dropna(), 260)  # ~5 year
    s.name = "Dollar Value (Inv)"
    return s.dropna()


def value_composite(window: int = 260) -> pd.Series:
    """Composite value signal across asset classes.

    Combines equity, bond, and FX value scores.
    Positive = cheap assets (contrarian buy). Negative = expensive (contrarian sell).
    """
    components = {}
    ev = equity_value()
    if not ev.empty:
        components["Equity"] = ev
    bv = bond_value()
    if not bv.empty:
        components["Bond"] = bv
    fv = fx_value()
    if not fv.empty:
        components["FX"] = fv

    if not components:
        return pd.Series(dtype=float, name="Value Composite")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Value Composite"
    return s


# ── Combined Factor Score ───────────────────────────────────────────────────


def macro_factor_score(window: int = 120) -> pd.Series:
    """Combined macro factor score: momentum + carry + value.

    The three core risk premia that drive macro hedge fund returns.
    Equal-weighted composite of z-scored factor signals.
    Positive = favorable factor environment. Negative = headwinds.
    """
    components = {}
    mc = momentum_composite()
    if not mc.empty:
        components["Momentum"] = StandardScalar(mc, window)
    cc = carry_composite()
    if not cc.empty:
        components["Carry"] = cc  # Already z-scored internally
    vc = value_composite()
    if not vc.empty:
        components["Value"] = vc  # Already z-scored internally

    if not components:
        return pd.Series(dtype=float, name="Macro Factor Score")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Macro Factor Score"
    return s
