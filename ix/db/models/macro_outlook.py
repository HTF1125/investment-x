"""SQLAlchemy model for precomputed macro outlook data."""

from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from ix.db.conn import Base


class MacroOutlook(Base):
    """Stores precomputed macro outlook snapshots for each target index.

    Each row holds three JSONB blobs:
      - snapshot: current state, indicator readings, regime probabilities, projections
      - timeseries: historical time series of composites, allocations, regime probs
      - backtest: equity curves, allocation weights, performance statistics
    """

    __tablename__ = "macro_outlook"

    target_name = Column(String(64), primary_key=True)
    computed_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    snapshot = Column(JSONB, nullable=False)
    timeseries = Column(JSONB, nullable=False)
    backtest = Column(JSONB, nullable=False)
