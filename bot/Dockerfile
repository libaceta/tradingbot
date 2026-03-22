FROM python:3.11-slim AS base

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create reports dir
RUN mkdir -p backtest_reports

# Startup script (runs migrations then starts bot)
COPY scripts/start.sh /start.sh
RUN chmod +x /start.sh

# Default command: migrate + run bot
CMD ["/start.sh"]
