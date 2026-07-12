"""Environment and Docker-secret based application settings."""

from __future__ import annotations

import os
from pathlib import Path


def _read_secret(name: str, default: str = "") -> str:
    file_path = os.environ.get(f"{name}_FILE", "").strip()
    if file_path:
        try:
            return Path(file_path).read_text().strip()
        except OSError as exc:
            raise RuntimeError(f"Cannot read {name}_FILE: {exc}") from exc
    return os.environ.get(name, default).strip()


def _bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)))


def _ids(name: str, fallback: list[int] | None = None) -> list[int]:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return list(fallback or [])
    return [int(value.strip()) for value in raw.split(",") if value.strip()]


TELEGRAM_BOT_TOKEN = _read_secret("TELEGRAM_BOT_TOKEN")
TELEGRAM_BASE_URL = os.environ.get("TELEGRAM_BASE_URL", "").strip()
TELEGRAM_PROXY_URL = _read_secret("TELEGRAM_PROXY_URL")

ALLOWED_USER_IDS = _ids("ALLOWED_USER_IDS")
AUTH_RECIPIENT_IDS = _ids("AUTH_RECIPIENT_IDS", ALLOWED_USER_IDS)
BILLING_RECIPIENT_IDS = _ids("BILLING_RECIPIENT_IDS", ALLOWED_USER_IDS)
INCIDENT_RECIPIENT_IDS = _ids("INCIDENT_RECIPIENT_IDS", ALLOWED_USER_IDS)
GENERAL_RECIPIENT_IDS = _ids("GENERAL_RECIPIENT_IDS", ALLOWED_USER_IDS)
ADMIN_USER_IDS = _ids("ADMIN_USER_IDS", ALLOWED_USER_IDS)

GMAIL_CREDENTIALS_FILE = os.environ.get("GMAIL_CREDENTIALS_FILE", "credentials.json")
GMAIL_TOKEN_FILE = os.environ.get("GMAIL_TOKEN_FILE", "data/token.json")
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

ENABLE_CLAUDE_EMAILS = _bool("ENABLE_CLAUDE_EMAILS", True)
ENABLE_OPENAI_EMAILS = _bool("ENABLE_OPENAI_EMAILS", True)
ENABLE_BILLING_EMAILS = _bool("ENABLE_BILLING_EMAILS", True)
ENABLE_OPENAI_INCIDENTS = _bool("ENABLE_OPENAI_INCIDENTS", True)

CLAUDE_AUTH_GMAIL_QUERY = os.environ.get(
    "CLAUDE_AUTH_GMAIL_QUERY",
    'from:anthropic.com subject:"Secure link to log in" newer_than:1d is:unread',
)
CLAUDE_BILLING_GMAIL_QUERY = os.environ.get(
    "CLAUDE_BILLING_GMAIL_QUERY",
    'from:anthropic.com (subject:"payment" OR subject:"unsuccessful" OR '
    'subject:"receipt" OR subject:"invoice" OR subject:"paused") '
    "newer_than:2d is:unread",
)
OPENAI_AUTH_GMAIL_QUERY = os.environ.get(
    "OPENAI_AUTH_GMAIL_QUERY",
    "(from:openai.com OR from:tm.openai.com OR from:tm1.openai.com OR "
    'from:email.openai.com) subject:"Your authentication code" newer_than:1d is:unread',
)
OPENAI_BILLING_GMAIL_QUERY = os.environ.get(
    "OPENAI_BILLING_GMAIL_QUERY",
    "(from:openai.com OR from:tm.openai.com OR from:tm1.openai.com OR "
    'from:email.openai.com) (subject:"Your OpenAI API account has been funded" OR '
    'subject:"Your API usage limits have increased" OR subject:"ChatGPT" OR '
    'subject:"payment" OR subject:"billing" OR subject:"receipt" OR '
    'subject:"invoice" OR subject:"plan" OR subject:"subscription") '
    "newer_than:2d is:unread",
)

CHECK_INTERVAL = _int("CHECK_INTERVAL", 15)
STATUS_CHECK_INTERVAL = _int("STATUS_CHECK_INTERVAL", 60)
AUTH_EMAIL_MAX_AGE_SECONDS = _int("AUTH_EMAIL_MAX_AGE_SECONDS", 900)
BILLING_EMAIL_MAX_AGE_SECONDS = _int("BILLING_EMAIL_MAX_AGE_SECONDS", 172800)
DISPLAY_TIMEZONE = os.environ.get("DISPLAY_TIMEZONE", "Europe/Saratov")
LANGUAGE = os.environ.get("LANGUAGE", "ru")
OAUTH_PORT = _int("OAUTH_PORT", 8080)
OAUTH_BIND_HOST = os.environ.get("OAUTH_BIND_HOST", "127.0.0.1")

STATE_DB_FILE = os.environ.get("STATE_DB_FILE", "data/bot.db")
ADMIN_STATE_FILE = os.environ.get("ADMIN_STATE_FILE", "data/admin_state.json")
HEALTH_MAX_HEARTBEAT_AGE = _int("HEALTH_MAX_HEARTBEAT_AGE", 120)
HEALTH_MAX_GMAIL_AGE = _int("HEALTH_MAX_GMAIL_AGE", 300)
HEALTH_MAX_STATUS_AGE = _int("HEALTH_MAX_STATUS_AGE", 300)

OPENAI_STATUS_API_URL = os.environ.get(
    "OPENAI_STATUS_API_URL", "https://status.openai.com/api/v2/incidents.json"
)
OPENAI_STATUS_PAGE_URL = os.environ.get("OPENAI_STATUS_PAGE_URL", "https://status.openai.com")
