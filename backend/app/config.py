"""Read local configuration without exposing credentials to the browser."""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / '.env')
FRONTEND_ORIGIN = os.getenv('FRONTEND_ORIGIN', 'http://localhost:5500').rstrip('/')
COOKIE_NAME = 'taskwell_session'
COOKIE_SECURE = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
SESSION_SECONDS = 60 * 60 * 24
RESET_SECONDS = 60 * 30

