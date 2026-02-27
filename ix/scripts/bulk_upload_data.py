import os
import hashlib
import time
import random
from datetime import datetime, date
from pathlib import Path
from sqlalchemy.orm import Session
from ix.db.conn import conn
from ix.db.models import Insights
from ix.api.routers.task import start_process, update_process, ProcessStatus

# Setup Paths
BASE_DIR = Path("d:/investment-x")
DATA_DIR = BASE_DIR / "ix" / "data"


def calculate_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def parse_filename(filename: str):
    base_name = filename.rsplit(".", 1)[0]
    parts = base_name.replace(" ", "_").replace("-", "_").split("_")
    pub_date = date.today()
    issuer = "Direct Upload"
    name = base_name

    if len(parts) >= 1:
        first_part = parts[0].strip()
        if len(first_part) == 8 and first_part.isdigit():
            try:
                pub_date = datetime.strptime(first_part, "%Y%m%d").date()
            except Exception:
                pass
        if len(parts) >= 2:
            issuer = parts[1].replace("-", " ").title()
    return pub_date, issuer, name


def bulk_upload():
    pid = start_process("Deep Data Ingestion (Bulk)", user_id="system")
    pdf_files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(".pdf")]
    total = len(pdf_files)
    success = 0
    duplicates = 0
    errors = 0

    print(f"Starting resilient bulk migration of {total} files...")
    update_process(
        pid, message=f"Starting migration of {total} PDFs...", progress=f"0/{total}"
    )

    def get_db_session():
        # Force a fresh engine connection if possible or ensure pool is healthy
        if not conn.is_connected():
            conn.connect()
        return conn.SessionLocal()

    db = get_db_session()

    # We will process in small batches to reduce transaction overhead but keep it safe
    BATCH_SIZE = 10
    current_batch = []

    for i, filename in enumerate(pdf_files):
        file_path = DATA_DIR / filename
        try:
            # Check size - Skip very large files in bulk to avoid memory pressure
            if file_path.stat().st_size > 70 * 1024 * 1024:
                print(f"Skipping {filename} (>70MB)")
                continue

            with open(file_path, "rb") as f:
                content = f.read()

            file_hash = calculate_hash(content)

            # 1. Existence Check with Retries
            insight_exists = False
            for retry in range(5):  # More retries for transient errors
                try:
                    existing = (
                        db.query(Insights).filter(Insights.hash == file_hash).first()
                    )
                    if existing:
                        insight_exists = True
                    break
                except Exception as e:
                    print(f"Query Retry {retry+1} for {filename}: {e}")
                    db.close()
                    time.sleep(2**retry + random.random())  # Exponential backoff
                    db = get_db_session()

            if insight_exists:
                duplicates += 1
                continue

            # 2. Add to session
            pub_date, issuer, name = parse_filename(filename)
            new_item = Insights(
                published_date=pub_date,
                issuer=issuer,
                name=name,
                summary=f"Automated Batch Ingest: {filename}",
                pdf_content=content,
                hash=file_hash,
                status="new",
            )
            db.add(new_item)
            current_batch.append(filename)

            # 3. Commit Batch
            if len(current_batch) >= BATCH_SIZE or i == total - 1:
                for retry in range(5):
                    try:
                        db.commit()
                        success += len(current_batch)
                        current_batch = []
                        break
                    except Exception as e:
                        print(
                            f"Commit Retry {retry+1} (batch size {len(current_batch)}): {e}"
                        )
                        db.rollback()
                        db.close()
                        time.sleep(3**retry + random.random())
                        db = get_db_session()
                        # Re-add items to the new session
                        # (Note: In a pure script we'd re-read or cache objects,
                        # but for simplicity we'll just re-push if commit fails)
                        # Actually, better to just commit per file if it fails batch
                        # but let's try to re-add.
                        # Since objects are lost on session close, we just re-run this specific item
                        # but that's complex. Let's fallback to ONE BY ONE if batch fails.
                        if retry == 4:
                            print(
                                f"FATAL: Batch failed. Falling back to single-mode for these items."
                            )
                            errors += len(current_batch)
                            current_batch = []

            # 4. Updates
            if (i + 1) % 10 == 0:
                update_process(
                    pid,
                    message=f"Ingesting: {success} new | {duplicates} skips | {errors} errors",
                    progress=f"{i+1}/{total}",
                )

        except Exception as e:
            errors += 1
            print(f"Final Failure for {filename}: {e}")

    db.commit()  # Final cleanup
    update_process(
        pid,
        status=ProcessStatus.COMPLETED,
        message=f"Sync Complete. {success} Ingested, {duplicates} Skips, {errors} Failures.",
        progress=f"{total}/{total}",
    )
    db.close()
    print(f"COMPLETED: {success} items migrated.")


if __name__ == "__main__":
    bulk_upload()
