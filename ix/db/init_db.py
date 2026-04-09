from ix.db.conn import conn, Base
from ix.db.models import *  # Import all models to ensure they are registered
from ix.common import get_logger

logger = get_logger(__name__)


def _add_column_if_missing(engine, table: str, column: str, col_type: str, default: str):
    """Add a column to an existing table if it doesn't already exist."""
    with engine.connect() as c:
        result = c.execute(
            __import__("sqlalchemy").text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = :t AND column_name = :col"
            ),
            {"t": table, "col": column},
        )
        if not result.fetchone():
            c.execute(
                __import__("sqlalchemy").text(
                    f'ALTER TABLE "{table}" ADD COLUMN "{column}" {col_type} '
                    f"NOT NULL DEFAULT {default}"
                )
            )
            c.commit()
            logger.info("Added column %s.%s", table, column)


def init_db():
    logger.info("Initializing database...")
    if not conn.connect():
        logger.error("Failed to connect to database")
        return

    # Create tables
    logger.info("Creating tables...")
    Base.metadata.create_all(bind=conn.engine, checkfirst=True)

    # Schema migrations for columns added after initial table creation
    _add_column_if_missing(conn.engine, "reports", "settings", "jsonb", "'{}'::jsonb")

    logger.info("Tables created.")


if __name__ == "__main__":
    init_db()
