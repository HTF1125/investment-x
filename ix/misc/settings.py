import os
from typing import List
from dotenv import load_dotenv
import ast

# Load environment variables
load_dotenv()

class Settings:
    db_url: str = os.getenv("DB_URL", "")
    db_name: str = os.getenv("DB_NAME", "")
    public_api_url: str = os.getenv("API_BASE_URL", "")
    r2_access_id: str = os.getenv("R2_ACCESS_ID", "")
    r2_access_key: str = os.getenv("R2_ACCESS_KEY", "")
    r2_account_id: str = os.getenv("R2_CLIENT_ID", "")
    r2_bucket_name: str = os.getenv("R2_BUCKET_NAME", "")
    secret_key: str = os.getenv("SECRET_KEY", "")
    access_token_expire_minutes: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "600")
    )
    algorithm: str = "HS256"
    openai_secret_key: str = os.getenv("OPENAI_API_KEY", "")
    email_login: str = os.getenv("EMAIL_LOGIN", "")
    email_password: str = os.getenv("EMAIL_PASSWORD", "")
    email_recipients: List[str] = ast.literal_eval(os.getenv("EMAIL_RECIPIENTS", "[]"))
