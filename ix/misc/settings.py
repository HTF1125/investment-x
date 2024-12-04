import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    db_url: str = os.getenv("DATABASE_URL", "mogodb://...")
    db_name: str = os.getenv("DATABASE_NAME", "investmentx")
    api_url: str = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
