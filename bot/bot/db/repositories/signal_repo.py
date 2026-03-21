from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Signal
from bot.strategy.base import SignalResult


async def save_signal(
    session: AsyncSession,
    symbol: str,
    interval: str,
    signal_time: datetime,
    result: SignalResult,
    acted_on: bool = False,
    skip_reason: Optional[str] = None,
) -> Signal:
    signal = Signal(
        symbol=symbol,
        interval=str(interval),
        signal_time=signal_time,
        direction=result.direction,
        ema_21=result.ema_21,
        ema_55=result.ema_55,
        ema_cross=result.ema_cross,
        supertrend=result.supertrend,
        supertrend_dir=result.supertrend_dir,
        rsi=result.rsi,
        macd_line=result.macd_line,
        macd_signal=result.macd_signal,
        macd_hist=result.macd_hist,
        atr=result.atr,
        close_price=result.close_price,
        acted_on=acted_on,
        skip_reason=skip_reason or result.skip_reason,
    )
    session.add(signal)
    await session.flush()
    return signal


async def get_latest_signal(
    session: AsyncSession, symbol: str
) -> Optional[Signal]:
    stmt = (
        select(Signal)
        .where(Signal.symbol == symbol)
        .order_by(Signal.signal_time.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
