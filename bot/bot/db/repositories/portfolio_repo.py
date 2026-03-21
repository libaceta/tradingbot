from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import PortfolioSnapshot


async def save_snapshot(
    session: AsyncSession,
    snapshot_time: datetime,
    equity_usdt: float,
    available_usdt: float,
    unrealized_pnl: float = 0.0,
    realized_pnl_day: float = 0.0,
    open_positions: int = 0,
    peak_equity: Optional[float] = None,
    drawdown_pct: Optional[float] = None,
) -> PortfolioSnapshot:
    snap = PortfolioSnapshot(
        snapshot_time=snapshot_time,
        equity_usdt=equity_usdt,
        available_usdt=available_usdt,
        unrealized_pnl=unrealized_pnl,
        realized_pnl_day=realized_pnl_day,
        open_positions=open_positions,
        peak_equity=peak_equity,
        drawdown_pct=drawdown_pct,
    )
    session.add(snap)
    await session.flush()
    return snap


async def get_snapshots(
    session: AsyncSession,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    limit: int = 5000,
) -> List[PortfolioSnapshot]:
    stmt = select(PortfolioSnapshot).order_by(PortfolioSnapshot.snapshot_time)
    if date_from:
        stmt = stmt.where(PortfolioSnapshot.snapshot_time >= date_from)
    if date_to:
        stmt = stmt.where(PortfolioSnapshot.snapshot_time <= date_to)
    stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()


async def get_latest_snapshot(
    session: AsyncSession,
) -> Optional[PortfolioSnapshot]:
    stmt = (
        select(PortfolioSnapshot)
        .order_by(PortfolioSnapshot.snapshot_time.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()
