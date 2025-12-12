import os
import sys
import io
import logging
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import Base explicitly to ensure models are registered
from ix.db.models import Insights, Timeseries, Universe, EconomicCalendar, TacticalView
from ix.db.conn import Session, ensure_connection, Base, conn
from ix.misc import PDFSummarizer, Settings, get_logger

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = get_logger(__name__)

# Constants
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
FOLDER_ID = '1jkpxtpaZophtkx5Lhvb-TAF9BuKY_pPa'
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'credentials.json')

def get_drive_service():
    """Authenticate and return Drive service."""
    if not os.path.exists(CREDENTIALS_FILE):
        logger.error(f"Credentials file not found at: {CREDENTIALS_FILE}")
        return None

    try:
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Failed to authenticate with Google Drive: {e}")
        return None

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
    except Exception:
        pass

    # Fallback
    return datetime.now().date(), "Unknown", filename

def ingest_from_drive():
    """Download and ingest PDFs from Google Drive."""
    service = get_drive_service()
    if not service:
        return

    logger.info(f"Connecting to Google Drive folder: {FOLDER_ID}")

    # List files in folder
    try:
        results = service.files().list(
            q=f"'{FOLDER_ID}' in parents and mimeType='application/pdf' and trashed=false",
            fields="files(id, name, size)",
            pageSize=100
        ).execute()
        items = results.get('files', [])
    except Exception as e:
        logger.error(f"Failed to list files: {e}")
        return

    if not items:
        logger.info("No PDF files found in the folder.")
        return

    logger.info(f"Found {len(items)} PDF files. Starting ingestion...")

    # DEBUG: Check if Insights is registered
    logger.info(f"Registered tables: {list(Base.metadata.tables.keys())}")

    ensure_connection()
    # Explicitly create tables to avoid "relation does not exist" error
    try:
        Base.metadata.create_all(bind=conn.engine)
        logger.info("Checked/Created DB tables.")
    except Exception as e:
        logger.error(f"Failed to create tables: {e}")


    # Initialize summarizer
    summarizer = None
    if hasattr(Settings, "openai_secret_key") and Settings.openai_secret_key:
        try:
            summarizer = PDFSummarizer(Settings.openai_secret_key)
            logger.info("AI Summarizer initialized")
        except Exception as e:
            logger.warning(f"Could not initialize summarizer: {e}")

    new_count = 0

    for item in items:
        file_id = item['id']
        filename = item['name']

        # Check if exists in DB
        published_date, issuer, title = parse_filename(filename)

        try:
            with Session() as session:
                existing = session.query(Insights).filter(Insights.name == title).first()
                if existing:
                    # logger.info(f"Skipping existing: {title}")
                    continue

                logger.info(f"Downloading: {filename}...")
                request = service.files().get_media(fileId=file_id)
                file_stream = io.BytesIO()
                downloader = MediaIoBaseDownload(file_stream, request)

                done = False
                while done is False:
                    status, done = downloader.next_chunk()

                content = file_stream.getvalue()

                # Create DB Record
                insight = Insights(
                    published_date=published_date,
                    issuer=issuer,
                    name=title,
                    status="processing",
                    pdf_content=content,
                )
                session.add(insight)
                session.flush()

                # Generate summary
                if summarizer:
                    try:
                        logger.info(f"Generating summary for {title}...")
                        summary_text = summarizer.process_insights(content)
                        insight.summary = summary_text
                        insight.status = "completed"
                    except Exception as e:
                        logger.error(f"Summary generation failed for {title}: {e}")
                        insight.status = "completed"
                else:
                    insight.status = "completed"

                session.commit()
                new_count += 1
                logger.info(f"Successfully ingested: {title}")

        except Exception as e:
            logger.error(f"Failed to process {filename}: {e}")

    logger.info(f"Ingestion complete. Added {new_count} new insights.")

if __name__ == "__main__":
    ingest_from_drive()
