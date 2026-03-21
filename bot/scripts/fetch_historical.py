"""
Seed the database with historical OHLCV data from Bybit.
Usage: python scripts/fetch_historical.py
"""
import asyncio
import sys
from datetime import datetime, timezone, timedelta

sys.path.insert(0, "/app")

from bot.config.settings import settings
from bot.data.historical import fetch_and_store_historical, get_latest_ohlcv_time
from bot.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


async def main():
    configure_logging(settings.log_level, "pretty")

    symbol = settings.trade_symbol
    interval = str(settings.trade_interval)

    # Check if we already have recent data
    latest = await get_latest_ohlcv_time(symbol, interval)
    if latest and (datetime.now(timezone.utc) - latest) < timedelta(hours=2):
        logger.info("data_already_fresh", latest=latest.isoformat())
        return

    # Fetch 2 years of history
    start_dt = datetime.now(timezone.utc) - timedelta(days=730)
    if latest and latest > start_dt:
        start_dt = latest + timedelta(minutes=int(interval))
        logger.info("resuming_from", start=start_dt.isoformat())

    total = await fetch_and_store_historical(
        symbol=symbol,
        interval=interval,
        start_dt=start_dt,
    )
    logger.info("fetch_complete", total_rows=total)


if __name__ == "__main__":
    asyncio.run(main())
