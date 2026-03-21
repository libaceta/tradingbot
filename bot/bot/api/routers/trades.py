from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from bot.api.dependencies import get_db
from bot.db.repositories.trade_repo import get_trades

router = APIRouter()


@router.get("/trades")
async def list_trades(
    symbol: Optional[str] = None,
    status: Optional[str] = None,
    direction: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    is_backtest: bool = False,
    backtest_id: Optional[int] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size
    trades, total = await get_trades(
        db,
        symbol=symbol,
        status=status,
        direction=direction,
        date_from=date_from,
        date_to=date_to,
        is_backtest=is_backtest,
        backtest_id=backtest_id,
        offset=offset,
        limit=page_size,
    )

    items = [_trade_to_dict(t) for t in trades]
    pages = (total + page_size - 1) // page_size

    return {"items": items, "total": total, "page": page, "pages": pages}


@router.get("/trades/{trade_id}")
async def get_trade(trade_id: int, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from bot.db.models import Trade
    result = await db.execute(select(Trade).where(Trade.id == trade_id))
    trade = result.scalar_one_or_none()
    if not trade:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Trade not found")
    return _trade_to_dict(trade)


def _trade_to_dict(t) -> dict:
    return {
        "id": t.id,
        "external_id": t.external_id,
        "symbol": t.symbol,
        "direction": t.direction,
        "status": t.status,
        "entry_time": t.entry_time.isoformat() if t.entry_time else None,
        "exit_time": t.exit_time.isoformat() if t.exit_time else None,
        "entry_price": float(t.entry_price) if t.entry_price else None,
        "exit_price": float(t.exit_price) if t.exit_price else None,
        "quantity": float(t.quantity),
        "notional_usdt": float(t.notional_usdt) if t.notional_usdt else None,
        "stop_loss": float(t.stop_loss) if t.stop_loss else None,
        "take_profit": float(t.take_profit) if t.take_profit else None,
        "gross_pnl": float(t.gross_pnl) if t.gross_pnl else None,
        "net_pnl": float(t.net_pnl) if t.net_pnl else None,
        "pnl_pct": float(t.pnl_pct) if t.pnl_pct else None,
        "r_multiple": float(t.r_multiple) if t.r_multiple else None,
        "duration_secs": t.duration_secs,
        "exit_reason": t.exit_reason,
        "entry_fee": float(t.entry_fee) if t.entry_fee else None,
        "exit_fee": float(t.exit_fee) if t.exit_fee else None,
        "risk_usdt": float(t.risk_usdt) if t.risk_usdt else None,
        "atr_at_entry": float(t.atr_at_entry) if t.atr_at_entry else None,
        "is_backtest": t.is_backtest,
        "backtest_id": t.backtest_id,
        "signal_id": t.signal_id,
    }
