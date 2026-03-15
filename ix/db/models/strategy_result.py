"""General-purpose strategy result storage.

Any ``Strategy`` subclass can persist its backtest results here via
``strategy.save()`` and reload via ``Strategy.load()``.

The *strategy_type* column is auto-populated from ``cls.__name__`` —
no manual strings required.  The *fingerprint* (primary key) is
``"{ClassName}:{params_hash}"`` where *params_hash* is the first 12
hex chars of a SHA-256 over the canonical JSON of the parameters dict.
"""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import Column, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB

from ix.db.conn import Base


def compute_fingerprint(strategy_type: str, params: dict) -> str:
    """Deterministic fingerprint from strategy class name + params.

    >>> compute_fingerprint("MacroRegimeStrategy", {"index_name": "ACWI"})
    'MacroRegimeStrategy:...'
    """
    canonical = json.dumps(params, sort_keys=True, default=str)
    params_hash = hashlib.sha256(canonical.encode()).hexdigest()[:12]
    return f"{strategy_type}:{params_hash}"


class StrategyResult(Base):
    """Stores backtest results for any strategy type.

    Columns
    -------
    fingerprint : str (PK)
        ``"{ClassName}:{params_hash}"`` — deterministic, unique per config.
    strategy_type : str
        ``cls.__name__`` of the Strategy subclass.
    computed_at : datetime
        When the backtest was last computed.
    performance : JSONB  (mandatory)
        Standardized metrics: total_return, cagr, vol, sharpe, sortino,
        max_dd, win_rate, plus nested ``benchmark`` dict.
    parameters : JSONB  (mandatory)
        Full parameter dict for reproducibility.  Includes target/index
        name, lookback, etc.
    backtest : JSONB  (flexible)
        Strategy-specific: NAV curves, weights, drawdowns, etc.
    signals : JSONB  (flexible)
        Current signal state, factor selections, etc.
    meta : JSONB  (flexible)
        Anything else (IC heatmaps, regime history, …).
    """

    __tablename__ = "strategy_result"
    __table_args__ = (Index("ix_sr_type", "strategy_type"),)

    fingerprint = Column(String(128), primary_key=True)
    strategy_type = Column(String(64), nullable=False)
    computed_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Mandatory — standardized metrics every strategy produces
    performance = Column(JSONB, nullable=False)

    # Full parameter dict (includes index_name, lookback, etc.)
    parameters = Column(JSONB, nullable=False)

    # Strategy-specific (flexible, nullable)
    backtest = Column(JSONB, nullable=True)
    signals = Column(JSONB, nullable=True)
    meta = Column(JSONB, nullable=True)
