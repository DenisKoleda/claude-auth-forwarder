<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/Telegram-Bot-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram">
  <img src="https://img.shields.io/badge/Gmail-API-EA4335?style=for-the-badge&logo=gmail&logoColor=white" alt="Gmail">
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
</p>

<h1 align="center">Claude Auth Forwarder</h1>

<p align="center">
  <b>Telegram bot that forwards Claude.ai authentication links from your Gmail inbox</b>
</p>

<p align="center">
  <img src="https://img.shields.io/github/license/deniskoleda/claude-auth-forwarder?style=flat-square" alt="License">
  <img src="https://img.shields.io/github/stars/deniskoleda/claude-auth-forwarder?style=flat-square" alt="Stars">
  <img src="https://img.shields.io/github/issues/deniskoleda/claude-auth-forwarder?style=flat-square" alt="Issues">
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square" alt="PRs Welcome">
</p>

---

## Features

- **Instant notifications** - Get Claude auth links in Telegram within seconds
- **Magic link extraction** - Automatically extracts login links from emails
- **Code support** - Also supports 6-digit verification codes
- **Multi-user** - Send notifications to multiple Telegram users
- **Docker ready** - Easy deployment with Docker Compose
- **Secure** - Uses OAuth 2.0 for Gmail API access

## How it works

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐
│   Gmail     │────▶│   Bot        │────▶│   Telegram   │
│  (OAuth)    │     │  (polling)   │     │   (you)      │
└─────────────┘     └──────────────┘     └──────────────┘
```

1. Bot monitors your Gmail inbox every 15 seconds
2. When a new email from Anthropic arrives, it extracts the magic link
3. Sends the link to your Telegram instantly
4. Marks the email as read

## Quick Start

### Prerequisites

- Python 3.10+
- Gmail account
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Google Cloud Project with Gmail API enabled

### Installation

**1. Clone the repository**

```bash
git clone https://github.com/deniskoleda/claude-auth-forwarder.git
cd claude-auth-forwarder
```

**2. Set up virtual environment**

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows
```

**3. Install dependencies**

```bash
pip install -r requirements.txt
```

**4. Configure**

Create `credentials.json` from Google Cloud Console:
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop App)
5. Download JSON and rename to `credentials.json`

Edit `config.py`:
```python
TELEGRAM_BOT_TOKEN = "your_bot_token"
ALLOWED_USER_IDS = [your_telegram_id]
```

**5. Run**

```bash
python main.py
```

On first run, a browser window will open for Gmail authorization.

## Docker Deployment

### Using Docker Compose (Recommended)

```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

### Using Docker directly

```bash
# Build
docker build -t claude-auth-forwarder .

# Run
docker run -d \
  --name claude-auth-bot \
  -v $(pwd)/credentials.json:/app/credentials.json \
  -v $(pwd)/token.json:/app/token.json \
  claude-auth-forwarder
```

> **Note:** You need to run locally first to generate `token.json`, then copy it to your server.

## Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Your Telegram bot token | - |
| `ALLOWED_USER_IDS` | List of Telegram user IDs | - |
| `CHECK_INTERVAL` | Email check interval (seconds) | `15` |
| `GMAIL_QUERY` | Gmail search filter | `from:anthropic.com OR from:claude.ai is:unread` |

## Getting Your Telegram ID

Send a message to [@userinfobot](https://t.me/userinfobot) - it will reply with your ID.

## Project Structure

```
claude-auth-forwarder/
├── main.py              # Entry point
├── gmail_monitor.py     # Gmail API integration
├── telegram_bot.py      # Telegram notifications
├── config.py            # Configuration
├── credentials.json     # Google OAuth credentials
├── token.json           # Saved Gmail token (auto-generated)
├── requirements.txt     # Python dependencies
├── Dockerfile           # Docker image
├── docker-compose.yml   # Docker Compose config
└── README.md
```

## Security Notes

- Never commit `credentials.json` or `token.json` to git
- Use environment variables for sensitive data in production
- The bot only reads emails, it cannot send or delete them

## Contributing

Pull requests are welcome! For major changes, please open an issue first.

## License

[MIT](LICENSE)

---

<p align="center">
  Made with Claude Code
</p>
