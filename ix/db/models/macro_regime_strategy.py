"""SQLAlchemy model for precomputed macro regime strategy backtest data."""

from sqlalchemy import Column, String, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from ix.db.conn import Base


class MacroRegimeStrategy(Base):
    """Stores precomputed walk-forward backtest results per target index.

    Each row holds three JSONB blobs:
      - backtest: per-strategy performance stats, cumulative curves, equity weights,
                  drawdowns, rolling excess, year-by-year alpha, regime history
      - factors: factor selection frequency, latest selection, IC heatmap per category
      - current_signal: latest equity weight per category, regime, factor selections
    """

    __tablename__ = "macro_regime_strategy"

    index_name = Column(String(64), primary_key=True)
    computed_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    backtest = Column(JSONB, nullable=False)
    factors = Column(JSONB, nullable=False)
    current_signal = Column(JSONB, nullable=False)
