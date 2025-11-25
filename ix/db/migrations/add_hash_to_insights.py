import sys
import os
from sqlalchemy import text
from ix.db.conn import Connection
from ix.misc.terminal import get_logger

logger = get_logger(__name__)


def run_migration():
    logger.info("Adding 'hash_tag' column to insights table...")
    conn = Connection()
    if not conn.is_connected():
        if not conn.connect():
            logger.error("Failed to connect to the database for migration.")
            return False

    engine = conn.engine
    if engine is None:
        logger.error("Database engine is not initialized.")
        return False

    try:
        with engine.begin() as connection:
            # Add the column if it doesn't exist
            # Using IF NOT EXISTS to make the migration idempotent
            connection.execute(
                text(
                    "ALTER TABLE insights ADD COLUMN IF NOT EXISTS hash_tag VARCHAR"
                )
            )
            logger.info("Added 'hash_tag' column to insights table")

        logger.info("Migration completed successfully: hash_tag column added.")
        return True
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False


if __name__ == "__main__":
    print("============================================================")
    print("Migration: Add hash column to insights table")
    print("============================================================")
    try:
        run_migration()
        print("\n============================================================")
        print("✅ Migration completed successfully!")
        print("============================================================")
    except Exception as e:
        logger.exception("Migration failed.")
        print("\n============================================================")
        print(f"❌ Migration failed: {e}")
        print("============================================================")
        sys.exit(1)
