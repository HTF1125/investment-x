from sqlalchemy import Column, Boolean, Date, DateTime, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from ix.db.conn import Base


class CreditEvent(Base):
    """Credit rating action from a rating agency."""

    __tablename__ = "credit_events"

    id = Column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    event_date = Column(Date, nullable=False, index=True)
    agency = Column(String(32), nullable=False, index=True)       # S&P, Moodys, Fitch, KIS, KR, NICE
    entity = Column(String, nullable=False, index=True)
    entity_type = Column(String(32))                               # corporate, sovereign, financial, municipal, structured
    action = Column(String(32), nullable=False)                    # upgrade, downgrade, outlook_change, watch_on, watch_off, affirm, withdraw
    rating_from = Column(String(16))
    rating_to = Column(String(16))
    outlook = Column(String(16))                                   # positive, negative, stable, developing
    sector = Column(String)
    region = Column(String(8))                                     # US, KR, EU, EM, CN, JP, etc.
    summary = Column(Text)
    source_url = Column(String)
    significance = Column(String(8))                               # high, medium, low
    market_impact = Column(Text)
    sources = Column(JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CreditWatchlist(Base):
    """Entity under active surveillance for credit deterioration."""

    __tablename__ = "credit_watchlist"

    id = Column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    entity = Column(String, nullable=False, unique=True, index=True)
    entity_type = Column(String(32))
    sector = Column(String)
    region = Column(String(8))
    current_rating = Column(String(256))                           # e.g. "BBB+ (S&P) / Baa1 (Moody's) / BBB+ (Fitch) / A- (KIS)"
    watch_reason = Column(Text)
    risk_level = Column(String(16), nullable=False, default="medium")  # critical, high, medium, low
    signal_count = Column(Integer, nullable=False, default=0)
    last_signal = Column(Text)
    cra_summary = Column(Text)                                     # 1-2 sentence key point from rating agency commentaries
    added_by = Column(String(32))                                  # manual, auto_outlook, auto_cds, auto_earnings, briefing
    active = Column(Boolean, nullable=False, default=True, index=True)
    notes = Column(JSONB, default=list)                            # [{date, signal, detail}]
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
