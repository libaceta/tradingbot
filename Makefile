.PHONY: up down build migrate backtest logs shell-bot shell-db test clean

# Start all services
up:
	docker-compose up -d

# Start in foreground with logs
up-logs:
	docker-compose up

# Stop all services
down:
	docker-compose down

# Stop and remove volumes (WARNING: destroys data)
down-volumes:
	docker-compose down -v

# Build images
build:
	docker-compose build --no-cache

# Run database migrations
migrate:
	docker-compose exec bot alembic upgrade head

# Downgrade one migration
migrate-down:
	docker-compose exec bot alembic downgrade -1

# Fetch historical OHLCV data (seed DB)
fetch-data:
	docker-compose exec bot python scripts/fetch_historical.py

# Run VectorBT optimization backtest
backtest-optimize:
	docker-compose exec bot python scripts/run_backtest.py --engine vectorbt --symbol BTCUSDT --optimize

# Run detailed single backtest
backtest-detail:
	docker-compose exec bot python scripts/run_backtest.py --engine backtestingpy --symbol BTCUSDT

# Follow bot logs
logs:
	docker-compose logs -f bot

# Follow all logs
logs-all:
	docker-compose logs -f

# Shell into bot container
shell-bot:
	docker-compose exec bot bash

# Shell into db container
shell-db:
	docker-compose exec db psql -U trader tradingbot

# Run tests
test:
	docker-compose exec bot pytest bot/tests/ -v

# Run tests with coverage
test-cov:
	docker-compose exec bot pytest bot/tests/ -v --cov=bot --cov-report=html

# Clean Python cache
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; \
	find . -name "*.pyc" -delete 2>/dev/null; \
	echo "Cleaned"

# Show service status
status:
	docker-compose ps
