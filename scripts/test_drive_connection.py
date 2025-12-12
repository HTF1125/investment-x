import os
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Config
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
CREDENTIALS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'credentials.json')
FOLDER_ID = '1jkpxtpaZophtkx5Lhvb-TAF9BuKY_pPa'

def test_connection():
    print(f"Checking credentials at: {CREDENTIALS_FILE}")
    if not os.path.exists(CREDENTIALS_FILE):
        print("ERROR: Credentials file not found!")
        return

    try:
        print("Authenticating...")
        creds = service_account.Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)

        # Test 1: Get Service Account Email
        about = service.about().get(fields="user").execute()
        email = about['user']['emailAddress']
        print(f"SUCCESS: Authenticated as {email}")

        # Test 2: Check Folder Access
        print(f"Checking access to folder: {FOLDER_ID}")
        try:
            folder = service.files().get(fileId=FOLDER_ID, fields="name").execute()
            print(f"SUCCESS: Can see folder '{folder.get('name')}'")
        except Exception as e:
            print(f"ERROR: Cannot access folder. Have you shared it with {email}?")
            print(f"Details: {e}")
            return

        # Test 3: List Files
        print("Listing PDF files...")
        results = service.files().list(
            q=f"'{FOLDER_ID}' in parents and mimeType='application/pdf' and trashed=false",
            fields="files(id, name, createdTime)",
            pageSize=10
        ).execute()
        files = results.get('files', [])

        print(f"Found {len(files)} files.")
        for f in files:
            print(f" - {f['name']} ({f['id']})")

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")

if __name__ == "__main__":
    test_connection()
