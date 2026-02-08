# Script to recreate the Charts table
import sys
import os

sys.path.append(os.getcwd())

from ix.db.conn import conn
from ix.db.models.chart import Chart


def recreate_charts_table():
    print("Connecting to database...")
    if not conn.connect():
        print("Failed to connect to database.")
        return

    print("Recreating Charts table...")
    try:
        # Drop existing table if exists
        Chart.__table__.drop(conn.engine, checkfirst=True)
        print("Dropped existing 'charts' table.")

        # Create new table
        Chart.__table__.create(conn.engine, checkfirst=True)
        print("Created new 'charts' table with updated schema.")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.disconnect()


if __name__ == "__main__":
    recreate_charts_table()
