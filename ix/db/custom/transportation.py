from __future__ import annotations

import numpy as np
import pandas as pd

from ix.db.query import Series, MultiSeries
from ix.core.transforms import StandardScalar


# ── Trucking ───────────────────────────────────────────────────────────────


def truck_tonnage(freq: str = "ME") -> pd.Series:
    """ATA Truck Tonnage Index.

    70% of US freight moves by truck. Strong coincident indicator
    of real economic activity. Tonnage declines precede GDP
    contractions.
    """
    s = Series("TRFVOLUSM227NFWA", freq=freq)
    s.name = "Truck Tonnage"
    return s.dropna()


def truck_tonnage_yoy(freq: str = "ME") -> pd.Series:
    """Truck Tonnage YoY (%)."""
    tt = Series("TRFVOLUSM227NFWA", freq=freq)
    s = tt.pct_change(12) * 100
    s.name = "Truck Tonnage YoY"
    return s.dropna()


# ── Rail ───────────────────────────────────────────────────────────────────


def rail_freight(freq: str = "ME") -> pd.Series:
    """Railroad Freight Carloads proxy.

    Industrial activity proxy. Intermodal = consumer goods.
    Carloads = raw materials (coal, chemicals, lumber).
    Falling carloads = industrial slowdown.
    """
    s = Series("RAILFRTCARLOADSD11", freq=freq)
    if s.empty:
        s = Series("RAIL", freq=freq)
    s.name = "Rail Freight"
    return s.dropna()


def rail_freight_yoy(freq: str = "ME") -> pd.Series:
    """Rail freight YoY (%)."""
    rail = rail_freight()
    if rail.empty:
        return pd.Series(dtype=float, name="Rail Freight YoY")
    s = rail.pct_change(12) * 100
    s.name = "Rail Freight YoY"
    return s.dropna()


# ── Air Travel ─────────────────────────────────────────────────────────────


def air_passengers(freq: str = "ME") -> pd.Series:
    """Air Revenue Passenger-Miles (millions).

    Consumer spending/travel proxy. Strong seasonal patterns.
    YoY comparison smooths seasonality.
    """
    s = Series("AIRRPMTSID11", freq=freq)
    s.name = "Air Passengers"
    return s.dropna()


def air_passengers_yoy(freq: str = "ME") -> pd.Series:
    """Air passenger-miles YoY (%)."""
    air = Series("AIRRPMTSID11", freq=freq)
    s = air.pct_change(12) * 100
    s.name = "Air Passengers YoY"
    return s.dropna()


# ── Vehicle Sales ──────────────────────────────────────────────────────────


def vehicle_sales(freq: str = "ME") -> pd.Series:
    """Total Vehicle Sales (millions, SAAR).

    Big-ticket consumer spending barometer.
    Above 17M = strong. Below 14M = recessionary.
    Sensitive to interest rates and credit availability.
    """
    s = Series("TOTALSA", freq=freq)
    s.name = "Vehicle Sales (M)"
    return s.dropna()


def vehicle_sales_yoy(freq: str = "ME") -> pd.Series:
    """Vehicle Sales YoY (%)."""
    vs = Series("TOTALSA", freq=freq)
    s = vs.pct_change(12) * 100
    s.name = "Vehicle Sales YoY"
    return s.dropna()


# ── Composite ──────────────────────────────────────────────────────────────


def real_economy_transport_composite(window: int = 120) -> pd.Series:
    """Physical economy composite from transportation data.

    Combines trucking, rail, air, and vehicle sales.
    Positive = expanding real activity. Negative = contracting.
    """
    components = {}

    tt = Series("TRFVOLUSM227NFWA")
    if not tt.empty:
        tt_yoy = tt.pct_change(12).dropna()
        components["Trucks"] = StandardScalar(tt_yoy, window)

    rail = rail_freight()
    if not rail.empty:
        rail_yoy = rail.pct_change(12).dropna()
        components["Rail"] = StandardScalar(rail_yoy, window)

    vs = Series("TOTALSA")
    if not vs.empty:
        vs_yoy = vs.pct_change(12).dropna()
        components["Vehicles"] = StandardScalar(vs_yoy, window)

    air = Series("AIRRPMTSID11")
    if not air.empty:
        air_yoy = air.pct_change(12).dropna()
        components["Air"] = StandardScalar(air_yoy, window)

    if not components:
        return pd.Series(dtype=float, name="Transport Composite")

    s = pd.DataFrame(components).mean(axis=1).dropna()
    s.name = "Transport Composite"
    return s
