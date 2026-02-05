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
GMAIL_QUERY = 'from:anthropic.com (subject:"Secure link to log in" OR subject:"payment" OR subject:"unsuccessful") is:unread'

# Check interval in seconds
CHECK_INTERVAL = 15

# Interface language: "ru" or "en"
LANGUAGE = "ru"
