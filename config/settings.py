import os
from typing import Optional
from dotenv import load_dotenv
 
# Load environment variables from .env file (override system env vars)
load_dotenv(override=True)
 
class Settings:
    """Application settings loaded from environment variables."""
   
    # API Configuration
    API_SERVER_URL: str = os.getenv("API_SERVER_URL", "http://localhost:8000")
    API_SERVER_DESCRIPTION: str = os.getenv("API_SERVER_DESCRIPTION", "Agent Hub Manager Service API")
    FASTAPI_PORT: int = int(os.getenv("FASTAPI_PORT", "8000"))


