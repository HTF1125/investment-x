from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series, MultiSeries
from ix.core.transforms import StandardScalar


# ── Rig Counts ─────────────────────────────────────────────────────────────


def us_rig_count(freq: str = "W") -> pd.Series:
    """Baker Hughes US Total Rig Count.

    Energy supply response to prices. Rising rigs = future supply
    increase. Falling rigs = future supply tightening.
    Lags oil prices by 4-6 months.
    """
    s = Series("ROUSTCNT:PX_LAST", freq=freq)
    if s.empty:
        s = Series("BARONE", freq=freq)
    s.name = "US Rig Count"
    return s.dropna()


def us_rig_count_momentum(window: int = 13) -> pd.Series:
    """Rig count change over ~1 quarter.

    Positive = drillers adding rigs (bullish on oil price).
    Negative = pullback (bearish signal for energy sector).
    """
    rigs = us_rig_count()
    if rigs.empty:
        return pd.Series(dtype=float, name="Rig Count Momentum")
    s = rigs.diff(window).dropna()
    s.name = "Rig Count Momentum"
    return s


# ── Strategic Petroleum Reserve ────────────────────────────────────────────


def strategic_petroleum_reserve(freq: str = "W") -> pd.Series:
    """US Strategic Petroleum Reserve (million barrels).

    Government supply buffer. 2022 drawdown was historic
    (~180M bbl release). Refilling creates price floor.
    Low SPR = less buffer for future price shocks.
    """
    s = Series("WTTSTUS1", freq=freq)
    s.name = "SPR (M bbl)"
    return s.dropna()


def spr_change(window: int = 13) -> pd.Series:
    """SPR quarterly change (million barrels).

    Negative = government selling (adding supply, capping prices).
    Positive = refilling (adding demand, supporting prices).
    """
    spr = strategic_petroleum_reserve()
    if spr.empty:
        return pd.Series(dtype=float, name="SPR Change")
    s = spr.diff(window).dropna()
    s.name = "SPR Change"
    return s


# ── Crude Inventories ──────────────────────────────────────────────────────


def crude_inventories(freq: str = "W") -> pd.Series:
    """US Crude Oil Inventories excl SPR (million barrels).

    Supply/demand balance. Rising inventories = oversupply.
    Falling inventories = tight market.
    """
    s = Series("WCESTUS1", freq=freq)
    s.name = "Crude Inventories"
    return s.dropna()


def crude_inventories_zscore(window: int = 52) -> pd.Series:
    """Z-scored crude inventories for supply regime detection.

    > 1σ = glut conditions. < -1σ = tight market.
    """
    inv = crude_inventories()
    if inv.empty:
        return pd.Series(dtype=float, name="Inventory Z-Score")
    s = StandardScalar(inv, window)
    s.name = "Inventory Z-Score"
    return s.dropna()


def crude_inventory_change(window: int = 4) -> pd.Series:
    """Crude inventory weekly change (million barrels).

    Surprise builds/draws move oil prices intraday.
    Persistent direction signals supply/demand imbalance.
    """
    inv = crude_inventories()
    if inv.empty:
        return pd.Series(dtype=float, name="Inventory Change")
    s = inv.diff(window).dropna()
    s.name = "Inventory Change"
    return s


# ── Natural Gas Storage ────────────────────────────────────────────────────


def natural_gas_storage(freq: str = "W") -> pd.Series:
    """US Natural Gas Storage (Bcf).

    Seasonal pattern: injections (Apr-Oct), withdrawals (Nov-Mar).
    Deviation from 5-year average drives price moves.
    """
    s = Series("NGTMPUS", freq=freq)
    if s.empty:
        s = Series("NATURALGAS", freq=freq)
    s.name = "NG Storage"
    return s.dropna()


def natural_gas_storage_zscore(window: int = 52) -> pd.Series:
    """Z-scored natural gas storage vs rolling history."""
    ng = natural_gas_storage()
    if ng.empty:
        return pd.Series(dtype=float, name="NG Storage Z-Score")
    s = StandardScalar(ng, window)
    s.name = "NG Storage Z-Score"
    return s.dropna()


# ── Composite ──────────────────────────────────────────────────────────────


def energy_supply_composite(window: int = 52) -> pd.Series:
    """Energy supply conditions composite.

    Combines rig counts, inventories, and SPR into a single signal.
    Positive = ample supply. Negative = tight supply (bullish prices).
    """
    components = {}

    inv = crude_inventories()
    if not inv.empty:
        components["Crude Inv"] = StandardScalar(inv, window)

    rigs = us_rig_count()
    if not rigs.empty:
        components["Rigs"] = StandardScalar(rigs, window)

    spr = strategic_petroleum_reserve()
    if not spr.empty:
        components["SPR"] = StandardScalar(spr, window)

    if not components:
        return pd.Series(dtype=float, name="Energy Supply Composite")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Energy Supply Composite"
    return s
