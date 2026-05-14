# Copy this file to config.py and fill in your values
# cp config.example.py config.py

# Telegram settings
TELEGRAM_BOT_TOKEN = "YOUR_BOT_TOKEN_FROM_BOTFATHER"  # nosec B105
ALLOWED_USER_IDS = [123456789]  # Your Telegram user ID(s)

# Gmail settings
GMAIL_CREDENTIALS_FILE = "credentials.json"
GMAIL_TOKEN_FILE = "token.json"  # nosec B105
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]

# Filter for Claude/Anthropic emails
GMAIL_QUERY = 'from:anthropic.com (subject:"Secure link to log in" OR subject:"payment" OR subject:"unsuccessful" OR subject:"receipt" OR subject:"invoice" OR subject:"paused") is:unread'

# Check interval in seconds
CHECK_INTERVAL = 15

# Interface language: "ru" or "en"
LANGUAGE = "ru"

# Telegram API base URL (optional) — drop-in replacement for https://api.telegram.org/bot
# Useful when api.telegram.org is blocked. Example: https://relay.klsnv.ru/tg/bot
TELEGRAM_BASE_URL = ""

# Telegram proxy (optional), e.g. http://user:pass@proxy:8888
TELEGRAM_PROXY_URL = ""
