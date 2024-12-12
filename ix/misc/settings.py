import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables
load_dotenv()


class Settings:
    db_url: Optional[str] = os.getenv("DATABASE_URL")
    db_name: Optional[str] = os.getenv("DATABASE_NAME")
    public_api_url: Optional[str] = os.getenv("PUBLIC_API_BASE_URL")
    r2_access_id: Optional[str] = os.getenv("R2_ACCESS_ID")
    r2_access_key: Optional[str] = os.getenv("R2_ACCESS_KEY")
    r2_account_id: Optional[str] = os.getenv("R2_CLIENT_ID")
    r2_bucket_name: Optional[str] = os.getenv("R2_BUCKET_NAME")
