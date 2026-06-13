"""ZimHub Stage 1 — Flask configuration.

Note: SYSTEM_CONFIG is the runtime-mutable bag of operational settings
(HOLD_HOURS, DEMO_MODE, etc.) read/written via /api/super/config.
We keep it in-memory + DB-backed via a dedicated row pattern would be cleaner,
but for Stage 1 a module-level dict mutated by the super admin endpoint is fine
and matches the spec ("Default config values defined in config.py, overridable
via env or the config endpoint").
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


def _bool(value, default=False):
    if value is None:
        return default
    return str(value).lower() in ('1', 'true', 'yes', 'on')


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 'postgresql+psycopg2://postgres:Mqhe2026@localhost:5432/zimhub_dev'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT in httpOnly cookies — see spec §5.1
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'dev-jwt-secret-change-me')
    JWT_TOKEN_LOCATION = ['cookies']
    JWT_ACCESS_COOKIE_NAME = 'access_token_cookie'
    JWT_COOKIE_HTTPONLY = True
    JWT_COOKIE_SECURE = _bool(os.environ.get('JWT_COOKIE_SECURE'), default=False)
    JWT_COOKIE_SAMESITE = 'Lax'
    JWT_COOKIE_CSRF_PROTECT = False  # We use SameSite=Lax + CORS allowlist; no separate CSRF token this stage.
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)
    JWT_ACCESS_COOKIE_PATH = '/'

    # CORS — allow the Vite dev server with credentials.
    CORS_ORIGINS = [
        origin.strip()
        for origin in os.environ.get('CORS_ORIGINS', 'http://localhost:5173').split(',')
        if origin.strip()
    ]

    # Frontend URL used in mock-dispatched emails / WhatsApp links.
    FRONTEND_BASE_URL = os.environ.get('FRONTEND_BASE_URL', 'http://localhost:5173')


# Default runtime-mutable system config — see spec §5.6.
# Mutated via PUT /api/super/config. Read via host.config(key).
SYSTEM_CONFIG = {
    'HOLD_HOURS': 24,
    'SETTLE_HOURS': 72,
    'DEFAULT_CURRENCY': 'USD',
    'DEMO_MODE': _bool(os.environ.get('DEMO_MODE'), default=True),
    'EVENT_MODERATION': False,
    'RESPONSE_HOURS': None,
    'CANCEL_CUTOFF_HOURS': 0,
    'DEFAULT_TIMEZONE': 'Africa/Harare',
}
