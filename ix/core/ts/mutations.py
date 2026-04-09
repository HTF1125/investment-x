"""Timeseries model mutation helpers and shared constants."""

from __future__ import annotations

from ix.db.models import Timeseries

BULK_META_FIELDS = [
    "code",
    "name",
    "provider",
    "asset_class",
    "category",
    "source",
    "source_code",
    "frequency",
    "unit",
    "scale",
    "currency",
    "country",
    "remark",
]

BULK_EXAMPLE = {
    "code": "US_CPI_YOY",
    "name": "US CPI YoY",
    "provider": "FRED",
    "asset_class": "Macro",
    "category": "Inflation",
    "source": "Fred",
    "source_code": "CPIAUCSL:value",
    "frequency": "M",
    "unit": "%",
    "scale": "1",
    "currency": "USD",
    "country": "US",
    "remark": "Example \u2014 delete this column",
}


def apply_timeseries_updates(ts: Timeseries, data: dict) -> None:
    """Apply whitelisted field updates to a Timeseries instance."""
    if "code" in data and data["code"] is not None:
        code = str(data["code"])
        if ":" not in code:
            code = f"{code}:PX_LAST"
        ts.code = code

    if "name" in data:
        name = data["name"]
        ts.name = str(name)[:200] if name else None
    if "provider" in data:
        provider = data["provider"]
        ts.provider = str(provider)[:100] if provider else None
    if "asset_class" in data:
        asset_class = data["asset_class"]
        ts.asset_class = str(asset_class)[:50] if asset_class else None
    if "category" in data:
        category = data["category"]
        ts.category = str(category)[:100] if category else None
    if "source" in data:
        source = data["source"]
        ts.source = str(source)[:100] if source else None
    if "source_code" in data:
        source_code = data["source_code"]
        ts.source_code = str(source_code)[:2000] if source_code else None
    if "frequency" in data:
        frequency = data["frequency"]
        ts.frequency = str(frequency)[:20] if frequency else None
    if "unit" in data:
        unit = data["unit"]
        ts.unit = str(unit)[:50] if unit else None
    if "scale" in data:
        scale = data["scale"]
        if scale is not None:
            ts.scale = int(scale)
        else:
            ts.scale = None
    if "currency" in data:
        currency = data["currency"]
        ts.currency = str(currency)[:10] if currency else None
    if "country" in data:
        country = data["country"]
        ts.country = str(country)[:100] if country else None
    if "remark" in data:
        remark = data["remark"]
        ts.remark = str(remark) if remark else None
    if "favorite" in data:
        ts.favorite = bool(data["favorite"]) if data["favorite"] is not None else None
