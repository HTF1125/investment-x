from sqlalchemy import Column, String, Date, DateTime, Float, BigInteger, Index, text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from ix.db.conn import Base


class InstitutionalHolding(Base):
    """SEC 13-F quarterly institutional holdings."""

    __tablename__ = "institutional_holdings"
    __table_args__ = (
        Index("ix_inst_hold_fund_date", "fund_name", "report_date"),
        Index("ix_inst_hold_cusip", "cusip"),
        Index("ix_inst_hold_symbol", "symbol"),
    )

    id = Column(
        UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()")
    )

    # Filing identity
    cik = Column(String(20), nullable=False, index=True)
    fund_name = Column(String(255), nullable=False, index=True)
    accession_number = Column(String(50), nullable=False, unique=True)

    # Report metadata
    report_date = Column(Date, nullable=False, index=True)
    filed_date = Column(Date, nullable=True)

    # Security identification
    cusip = Column(String(9), nullable=True)
    symbol = Column(String(20), nullable=True)
    security_name = Column(String(255), nullable=False)
    security_class = Column(String(50), nullable=True)

    # Position data
    shares = Column(BigInteger, nullable=False)
    value_usd = Column(BigInteger, nullable=False)  # In thousands (as reported)
    put_call = Column(String(10), nullable=True)

    # Change tracking vs previous quarter
    shares_change = Column(BigInteger, nullable=True)
    shares_change_pct = Column(Float, nullable=True)
    action = Column(String(20), nullable=True)  # NEW, INCREASED, DECREASED, SOLD, UNCHANGED

    # Metadata
    meta = Column(JSONB, default=dict)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
