import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from sqlalchemy import text
from ix.db.conn import conn, ensure_connection, Base
from ix.misc import get_logger

logger = get_logger(__name__)


def init_db():
    """Initialize the database schema."""
    logger.info("Initializing database schema...")

    if not ensure_connection():
        logger.error("Failed to connect to database.")
        sys.exit(1)

    try:
        # Import models to ensure they're registered with Base
        from ix.db import models

        # Create all tables
        logger.info("Creating tables...")
        Base.metadata.create_all(bind=conn.engine)

        # Run manual migrations
        logger.info("Running manual migrations...")
        with conn.engine.begin() as conn_check:
            conn_check.execute(
                text(
                    "ALTER TABLE IF EXISTS insights ADD COLUMN IF NOT EXISTS pdf_content BYTEA"
                )
            )
            conn_check.execute(
                text(
                    "ALTER TABLE IF EXISTS timeseries ADD COLUMN IF NOT EXISTS favorite BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
            conn_check.execute(
                text(
                    "ALTER TABLE IF EXISTS insights ADD COLUMN IF NOT EXISTS hash_tag VARCHAR"
                )
            )

        logger.info("Database schema initialized successfully.")

    except Exception as e:
        logger.exception(f"Error initializing database: {e}")
        sys.exit(1)
    finally:
        conn.disconnect()


if __name__ == "__main__":
    init_db()
