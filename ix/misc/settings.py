import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    db_url: str = os.getenv("DATABASE_URL", "")
    db_name: str = os.getenv("DATABASE_NAME", "")
    public_api_url: str = os.getenv("PUBLIC_API_BASE_URL", "")
    r2_access_id: str = os.getenv("R2_ACCESS_ID", "")
    r2_access_key: str = os.getenv("R2_ACCESS_KEY", "")
    r2_account_id: str = os.getenv("R2_CLIENT_ID", "")
    r2_bucket_name: str = os.getenv("R2_BUCKET_NAME", "")
    secret_key: str = os.getenv("SECRET_KEY", "")
    access_token_expire_minutes: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "600")
    )
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    openai_secret_key: str = os.getenv("OPENAI_SECRET_KEY", "")
