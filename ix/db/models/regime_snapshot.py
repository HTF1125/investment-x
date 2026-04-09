"""Unified regime snapshot storage.

Any regime model (Macro, Liquidity, Credit Cycle, etc.) persists its
computed results here.  The *regime_type* column identifies the model,
and the *fingerprint* (primary key) is deterministic from type + params
so ``compute_and_save()`` is idempotent — same config = same row, overwritten.

Pattern mirrors ``StrategyResult`` (``ix/db/models/strategy_result.py``).
"""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import Column, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB

from ix.db.conn import Base


def regime_fingerprint(regime_type: str, params: dict) -> str:
    """Deterministic fingerprint from regime type + parameters.

    >>> regime_fingerprint("macro_liquidity", {"z_window": 36})
    'macro_liquidity:...'
    """
    canonical = json.dumps(params, sort_keys=True, default=str)
    params_hash = hashlib.sha256(canonical.encode()).hexdigest()[:12]
    return f"{regime_type}:{params_hash}"


class RegimeSnapshot(Base):
    """Stores precomputed regime model results.

    One row per (regime_type, parameters) combination.  Each JSONB column
    maps to a frontend page group:

    +-----------------+-------+-------------------------------------------+
    | Column          | Null? | Frontend page(s)                          |
    +-----------------+-------+-------------------------------------------+
    | current_state   |  No   | Current State                             |
    | timeseries      |  No   | History, Indicators                       |
    | strategy        |  Yes  | Strategy (only models with allocations)   |
    | asset_analytics |  Yes  | Asset Performance, Playbook               |
    | meta            |  Yes  | Model (methodology docs)                  |
    +-----------------+-------+-------------------------------------------+
    """

    __tablename__ = "regime_snapshot"
    __table_args__ = (
        Index("ix_rs_type", "regime_type"),
    )

    # ── Identity ────────────────────────────────────────────────────
    fingerprint = Column(String(128), primary_key=True)
    regime_type = Column(String(64), nullable=False)
    computed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ── Reproducibility ─────────────────────────────────────────────
    parameters = Column(JSONB, nullable=False)

    # ── Core (every regime model must populate) ─────────────────────
    current_state = Column(JSONB, nullable=False)
    timeseries = Column(JSONB, nullable=False)

    # ── Optional (only models with allocation templates) ────────────
    strategy = Column(JSONB, nullable=True)
    asset_analytics = Column(JSONB, nullable=True)
    meta = Column(JSONB, nullable=True)
