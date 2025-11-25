"""Migration: Add favorite column to timeseries table.

This migration adds a 'favorite' boolean column to the timeseries table
and sets all existing records to False.
"""

from sqlalchemy import text
from ix.db.conn import conn, ensure_connection, Session
from ix.misc.terminal import get_logger

logger = get_logger(__name__)


def migrate():
    """Add favorite column to timeseries table and set all existing records to False."""
    # Ensure database connection
    if not ensure_connection():
        logger.error("Database connection not available. Cannot run migration.")
        return False

    try:
        with Session() as session:
            # Add the column if it doesn't exist
            logger.info("Adding 'favorite' column to timeseries table...")
            session.execute(
                text("""
                    ALTER TABLE timeseries
                    ADD COLUMN IF NOT EXISTS favorite BOOLEAN NOT NULL DEFAULT FALSE
                """)
            )

            # Set all existing records to False (in case column existed with NULL values)
            logger.info("Setting all existing timeseries records to favorite=False...")
            result = session.execute(
                text("""
                    UPDATE timeseries
                    SET favorite = FALSE
                    WHERE favorite IS NULL
                """)
            )

            rows_updated = result.rowcount
            session.commit()
            logger.info(f"Migration completed successfully: favorite column added. Updated {rows_updated} existing records to favorite=False")
            return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        session.rollback()
        return False


if __name__ == "__main__":
    migrate()
