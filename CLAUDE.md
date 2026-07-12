# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Claude/OpenAI Auth Forwarder** — Telegram bot for Claude/OpenAI authentication, billing notifications, and OpenAI Status incidents. Written in Python 3.11+ with asyncio and SQLite delivery state.

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt   # includes production deps

# Run the bot
python main.py

# Linting & formatting
ruff check .            # lint
ruff check --fix .      # lint with auto-fix
ruff format .           # format
ruff format --check .   # check formatting without changes

# Type checking
mypy . --ignore-missing-imports

# Security scanning
bandit -q main.py gmail_monitor.py telegram_bot.py telegram_admin.py admin_state.py \
  settings.py secure_files.py state_store.py status_monitor.py healthcheck.py
pip-audit -r requirements.txt

# Docker
docker-compose up -d
docker-compose logs -f
```

## Architecture

The bot runs independent Gmail, OpenAI Status, and heartbeat loops:

- **`main.py`** — Entry point and concurrent loops. Blocking Gmail API calls run through `asyncio.to_thread`; retries use bounded exponential backoff.

- **`gmail_monitor.py`** — Gmail OAuth, auth/billing queries, MIME parsing, and message TTL enforcement.

- **`telegram_bot.py`** — Per-audience delivery, retry ledger integration, and editable incident cards.

- **`status_monitor.py`** — Direct polling of the official OpenAI Status JSON API.

- **`state_store.py`** — SQLite state for delivery attempts, incident Telegram message IDs, and health timestamps.

- **`settings.py`** — Environment/Docker-secret configuration. Production secrets are never copied into the image.

- **`i18n.py`** — Translation system (EN/RU). All user-facing strings go through `t(key, **kwargs)`.

## Key Conventions

- **Config as module**: settings are loaded from environment and `*_FILE` Docker secrets by `settings.py`
- **Tests**: pytest regression tests cover security and delivery boundaries
- **Ruff rules**: E, W, F, I, B, C4, UP, SIM enabled; line length 100; E501 ignored (handled by formatter)
- **Mypy**: strict mode with `ignore_missing_imports = true`
- **Bandit**: B101 (assert_used) skipped
- **OAuth tokens**: stored in `data/token.json` with mode `0600`; `credentials.json` is mounted read-only
- **Docker**: runs as non-root `botuser`; OAuth port is published only on host loopback
