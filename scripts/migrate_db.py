import sys
import os
import logging
import time
from sqlalchemy import create_engine, text, inspect, bindparam
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError, DisconnectionError

# Add project root to path
sys.path.append(os.getcwd())

from ix.db.conn import conn as local_conn, Base
from ix.db.models import *  # Import all models to ensure metadata is populated

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("migration.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Remote DB URL provided by user
REMOTE_DATABASE_URL = "postgresql://investmentx_user:5o5qajk8f7DWKoT6QuKTfc5i9J643Dbq@dpg-d67umm15pdvs73fnk7kg-a.oregon-postgres.render.com/investmentx_2l0n"


def get_remote_connection(engine):
    """Establish and return a new connection to the remote database."""
    try:
        conn = engine.connect()
        return conn
    except Exception as e:
        logger.error(f"Failed to connect to remote DB: {e}")
        return None


def migrate_database():
    logger.info("Starting database migration...")

    # 1. Connect to Local Database
    logger.info("Connecting to local database...")
    if not local_conn.connect():
        logger.error("Failed to connect to local database.")
        return

    # 2. Setup Remote Engine
    logger.info(f"Connecting to remote database...")
    try:
        remote_engine = create_engine(REMOTE_DATABASE_URL, pool_pre_ping=True)
    except Exception as e:
        logger.error(f"Failed to create remote engine: {e}")
        return

    # 3. Create Schema on Remote
    logger.info("Creating schema on remote database...")
    try:
        Base.metadata.create_all(remote_engine)
    except Exception as e:
        logger.error(f"Schema creation failed (logging only): {e}")

    # 4. Truncate existing data on remote
    logger.info("Clearing existing data on remote database...")
    with remote_engine.connect() as conn:
        try:
            sorted_tables = Base.metadata.sorted_tables
            table_names = [t.name for t in sorted_tables]
            for table_name in reversed(table_names):
                try:
                    quoted_name = f'"{table_name}"'
                    conn.execute(text(f"TRUNCATE TABLE {quoted_name} CASCADE;"))
                    conn.commit()
                except Exception as e:
                    logger.warning(f"  Could not truncate {table_name}: {e}")
                    conn.rollback()
        except Exception as e:
            logger.warning(
                f"Error clearing remote data: {e}. Proceeding with insert..."
            )

    # 5. Migrate Data
    self_ref_tables = ["timeseries"]

    # Iterate tables
    for table in Base.metadata.sorted_tables:
        table_name = table.name
        logger.info(f"Migrating table: {table_name}")

        # Read from local
        rows = []
        try:
            with local_conn.engine.connect() as local_connection:
                stmt = table.select()
                result = local_connection.execute(stmt)
                for row in result:
                    if hasattr(row, "_mapping"):
                        rows.append(dict(row._mapping))
                    else:
                        rows.append(dict(row))
        except Exception as e:
            logger.error(f"Error reading from local table {table_name}: {e}")
            continue

        if not rows:
            logger.info(f"  No data found in local {table_name}. Skipping.")
            continue

        logger.info(f"  Found {len(rows)} rows to migrate.")

        # Prepare Data
        rows_to_insert = rows
        updates = []

        if table_name in self_ref_tables:
            logger.info(f"  Handling self-referential table {table_name}...")
            rows_to_insert = []
            for row in rows:
                new_row = row.copy()
                parent_id = new_row.get("parent_id")
                if parent_id:
                    updates.append({"id": new_row["id"], "parent_id": parent_id})
                    new_row["parent_id"] = None
                rows_to_insert.append(new_row)

        # Determine Chunk Size
        chunk_size = 200
        if table_name == "timeseries_data":
            chunk_size = 50  # Reduce chunk size for large JSONB data

        # Insert Loop with Retry
        remote_connection = get_remote_connection(remote_engine)
        if not remote_connection:
            logger.error("Skipping table due to connection failure.")
            continue

        start_index = 0
        while start_index < len(rows_to_insert):
            chunk = rows_to_insert[start_index : start_index + chunk_size]
            retries = 3
            success = False

            while retries > 0 and not success:
                try:
                    if remote_connection.closed:
                        logger.info("Reconnecting to remote DB...")
                        remote_connection = get_remote_connection(remote_engine)
                        if not remote_connection:
                            raise Exception("Could not reconnect")

                    remote_connection.execute(table.insert(), chunk)
                    remote_connection.commit()
                    success = True
                    logger.info(
                        f"    Inserted chunk {start_index} - {start_index+len(chunk)}"
                    )
                except Exception as e:
                    retries -= 1
                    logger.warning(
                        f"    Error inserting chunk ({retries} retries left): {e}"
                    )
                    try:
                        remote_connection.rollback()
                    except:
                        pass
                    # Force reconnect
                    try:
                        remote_connection.close()
                    except:
                        pass
                    remote_connection = get_remote_connection(remote_engine)
                    time.sleep(2)

            if not success:
                logger.error(
                    f"    Failed to insert chunk starting at {start_index} after retries. Skipping chunk."
                )

            start_index += chunk_size

        # Post-Insert Updates (Self-Ref)
        if updates:
            logger.info(f"  Updating parent_id references for {len(updates)} rows...")
            stmt = (
                table.update()
                .where(table.c.id == bindparam("b_id"))
                .values(parent_id=bindparam("b_parent_id"))
            )
            bind_updates = [
                {"b_id": u["id"], "b_parent_id": u["parent_id"]} for u in updates
            ]

            # Batch updates with retry capability?
            # Usually strict UUID updates are fast.
            try:
                if remote_connection.closed:
                    remote_connection = get_remote_connection(remote_engine)

                # Check 100 at a time
                for i in range(0, len(bind_updates), 100):
                    sub_updates = bind_updates[i : i + 100]
                    # We might need improved retry here too?
                    try:
                        remote_connection.execute(stmt, sub_updates)
                        remote_connection.commit()
                    except Exception as e:
                        logger.error(f"Update failed for batch: {e}")
                        remote_connection = get_remote_connection(
                            remote_engine
                        )  # Refresh for next

                logger.info(f"    Updated parent ids successfully.")
            except Exception as e:
                logger.error(f"    Error updating parent ids: {e}")

        # Close conn at end of table
        if remote_connection and not remote_connection.closed:
            remote_connection.close()

    logger.info("Migration completed.")


if __name__ == "__main__":
    migrate_database()
