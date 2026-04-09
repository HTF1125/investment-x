from sqlalchemy import Column, DateTime, Index, String, Text, text, func, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from ix.db.conn import Base


class ResearchSource(Base):
    """Unified research source registry.

    Every research artifact (YouTube video, RSS article, telegram message,
    central-bank doc, news briefing, etc.) gets one row here with enough
    content for downstream Claude synthesis.
    """

    __tablename__ = "research_source"
    __table_args__ = (
        Index("ix_rs_type_published", "source_type", text("published_at DESC NULLS LAST")),
        Index(
            "ix_rs_topics_gin",
            "topics",
            postgresql_using="gin",
        ),
        Index(
            "ix_rs_symbols_gin",
            "symbols",
            postgresql_using="gin",
        ),
        Index(
            "ix_rs_fts",
            text(
                "to_tsvector('english', "
                "coalesce(title, '') || ' ' || "
                "coalesce(content_text, '') || ' ' || "
                "coalesce(summary, ''))"
            ),
            postgresql_using="gin",
        ),
    )

    id = Column(
        UUID(as_uuid=False),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    source_type = Column(String(32), nullable=False, index=True)
    source_name = Column(String, nullable=True, index=True)
    dedup_key = Column(String(64), unique=True, nullable=False, index=True)
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=True)
    content_text = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    meta = Column(JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb"))
    symbols = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    topics = Column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    report_id = Column(
        UUID(as_uuid=False),
        ForeignKey("briefings.id"),
        nullable=True,
    )
    published_at = Column(DateTime, nullable=True, index=True)
    ingested_at = Column(
        DateTime, nullable=False, default=func.now(), server_default=func.now(), index=True,
    )
