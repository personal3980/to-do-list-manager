"""Read local configuration without exposing credentials to the browser."""
import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / '.env')
FRONTEND_ORIGIN = os.getenv('FRONTEND_ORIGIN', 'http://localhost:5500').rstrip('/')
# Treat the two standard loopback names consistently without allowing arbitrary
# origins or broadening a deployed site's CORS policy.
FRONTEND_ORIGINS = {FRONTEND_ORIGIN}
parts = urlsplit(FRONTEND_ORIGIN)
if parts.hostname in {'localhost', '127.0.0.1'}:
    alias = '127.0.0.1' if parts.hostname == 'localhost' else 'localhost'
    netloc = f'{alias}:{parts.port}' if parts.port else alias
    FRONTEND_ORIGINS.add(urlunsplit((parts.scheme, netloc, '', '', '')))
COOKIE_NAME = 'taskwell_session'
COOKIE_SECURE = os.getenv('COOKIE_SECURE', 'false').lower() == 'true'
SESSION_SECONDS = 60 * 60 * 24
RESET_SECONDS = 60 * 30

