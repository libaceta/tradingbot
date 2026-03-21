"""
Fetch historical OHLCV data from Bybit and store in the database.
Used for seeding the DB before backtesting and for warm-up on bot start.
"""
import asyncio
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.dialects.postgresql import insert as pg_insert

from bot.db.engine import get_session
from bot.db.models import OHLCV
from bot.exchange.bybit_client import get_http_client
from bot.utils.logging import get_logger
from bot.utils.time_utils import datetime_to_ms

logger = get_logger(__name__)

# Bybit max limit per request
BYBIT_MAX_LIMIT = 200


async def fetch_and_store_historical(
    symbol: str,
    interval: str,
    start_dt: datetime,
    end_dt: Optional[datetime] = None,
) -> int:
    """
    Fetch all OHLCV data between start_dt and end_dt and upsert into DB.
    Returns total rows inserted/updated.
    """
    if end_dt is None:
        end_dt = datetime.now(timezone.utc)

    client = get_http_client()
    total_inserted = 0
    current_start = start_dt

    logger.info(
        "historical_fetch_start",
        symbol=symbol,
        interval=interval,
        start=start_dt.isoformat(),
        end=end_dt.isoformat(),
    )

    interval_minutes = int(interval)
    batch_duration = timedelta(minutes=interval_minutes * BYBIT_MAX_LIMIT)

    while current_start < end_dt:
        start_ms = datetime_to_ms(current_start)
        # Limit end_ms to a batch window so Bybit returns the oldest candles first
        batch_end = min(current_start + batch_duration, end_dt)
        end_ms = datetime_to_ms(batch_end)

        rows = await asyncio.to_thread(
            client.get_klines,
            symbol=symbol,
            interval=interval,
            start=start_ms,
            end=end_ms,
            limit=BYBIT_MAX_LIMIT,
        )

        if not rows:
            break

        async with get_session() as session:
            stmt = pg_insert(OHLCV).values([
                {
                    "symbol": symbol,
                    "interval": interval,
                    "open_time": row["open_time"],
                    "open": row["open"],
                    "high": row["high"],
                    "low": row["low"],
                    "close": row["close"],
                    "volume": row["volume"],
                    "turnover": row["turnover"],
                }
                for row in rows
            ])
            stmt = stmt.on_conflict_do_update(
                constraint="uq_ohlcv_sym_int_time",
                set_={
                    "open": stmt.excluded.open,
                    "high": stmt.excluded.high,
                    "low": stmt.excluded.low,
                    "close": stmt.excluded.close,
                    "volume": stmt.excluded.volume,
                    "turnover": stmt.excluded.turnover,
                },
            )
            await session.execute(stmt)

        total_inserted += len(rows)
        last_time = rows[-1]["open_time"]
        logger.info(
            "historical_fetch_batch",
            symbol=symbol,
            rows=len(rows),
            last_time=last_time.isoformat(),
            total=total_inserted,
        )

        # Advance window past the last fetched candle
        current_start = last_time + timedelta(minutes=interval_minutes)

        # Small delay to respect rate limits
        await asyncio.sleep(0.2)

    logger.info(
        "historical_fetch_complete",
        symbol=symbol,
        total_inserted=total_inserted,
    )
    return total_inserted


async def get_latest_ohlcv_time(symbol: str, interval: str) -> Optional[datetime]:
    """Return the most recent open_time in the DB for this symbol+interval."""
    async with get_session() as session:
        result = await session.execute(
            text(
                "SELECT MAX(open_time) FROM ohlcv WHERE symbol = :symbol AND interval = :interval"
            ),
            {"symbol": symbol, "interval": interval},
        )
        val = result.scalar_one_or_none()
        return val
