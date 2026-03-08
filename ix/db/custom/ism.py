from __future__ import annotations

import pandas as pd

from ix.db.query import Series


# ISM Manufacturing sub-component codes
ISM_MFG_CODES = {
    "PMI": "ISMPMI_M",
    "New Orders": "ISMNOR_M",
    "Production": "ISMPRD_M",
    "Employment": "ISMEMP_M",
    "Supplier Deliveries": "ISMSUP_M",
    "Inventories": "ISMINV_M",
    "Customers Inventories": "ISMCINV_M",
    "Backlog of Orders": "ISMBOR_M",
    "New Export Orders": "ISMEXP_M",
    "Imports": "ISMIMP_M",
    "Prices": "ISMPRI_M",
}

# ISM Services sub-component codes
ISM_SVC_CODES = {
    "PMI": "ISMNMI_NM",
    "Business Activity": "ISMBUS_NM",
    "New Orders": "ISMNOR_NM",
    "Employment": "ISMEMP_NM",
    "Supplier Deliveries": "ISMSUP_NM",
    "Inventories": "ISMICH_NM",
    "Inventory Sentiment": "ISMINV_NM",
    "Backlog of Orders": "ISMBOR_NM",
    "New Export Orders": "ISMEXP_NM",
    "Imports": "ISMIMP_NM",
    "Prices": "ISMPRI_NM",
}


def ism_manufacturing_data() -> pd.DataFrame:
    """All ISM Manufacturing sub-components as DataFrame."""
    return pd.DataFrame(
        {name: Series(code) for name, code in ISM_MFG_CODES.items()}
    ).dropna(how="all")


def ism_services_data() -> pd.DataFrame:
    """All ISM Services sub-components as DataFrame."""
    return pd.DataFrame(
        {name: Series(code) for name, code in ISM_SVC_CODES.items()}
    ).dropna(how="all")


def ism_new_orders(freq: str = "ME") -> pd.Series:
    """ISM Manufacturing New Orders index."""
    s = Series("ISMNOR_M:PX_LAST", freq=freq).ffill()
    s.name = "ISM New Orders"
    return s.dropna()


def ism_manufacturing_breadth() -> pd.Series:
    """% of ISM Manufacturing sub-components above 50."""
    df = pd.DataFrame(
        {name: Series(code) for name, code in ISM_MFG_CODES.items()}
    ).dropna(how="all")
    above_50 = (df > 50).sum(axis=1)
    valid = df.notna().sum(axis=1)
    result = (above_50 / valid * 100).dropna()
    result.name = "ISM Mfg Breadth (>50)"
    return result


def ism_services_breadth() -> pd.Series:
    """% of ISM Services sub-components above 50."""
    df = pd.DataFrame(
        {name: Series(code) for name, code in ISM_SVC_CODES.items()}
    ).dropna(how="all")
    above_50 = (df > 50).sum(axis=1)
    valid = df.notna().sum(axis=1)
    result = (above_50 / valid * 100).dropna()
    result.name = "ISM Svc Breadth (>50)"
    return result


def ism_new_orders_minus_inventories() -> pd.Series:
    """ISM Manufacturing New Orders - Inventories spread.

    Classic leading indicator: rising = building demand,
    falling = inventory overhang.
    """
    noi = Series("ISMNOR_M") - Series("ISMINV_M")
    noi.name = "ISM New Orders - Inventories"
    return noi.dropna()


def ism_new_orders_minus_customers_inventories() -> pd.Series:
    """ISM Manufacturing New Orders - Customers' Inventories spread.

    Even more forward-looking than Orders - Inventories.
    """
    spread = Series("ISMNOR_M") - Series("ISMCINV_M")
    spread.name = "ISM New Orders - Customers Inv"
    return spread.dropna()


def ism_manufacturing_momentum_breadth() -> pd.Series:
    """% of ISM Manufacturing sub-components with positive MoM change."""
    df = pd.DataFrame(
        {name: Series(code) for name, code in ISM_MFG_CODES.items()}
    ).dropna(how="all")
    changes = df.diff()
    positive = (changes > 0).sum(axis=1)
    valid = changes.notna().sum(axis=1)
    result = (positive / valid * 100).dropna()
    result.name = "ISM Mfg Momentum Breadth"
    return result
