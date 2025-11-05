"""
Migration script to transfer Publishers and Insights from SQLite to PostgreSQL.

This script:
1. Reads Publishers and Insights from SQLite database (files/investment.db)
2. Transfers them to PostgreSQL database (via ix.db)
3. Handles PDF content for Insights by saving to Boto storage
"""

import sqlite3
import os
from datetime import datetime, date
from typing import Optional
from ix.db.conn import Session, ensure_connection
from ix.db.models import Publishers, Insights
from ix.db.boto import Boto


def migrate_publishers():
    """Migrate Publishers from SQLite to PostgreSQL."""
    sqlite_path = "files/investment.db"

    if not os.path.exists(sqlite_path):
        print(f"SQLite database not found at {sqlite_path}")
        return

    # Connect to SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    cursor = sqlite_conn.cursor()

    # Get all publishers from SQLite
    cursor.execute("SELECT * FROM publishers")
    sqlite_publishers = cursor.fetchall()

    print(f"Found {len(sqlite_publishers)} publishers in SQLite")

    # Ensure PostgreSQL connection
    ensure_connection()

    migrated_count = 0
    skipped_count = 0
    error_count = 0

    with Session() as session:
        # Get existing publishers by URL to check for duplicates
        existing_urls = {pub.url for pub in session.query(Publishers).all()}

    for row in sqlite_publishers:
        try:
            url = row["url"]

            # Skip if already exists
            if url in existing_urls:
                skipped_count += 1
                print(f"Skipping publisher (already exists): {row['name']} - {url}")
                continue

            # Parse last_visited datetime
            last_visited = None
            if row["last_visited"]:
                try:
                    if isinstance(row["last_visited"], str):
                        last_visited = datetime.fromisoformat(
                            row["last_visited"].replace("Z", "+00:00")
                        )
                    else:
                        last_visited = datetime.fromtimestamp(row["last_visited"])
                except Exception:
                    last_visited = datetime.now()

            # Create new publisher in PostgreSQL
            with Session() as session:
                new_publisher = Publishers(
                    url=url,
                    name=row["name"] or "Unnamed",
                    frequency=row["frequency"] or "Unclassified",
                    remark=row["remark"],
                    last_visited=last_visited or datetime.now(),
                )
                session.add(new_publisher)
                session.flush()  # Flush to get the ID if needed
                # Session context manager commits automatically

            migrated_count += 1
            if migrated_count % 10 == 0:
                print(f"Migrated {migrated_count} publishers...")

        except Exception as e:
            error_count += 1
            print(f"Error migrating publisher {row.get('name', 'Unknown')}: {e}")

    sqlite_conn.close()

    print(f"\nPublishers migration complete:")
    print(f"  Migrated: {migrated_count}")
    print(f"  Skipped (duplicates): {skipped_count}")
    print(f"  Errors: {error_count}")


def migrate_insights():
    """Migrate Insights from SQLite to PostgreSQL."""
    sqlite_path = "files/investment.db"

    if not os.path.exists(sqlite_path):
        print(f"SQLite database not found at {sqlite_path}")
        return

    # Connect to SQLite
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    cursor = sqlite_conn.cursor()

    # Get all insights from SQLite
    cursor.execute("SELECT * FROM insights")
    sqlite_insights = cursor.fetchall()

    print(f"\nFound {len(sqlite_insights)} insights in SQLite")

    # Ensure PostgreSQL connection
    ensure_connection()

    migrated_count = 0
    skipped_count = 0
    error_count = 0

    boto = Boto()

    with Session() as session:
        # Get existing insights by issuer+name+published_date to check for duplicates
        existing_insights = {
            (ins.issuer, ins.name, ins.published_date)
            for ins in session.query(Insights).all()
        }

    for row in sqlite_insights:
        try:
            issuer = row["issuer"] or "Unnamed"
            name = row["name"] or "Unnamed"

            # Parse published_date
            published_date = None
            if row["published_date"]:
                if isinstance(row["published_date"], str):
                    try:
                        published_date = datetime.strptime(
                            row["published_date"], "%Y-%m-%d"
                        ).date()
                    except:
                        published_date = date.today()
                else:
                    published_date = date.today()
            else:
                published_date = date.today()

            # Check for duplicate
            key = (issuer, name, published_date)
            if key in existing_insights:
                skipped_count += 1
                print(
                    f"Skipping insight (already exists): {issuer} - {name} - {published_date}"
                )
                continue

            # Create new insight in PostgreSQL
            with Session() as session:
                new_insight = Insights(
                    issuer=issuer,
                    name=name,
                    published_date=published_date,
                    summary=row["summary"],
                    status=row["status"] or "new",
                )
                session.add(new_insight)
                session.flush()  # Flush to get the ID
                insight_id = new_insight.id
                # Session context manager commits automatically

            # Save PDF content if it exists
            if row["content"]:
                try:
                    content_bytes = row["content"]
                    if isinstance(content_bytes, bytes) and len(content_bytes) > 0:
                        filename = f"{insight_id}.pdf"
                        if boto.save_pdf(pdf_content=content_bytes, filename=filename):
                            print(f"  Saved PDF content for insight {insight_id}")
                        else:
                            print(
                                f"  Warning: Failed to save PDF content for insight {insight_id}"
                            )
                except Exception as e:
                    print(
                        f"  Warning: Error saving PDF content for insight {insight_id}: {e}"
                    )

            migrated_count += 1
            if migrated_count % 50 == 0:
                print(f"Migrated {migrated_count} insights...")

        except Exception as e:
            error_count += 1
            print(f"Error migrating insight {row.get('name', 'Unknown')}: {e}")
            import traceback

            traceback.print_exc()

    sqlite_conn.close()

    print(f"\nInsights migration complete:")
    print(f"  Migrated: {migrated_count}")
    print(f"  Skipped (duplicates): {skipped_count}")
    print(f"  Errors: {error_count}")


def main():
    """Main migration function."""
    print("=" * 60)
    print("SQLite to PostgreSQL Migration")
    print("=" * 60)

    # Ensure PostgreSQL connection
    print("\nConnecting to PostgreSQL...")
    if not ensure_connection():
        print("ERROR: Failed to connect to PostgreSQL")
        return

    print("PostgreSQL connection established")

    # Migrate Publishers
    print("\n" + "=" * 60)
    print("Migrating Publishers...")
    print("=" * 60)
    migrate_publishers()

    # Migrate Insights
    print("\n" + "=" * 60)
    print("Migrating Insights...")
    print("=" * 60)
    migrate_insights()

    print("\n" + "=" * 60)
    print("Migration complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
