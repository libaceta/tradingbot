from datetime import datetime
from typing import List, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Trade


async def create_trade(
    session: AsyncSession,
    external_id: str,
    symbol: str,
    direction: str,
    quantity: float,
    entry_price: Optional[float] = None,
    entry_time: Optional[datetime] = None,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
    atr_at_entry: Optional[float] = None,
    risk_usdt: Optional[float] = None,
    notional_usdt: Optional[float] = None,
    signal_id: Optional[int] = None,
    is_backtest: bool = False,
    backtest_id: Optional[int] = None,
    entry_fee: Optional[float] = None,
    entry_fee_rate: Optional[float] = None,
) -> Trade:
    trade = Trade(
        external_id=external_id,
        symbol=symbol,
        direction=direction,
        status="OPEN",
        quantity=quantity,
        entry_price=entry_price,
        entry_time=entry_time,
        stop_loss=stop_loss,
        take_profit=take_profit,
        atr_at_entry=atr_at_entry,
        risk_usdt=risk_usdt,
        notional_usdt=notional_usdt,
        signal_id=signal_id,
        is_backtest=is_backtest,
        backtest_id=backtest_id,
        entry_fee=entry_fee,
        entry_fee_rate=entry_fee_rate,
    )
    session.add(trade)
    await session.flush()
    return trade


async def close_trade(
    session: AsyncSession,
    trade: Trade,
    exit_price: float,
    exit_time: datetime,
    exit_reason: str,
    exit_fee: Optional[float] = None,
) -> Trade:
    trade.exit_price = exit_price
    trade.exit_time = exit_time
    trade.exit_reason = exit_reason
    trade.exit_fee = exit_fee
    trade.status = "CLOSED"

    if trade.entry_price and trade.quantity:
        if trade.direction == "LONG":
            gross_pnl = (exit_price - trade.entry_price) * trade.quantity
        else:
            gross_pnl = (trade.entry_price - exit_price) * trade.quantity

        total_fees = (trade.entry_fee or 0) + (exit_fee or 0)
        net_pnl = gross_pnl - total_fees
        trade.gross_pnl = gross_pnl
        trade.net_pnl = net_pnl

        if trade.notional_usdt and trade.notional_usdt > 0:
            trade.pnl_pct = net_pnl / trade.notional_usdt * 100

        if trade.risk_usdt and trade.risk_usdt > 0:
            trade.r_multiple = net_pnl / trade.risk_usdt

        if trade.entry_time:
            trade.duration_secs = int((exit_time - trade.entry_time).total_seconds())

    session.add(trade)
    await session.flush()
    return trade


async def get_open_trade(
    session: AsyncSession, symbol: str
) -> Optional[Trade]:
    stmt = (
        select(Trade)
        .where(Trade.symbol == symbol, Trade.status == "OPEN", Trade.is_backtest == False)
        .order_by(Trade.created_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_all_open_trades(
    session: AsyncSession, symbol: str
) -> List[Trade]:
    """Return ALL open live trades for a symbol (used for reconciliation)."""
    stmt = (
        select(Trade)
        .where(Trade.symbol == symbol, Trade.status == "OPEN", Trade.is_backtest == False)
        .order_by(Trade.created_at.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_trades(
    session: AsyncSession,
    symbol: Optional[str] = None,
    status: Optional[str] = None,
    direction: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    is_backtest: bool = False,
    backtest_id: Optional[int] = None,
    offset: int = 0,
    limit: int = 50,
) -> tuple[List[Trade], int]:
    stmt = select(Trade).where(Trade.is_backtest == is_backtest)

    if symbol:
        stmt = stmt.where(Trade.symbol == symbol)
    if status:
        stmt = stmt.where(Trade.status == status)
    if direction:
        stmt = stmt.where(Trade.direction == direction)
    if date_from:
        stmt = stmt.where(Trade.entry_time >= date_from)
    if date_to:
        stmt = stmt.where(Trade.entry_time <= date_to)
    if backtest_id is not None:
        stmt = stmt.where(Trade.backtest_id == backtest_id)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await session.execute(count_stmt)
    total = total_result.scalar_one()

    stmt = stmt.order_by(Trade.entry_time.desc()).offset(offset).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all(), total
