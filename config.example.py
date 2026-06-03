# Copy this file to config.py and fill in your values
# cp config.example.py config.py

# Telegram settings
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_FROM_BOTFATHER"  # nosec B105
ALLOWED_USER_IDS = [123456789]  # Your Telegram user ID(s)
ADMIN_USER_IDS = [123456789]  # User ID(s) allowed to use /admin and broadcasts

# Gmail settings
GMAIL_CREDENTIALS_FILE = "credentials.json"
GMAIL_TOKEN_FILE = "token.json"  # nosec B105
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# Enable providers independently
ENABLE_CLAUDE_EMAILS = True
ENABLE_OPENAI_EMAILS = True
ADMIN_STATE_FILE = "data/admin_state.json"  # nosec B105

# Filters for auth/billing emails
CLAUDE_GMAIL_QUERY = 'from:anthropic.com (subject:"Secure link to log in" OR subject:"payment" OR subject:"unsuccessful" OR subject:"receipt" OR subject:"invoice" OR subject:"paused") is:unread'
OPENAI_GMAIL_QUERY = '(from:openai.com OR from:tm.openai.com OR from:tm1.openai.com OR from:email.openai.com) (subject:"Your authentication code" OR subject:"Your OpenAI API account has been funded" OR subject:"Your API usage limits have increased" OR subject:"ChatGPT" OR subject:"payment" OR subject:"billing" OR subject:"receipt" OR subject:"invoice" OR subject:"plan" OR subject:"subscription") newer_than:180d is:unread'
OPENAI_STATUS_GMAIL_QUERY = 'from:status.incident.io (OpenAI OR ChatGPT OR Codex OR API OR Sora OR DALL-E OR "DALL·E" OR error OR errors OR outage OR degraded OR incident) newer_than:180d is:unread'

# Backward-compatible fallback. Used only if provider-specific query is missing.
GMAIL_QUERY = CLAUDE_GMAIL_QUERY

# Check interval in seconds
CHECK_INTERVAL = 15

# Interface language: "ru" or "en"
LANGUAGE = "ru"

# Telegram API base URL (optional) — drop-in replacement for https://api.telegram.org/bot
# Useful when api.telegram.org is blocked. Example: https://relay.klsnv.ru/tg/bot
TELEGRAM_BASE_URL = ""

# Telegram proxy (optional), e.g. http://user:pass@proxy:8888
TELEGRAM_PROXY_URL = ""
