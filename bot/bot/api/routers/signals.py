from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.api.dependencies import get_db
from bot.db.models import Signal

router = APIRouter()


@router.get("/signals")
async def list_signals(
    symbol: Optional[str] = None,
    acted_on: Optional[bool] = None,
    date_from: Optional[datetime] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Signal)
    if symbol:
        stmt = stmt.where(Signal.symbol == symbol)
    if acted_on is not None:
        stmt = stmt.where(Signal.acted_on == acted_on)
    if date_from:
        stmt = stmt.where(Signal.signal_time >= date_from)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    offset = (page - 1) * page_size
    stmt = stmt.order_by(Signal.signal_time.desc()).offset(offset).limit(page_size)
    result = await db.execute(stmt)
    signals = result.scalars().all()

    return {
        "items": [_signal_to_dict(s) for s in signals],
        "total": total,
        "page": page,
    }


@router.get("/signals/latest")
async def get_latest(symbol: str = Query(default="BTCUSDT"), db: AsyncSession = Depends(get_db)):
    from bot.db.repositories.signal_repo import get_latest_signal
    sig = await get_latest_signal(db, symbol)
    if not sig:
        return None
    return _signal_to_dict(sig)


def _signal_to_dict(s) -> dict:
    return {
        "id": s.id,
        "symbol": s.symbol,
        "interval": s.interval,
        "signal_time": s.signal_time.isoformat() if s.signal_time else None,
        "direction": s.direction,
        "ema_21": float(s.ema_21) if s.ema_21 else None,
        "ema_55": float(s.ema_55) if s.ema_55 else None,
        "ema_cross": s.ema_cross,
        "supertrend": float(s.supertrend) if s.supertrend else None,
        "supertrend_dir": s.supertrend_dir,
        "rsi": float(s.rsi) if s.rsi else None,
        "macd_line": float(s.macd_line) if s.macd_line else None,
        "macd_signal": float(s.macd_signal) if s.macd_signal else None,
        "macd_hist": float(s.macd_hist) if s.macd_hist else None,
        "atr": float(s.atr) if s.atr else None,
        "close_price": float(s.close_price) if s.close_price else None,
        "acted_on": s.acted_on,
        "skip_reason": s.skip_reason,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }
