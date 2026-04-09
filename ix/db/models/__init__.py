"""Database models — re-exports for backward compatibility.

Individual models live in their own files; import from here or directly.
"""

from ix.db.conn import Base
from .user import User
from .logs import Logs
from .macro_outlook import MacroOutlook
from .briefing import Briefings
from .whiteboard import Whiteboard
from .chart_pack import ChartPack
from .collector_state import CollectorState
from .institutional_holding import InstitutionalHolding
from .macro_regime_strategy import MacroRegimeStrategy
from .strategy_result import StrategyResult
from .research_source import ResearchSource
from .api_cache import ApiCache
from .report import Report
from .credit_event import CreditEvent, CreditWatchlist
from .api_key import ApiKey
from .charts import Charts
from .timeseries import Timeseries, TimeseriesData
from .universe import Universe
from .research_file import ResearchFile
from .regime_snapshot import RegimeSnapshot, regime_fingerprint
from .cache import _cache_get, _cache_put, _cache_invalidate

__all__ = [
    "Base",
    "Timeseries",
    "TimeseriesData",
    "Universe",
    "User",
    "Logs",
    "MacroOutlook",
    "Briefings",
    "Whiteboard",
    "CollectorState",
    "InstitutionalHolding",
    "MacroRegimeStrategy",
    "StrategyResult",
    "ResearchSource",
    "ApiCache",
    "Report",
    "CreditEvent",
    "CreditWatchlist",
    "ApiKey",
    "Charts",
    "ChartPack",
    "ResearchFile",
    "RegimeSnapshot",
    "regime_fingerprint",
    "all_models",
]


def all_models() -> list:
    """Return all model classes."""
    return [
        User,
        Timeseries,
        TimeseriesData,
        Universe,
        Logs,
        MacroOutlook,
        Briefings,
        Whiteboard,
        CollectorState,
        InstitutionalHolding,
        MacroRegimeStrategy,
        StrategyResult,
        ResearchSource,
        ApiCache,
        Report,
        CreditEvent,
        CreditWatchlist,
        ApiKey,
        ResearchFile,
        RegimeSnapshot,
    ]
