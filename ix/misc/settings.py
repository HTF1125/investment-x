import os
import warnings
from typing import List
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()


def _require_env(name: str) -> str:
    """Return env var value or raise on missing/empty."""
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(
            f"Required environment variable {name} is not set. "
            f"Check your .env file."
        )
    return value


class Settings:
    db_url: str = _require_env("DB_URL")
    db_name: str = os.getenv("DB_NAME", "")
    public_api_url: str = os.getenv("API_BASE_URL", "")
    r2_access_id: str = os.getenv("R2_ACCESS_ID", "")
    r2_access_key: str = os.getenv("R2_ACCESS_KEY", "")
    r2_account_id: str = os.getenv("R2_CLIENT_ID", "")
    r2_bucket_name: str = os.getenv("R2_BUCKET_NAME", "")
    secret_key: str = _require_env("SECRET_KEY")
    access_token_expire_minutes: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "600")
    )
    algorithm: str = "HS256"
    email_login: str = os.getenv("EMAIL_LOGIN", "")
    email_password: str = os.getenv("EMAIL_PASSWORD", "")
    email_recipients: List[str] = json.loads(os.getenv("EMAIL_RECIPIENTS", "[]"))
