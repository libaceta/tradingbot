"""
Live WebSocket kline feed.
Maintains a rolling in-memory buffer of the last N candles and
emits closed candle events to registered async callbacks.
"""
import asyncio
from collections import deque
from datetime import datetime
from typing import Any, Callable, Deque, Dict, List, Optional

import pandas as pd

from bot.config.settings import settings
from bot.db.engine import get_session
from bot.db.models import OHLCV
from bot.exchange.bybit_client import get_ws_client, get_http_client
from bot.utils.logging import get_logger
from bot.utils.time_utils import datetime_to_ms

logger = get_logger(__name__)

BUFFER_SIZE = 300  # Keep last 300 candles in memory (enough for EMA55 warmup + more)


class KlineFeed:
    """
    Manages a rolling buffer of OHLCV candles for one symbol+interval.
    On each confirmed candle close: persists to DB and calls registered callbacks.
    """

    def __init__(self, symbol: str, interval: str) -> None:
        self.symbol = symbol
        self.interval = interval
        self._buffer: Deque[Dict] = deque(maxlen=BUFFER_SIZE)
        self._callbacks: List[Callable] = []
        self._ws = get_ws_client()
        self._initialized = False

    def on_candle(self, callback: Callable) -> None:
        """Register an async callback to be called on each closed candle."""
        self._callbacks.append(callback)

    async def initialize(self) -> None:
        """Load last BUFFER_SIZE candles from DB into the buffer."""
        client = get_http_client()
        rows = await asyncio.to_thread(
            client.get_klines,
            symbol=self.symbol,
            interval=self.interval,
            limit=BUFFER_SIZE,
        )
        for row in rows:
            self._buffer.append(row)
        self._initialized = True
        logger.info(
            "feed_initialized",
            symbol=self.symbol,
            interval=self.interval,
            candles=len(self._buffer),
        )

    async def start(self) -> None:
        """Start WebSocket subscription. pybit runs the WS in a background daemon thread."""
        if not self._initialized:
            await self.initialize()

        self._ws.subscribe_kline(self._on_closed_candle)
        loop = asyncio.get_running_loop()
        await asyncio.to_thread(
            self._ws.start,
            symbol=self.symbol,
            interval=self.interval,
            loop=loop,
        )

    async def _on_closed_candle(self, candle: Dict) -> None:
        """Called by WebSocket when a candle closes."""
        self._buffer.append(candle)

        # Persist to DB
        try:
            async with get_session() as session:
                from sqlalchemy.dialects.postgresql import insert as pg_insert
                stmt = pg_insert(OHLCV).values(
                    symbol=candle["symbol"],
                    interval=candle["interval"],
                    open_time=candle["open_time"],
                    open=candle["open"],
                    high=candle["high"],
                    low=candle["low"],
                    close=candle["close"],
                    volume=candle["volume"],
                    turnover=candle.get("turnover"),
                ).on_conflict_do_update(
                    constraint="uq_ohlcv_sym_int_time",
                    set_={
                        "close": candle["close"],
                        "high": candle["high"],
                        "low": candle["low"],
                        "volume": candle["volume"],
                    },
                )
                await session.execute(stmt)
        except Exception as e:
            logger.error("feed_db_persist_error", error=str(e))

        # Notify subscribers
        for cb in self._callbacks:
            try:
                await cb(candle, self.to_dataframe())
            except Exception as e:
                logger.error("feed_callback_error", error=str(e))

    def to_dataframe(self) -> pd.DataFrame:
        """Return the current buffer as a pandas DataFrame."""
        if not self._buffer:
            return pd.DataFrame()
        df = pd.DataFrame(list(self._buffer))
        df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
        df = df.sort_values("open_time").reset_index(drop=True)
        for col in ("open", "high", "low", "close", "volume"):
            df[col] = pd.to_numeric(df[col], errors="coerce")
        return df

    def stop(self) -> None:
        self._ws.stop()
