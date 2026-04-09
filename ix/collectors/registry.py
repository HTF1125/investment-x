"""Collector registry — maps collector names to instances and provides scheduler helpers."""

import logging

logger = logging.getLogger(__name__)

_COLLECTOR_CLASSES = [
    ("ix.collectors.cftc", "CFTCCollector"),
    ("ix.collectors.aaii", "AAIISentimentCollector"),
    ("ix.collectors.naaim", "NAAIMExposureCollector"),
    ("ix.collectors.cboe", "CBOECollector"),
    ("ix.collectors.google_trends", "GoogleTrendsCollector"),
    ("ix.collectors.sec_13f", "SEC13FCollector"),
    ("ix.collectors.finra_darkpool", "FINRADarkPoolCollector"),
]

ALL_COLLECTORS = []
for _mod, _cls in _COLLECTOR_CLASSES:
    try:
        import importlib
        _m = importlib.import_module(_mod)
        ALL_COLLECTORS.append(getattr(_m, _cls)())
    except Exception as e:
        logger.warning(f"Failed to load collector {_cls} from {_mod}: {e}")

COLLECTOR_MAP = {c.name: c for c in ALL_COLLECTORS}


def get_collector(name: str):
    """Get a collector instance by name."""
    return COLLECTOR_MAP.get(name)


def get_all_collectors():
    """Get all registered collectors."""
    return ALL_COLLECTORS
