import os
import sys
import base64
from datetime import datetime, date
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ix.db.conn import Session, ensure_connection
from ix.db.models import Insights
from ix.misc import PDFSummarizer, Settings, get_logger

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = get_logger(__name__)

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "insights")

def parse_filename(filename):
    """
    Parse filename to extract metadata.
    Expected format: YYYYMMDD_Issuer_Title.pdf
    """
    try:
        base_name = os.path.splitext(filename)[0]
        parts = base_name.split('_')

        if len(parts) >= 3:
            date_str = parts[0]
            issuer = parts[1]
            title = "_".join(parts[2:])

            published_date = datetime.strptime(date_str, "%Y%m%d").date()
            return published_date, issuer, title
    except Exception as e:
        logger.warning(f"Failed to parse filename '{filename}': {e}")

    # Fallback
    return date.today(), "Unknown", filename

def ingest_pdfs(directory):
    """Scan directory and ingest PDFs."""
    if not os.path.exists(directory):
        logger.error(f"Directory not found: {directory}")
        return

    logger.info(f"Scanning directory: {directory}")

    ensure_connection()
    session = Session()

    summarizer = None
    if hasattr(Settings, "openai_secret_key") and Settings.openai_secret_key:
        try:
            summarizer = PDFSummarizer(Settings.openai_secret_key)
            logger.info("AI Summarizer initialized")
        except Exception as e:
            logger.warning(f"Could not initialize summarizer: {e}")

    count = 0
    new_count = 0

    for filename in os.listdir(directory):
        if not filename.lower().endswith('.pdf'):
            continue

        count += 1
        filepath = os.path.join(directory, filename)

        # Check if already exists (simple check by name)
        # Note: Ideally we check hash, but name is faster for now
        published_date, issuer, title = parse_filename(filename)

        existing = session.query(Insights).filter(Insights.name == title).first()
        if existing:
            logger.info(f"Skipping existing: {title}")
            continue

        try:
            logger.info(f"Processing: {filename}")
            with open(filepath, "rb") as f:
                content = f.read()

            insight = Insights(
                published_date=published_date,
                issuer=issuer,
                name=title,
                status="processing",
                pdf_content=content,
            )
            session.add(insight)
            session.flush() # Get ID

            # Generate summary if possible
            if summarizer:
                try:
                    logger.info(f"Generating summary for {title}...")
                    summary_text = summarizer.process_insights(content)
                    insight.summary = summary_text
                    insight.status = "completed"
                except Exception as e:
                    logger.error(f"Summary generation failed for {title}: {e}")
                    insight.status = "completed" # Mark completed even if summary fails
            else:
                 insight.status = "completed"

            session.commit()
            new_count += 1
            logger.info(f"Successfully ingested: {title}")

        except Exception as e:
            logger.error(f"Failed to ingest {filename}: {e}")
            session.rollback()

    logger.info(f"Ingestion complete. Found {count} files, Added {new_count} new insights.")

if __name__ == "__main__":
    # Create directory if it doesn't exist
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        logger.info(f"Created data directory: {DATA_DIR}")
        print(f"Please place your PDF files in: {DATA_DIR}")
    else:
        ingest_pdfs(DATA_DIR)
