FROM python:3.11-slim

LABEL maintainer="deniskoleda"
LABEL description="Telegram bot for forwarding Claude.ai auth links"
LABEL version="1.0.0"

# Set working directory
WORKDIR /app

# Install dependencies first (better caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .
COPY gmail_monitor.py .
COPY telegram_bot.py .
COPY config.py .

# Create non-root user for security
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import telegram; print('OK')" || exit 1

# Run the bot
CMD ["python", "-u", "main.py"]
