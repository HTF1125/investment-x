"""Investment research data collectors."""

from ix.collectors.registry import get_collector, get_all_collectors, COLLECTOR_MAP

__all__ = ["get_collector", "get_all_collectors", "COLLECTOR_MAP"]
