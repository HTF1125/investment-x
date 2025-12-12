import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from google.oauth2 import service_account
from googleapiclient.discovery import build
from ix.misc import get_logger

logger = get_logger(__name__)

# Config
SCOPES = ['https://www.googleapis.com/auth/drive.file']
# Path: ix/web/pages/insights/services/drive_client.py -> ... -> investment-x/credentials.json
# We need to go up 6 levels to get to project root from here
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_current_dir))))))
# Actually, let's be safer and assume CWD is project root as is standard in this app
CREDENTIALS_FILE = os.path.abspath("credentials.json")
FOLDER_ID = '1jkpxtpaZophtkx5Lhvb-TAF9BuKY_pPa'

class DriveClient:
    _instance = None
    _service = None
    _cache: Dict[str, Any] = {}
    _cache_expiry: Dict[str, datetime] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DriveClient, cls).__new__(cls)
        return cls._instance

    def _get_service(self):
        """Get or create Drive service."""
        if self._service:
            return self._service

        if not os.path.exists(CREDENTIALS_FILE):
            logger.error(f"Credentials file not found at: {CREDENTIALS_FILE}")
            return None

        try:
            creds = service_account.Credentials.from_service_account_file(
                CREDENTIALS_FILE, scopes=SCOPES)
            self._service = build('drive', 'v3', credentials=creds)
            logger.info("Successfully connected to Google Drive API")
            return self._service
        except Exception as e:
            logger.error(f"Failed to authenticate with Google Drive: {e}")
            return None

    def list_files(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """List files from the specific folder with caching."""
        cache_key = "files_list"
        now = datetime.now()

        # Return cached if valid
        if not force_refresh and cache_key in self._cache and self._cache_expiry.get(cache_key, datetime.min) > now:
            return self._cache[cache_key]

        service = self._get_service()
        if not service:
            return []

        try:
            results = service.files().list(
                q=f"'{FOLDER_ID}' in parents and mimeType='application/pdf' and trashed=false",
                fields="files(id, name, createdTime, webViewLink, size, mimeType)",
                pageSize=100,
                orderBy="createdTime desc"
            ).execute()

            files = results.get('files', [])

            # Update cache (5 minute TTL)
            self._cache[cache_key] = files
            self._cache_expiry[cache_key] = now + timedelta(minutes=5)

            return files
        except Exception as e:
            logger.error(f"Failed to list files from Drive: {e}")
            return []

    def upload_file(self, filename: str, file_content: bytes, mime_type: str = 'application/pdf') -> Dict[str, Any]:
        """Upload a file to the configured Google Drive folder."""
        service = self._get_service()
        if not service:
            raise Exception("No Drive service available")

        try:
            from googleapiclient.http import MediaIoBaseUpload
            import io

            file_metadata = {
                'name': filename,
                'parents': [FOLDER_ID]
            }

            media = MediaIoBaseUpload(
                io.BytesIO(file_content),
                mimetype=mime_type,
                resumable=True
            )

            file = service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink'
            ).execute()

            # Invalidate cache to show new file immediately
            self._cache = {}

            return file

        except Exception as e:
            logger.error(f"Error uploading file to Drive: {e}")
            raise e

drive_client = DriveClient()
