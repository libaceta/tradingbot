from datetime import datetime
from typing import List, Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import OHLCV


async def get_ohlcv(
    session: AsyncSession,
    symbol: str,
    interval: str,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: Optional[int] = None,
) -> List[OHLCV]:
    stmt = (
        select(OHLCV)
        .where(OHLCV.symbol == symbol, OHLCV.interval == interval)
        .order_by(OHLCV.open_time)
    )
    if date_from:
        stmt = stmt.where(OHLCV.open_time >= date_from)
    if date_to:
        stmt = stmt.where(OHLCV.open_time <= date_to)
    if limit:
        stmt = stmt.limit(limit)

    result = await session.execute(stmt)
    return result.scalars().all()


async def get_ohlcv_as_dataframe(
    session: AsyncSession,
    symbol: str,
    interval: str,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> pd.DataFrame:
    rows = await get_ohlcv(session, symbol, interval, date_from, date_to)
    if not rows:
        return pd.DataFrame()

    data = [
        {
            "open_time": r.open_time,
            "open": float(r.open),
            "high": float(r.high),
            "low": float(r.low),
            "close": float(r.close),
            "volume": float(r.volume),
        }
        for r in rows
    ]
    df = pd.DataFrame(data)
    df["open_time"] = pd.to_datetime(df["open_time"], utc=True)
    df = df.set_index("open_time").sort_index()
    return df
