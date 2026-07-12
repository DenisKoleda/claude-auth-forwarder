# Claude/OpenAI Auth Forwarder

Telegram-бот для безопасной пересылки кодов входа Claude/OpenAI, уведомлений об оплате и инцидентов OpenAI Status.

## Возможности

- Gmail OAuth без пароля от почты;
- отдельные получатели кодов, платежей и инцидентов;
- TTL для кодов входа: старые письма не пересылаются;
- повтор доставки отдельно для каждого получателя;
- один обновляемый пост на каждый инцидент OpenAI;
- `/admin` для независимого включения источников;
- `/status` с реальным состоянием Gmail, OpenAI Status и основного цикла;
- Docker secrets для Telegram-токена и прокси;
- healthcheck по фактическому прогрессу приложения.

## Архитектура

```text
Gmail API ── auth/billing ──┐
                            ├── SQLite delivery state ── Telegram
OpenAI Status JSON API ─────┘
```

Gmail опрашивается каждые 15 секунд. OpenAI Status — каждые 60 секунд. Обновления одного инцидента редактируют уже отправленное Telegram-сообщение.

## Настройка

1. Скопируйте конфигурацию:

   ```bash
   cp .env.example .env
   chmod 600 .env
   ```

2. Укажите Telegram ID в `.env`. Получателей можно разделить:

   ```dotenv
   AUTH_RECIPIENT_IDS=123456789
   BILLING_RECIPIENT_IDS=123456789,987654321
   INCIDENT_RECIPIENT_IDS=123456789,987654321
   ADMIN_USER_IDS=123456789
   ```

3. Создайте файлы секретов:

   ```bash
   mkdir -p secrets
   printf '%s' 'BOT_TOKEN' > secrets/telegram_bot_token
   printf '%s' 'http://user:password@proxy:8080' > secrets/telegram_proxy_url
   chmod 600 secrets/*
   ```

   Если прокси не нужен, оставьте `secrets/telegram_proxy_url` пустым.

4. Положите Google OAuth Desktop credentials в `credentials.json` и ограничьте права:

   ```bash
   chmod 600 credentials.json
   ```

5. Запустите:

   ```bash
   docker compose up -d --build
   docker compose logs -f
   ```

## Первая авторизация Gmail

OAuth-порт публикуется только на `127.0.0.1` сервера. Для удалённого сервера откройте туннель:

```bash
ssh -L 8080:127.0.0.1:8080 user@server
```

После этого откройте `http://localhost:8080`. Callback принимается только с корректным OAuth `state`.

Токен Gmail сохраняется в `data/token.json` с правами `0600`.

## Команды Telegram

- `/admin` — независимо включить коды Claude, коды OpenAI, платежи и инциденты;
- `/status` — время последнего успешного Gmail/Status poll и heartbeat;
- `/broadcast текст` — сообщение всем пользователям из `ALLOWED_USER_IDS`.

## Проверки

```bash
pytest -q
ruff check .
ruff format --check .
mypy . --ignore-missing-imports
bandit -q main.py gmail_monitor.py telegram_bot.py telegram_admin.py \
  admin_state.py settings.py secure_files.py state_store.py status_monitor.py healthcheck.py
pip-audit -r requirements.txt
docker compose config
docker build -t claude-auth-forwarder:test .
```

## Данные и секреты

В Git и Docker build context не попадают:

- `.env`;
- `config.py` от старых установок;
- `credentials.json`;
- `data/`;
- `secrets/`.

После перехода со старой версии удалите legacy `config.py` с сервера только после проверки нового контейнера.
