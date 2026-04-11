from .crawler import *

"""Investment research data collectors."""


def __getattr__(name):
    # Lazy import to avoid pulling DB-dependent collector modules at package
    # import time (e.g. when only `ix.collectors.crawler` is needed).
    if name in ("get_collector", "get_all_collectors", "COLLECTOR_MAP"):
        from ix.collectors.registry import (
            get_collector,
            get_all_collectors,
            COLLECTOR_MAP,
        )
        return {
            "get_collector": get_collector,
            "get_all_collectors": get_all_collectors,
            "COLLECTOR_MAP": COLLECTOR_MAP,
        }[name]
    raise AttributeError(f"module 'ix.collectors' has no attribute {name!r}")


__all__ = ["get_collector", "get_all_collectors", "COLLECTOR_MAP"]
