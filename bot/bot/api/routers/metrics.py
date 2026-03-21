from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from bot.api.dependencies import get_db
from bot.db.models import Trade
from bot.backtest.metrics import (
    sharpe_ratio,
    sortino_ratio,
    max_drawdown,
    calmar_ratio,
    profit_factor,
    win_rate,
    avg_r_multiple,
)

router = APIRouter()


@router.get("/metrics/summary")
async def get_summary(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    symbol: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Trade).where(Trade.status == "CLOSED", Trade.is_backtest == False)
    if symbol:
        stmt = stmt.where(Trade.symbol == symbol)
    if date_from:
        stmt = stmt.where(Trade.entry_time >= date_from)
    if date_to:
        stmt = stmt.where(Trade.entry_time <= date_to)

    result = await db.execute(stmt)
    trades = result.scalars().all()

    if not trades:
        return {"total_trades": 0}

    net_pnls = [float(t.net_pnl) for t in trades if t.net_pnl is not None]
    r_mults = [float(t.r_multiple) for t in trades if t.r_multiple is not None]
    entry_times = [t.entry_time for t in trades if t.entry_time]
    exit_times = [t.exit_time for t in trades if t.exit_time]
    fees = sum((float(t.entry_fee or 0) + float(t.exit_fee or 0)) for t in trades)

    initial_capital = 10000.0  # Approximate — from earliest snapshot if available
    final_equity = initial_capital + sum(net_pnls)

    import pandas as pd
    import numpy as np

    if len(net_pnls) > 1:
        daily_returns = pd.Series(net_pnls) / initial_capital
        sharpe = sharpe_ratio(daily_returns, periods_per_year=len(net_pnls))
        sortino = sortino_ratio(daily_returns, periods_per_year=len(net_pnls))
        max_dd = 0
        equity_series = pd.Series([initial_capital + sum(net_pnls[:i+1]) for i in range(len(net_pnls))])
        max_dd = max_drawdown(equity_series)
    else:
        sharpe = sortino = max_dd = 0

    total_return = sum(net_pnls) / initial_capital * 100
    calmar = calmar_ratio(total_return, max_dd)
    pf = profit_factor(net_pnls)
    wr = win_rate(net_pnls)
    avg_r = avg_r_multiple(r_mults)

    avg_duration = 0
    if entry_times and exit_times:
        durations = [(e - s).total_seconds() for s, e in zip(entry_times, exit_times) if e and s]
        avg_duration = int(sum(durations) / len(durations)) if durations else 0

    best_trade = max(net_pnls) if net_pnls else 0
    worst_trade = min(net_pnls) if net_pnls else 0

    return {
        "total_trades": len(trades),
        "winning_trades": sum(1 for p in net_pnls if p > 0),
        "losing_trades": sum(1 for p in net_pnls if p <= 0),
        "win_rate": round(wr, 2),
        "profit_factor": round(pf, 4),
        "sharpe_ratio": round(sharpe, 4),
        "sortino_ratio": round(sortino, 4),
        "calmar_ratio": round(calmar, 4),
        "max_drawdown": round(max_dd, 4),
        "total_return": round(total_return, 4),
        "avg_r_multiple": round(avg_r, 4),
        "avg_trade_duration_secs": avg_duration,
        "total_fees_usdt": round(fees, 4),
        "best_trade_pnl": round(best_trade, 4),
        "worst_trade_pnl": round(worst_trade, 4),
        "total_pnl": round(sum(net_pnls), 4),
    }


@router.get("/metrics/by-symbol")
async def get_by_symbol(db: AsyncSession = Depends(get_db)):
    stmt = (
        select(
            Trade.symbol,
            func.count(Trade.id).label("trade_count"),
            func.sum(Trade.net_pnl).label("total_pnl"),
            func.avg(Trade.pnl_pct).label("avg_pnl_pct"),
        )
        .where(Trade.status == "CLOSED", Trade.is_backtest == False)
        .group_by(Trade.symbol)
    )
    result = await db.execute(stmt)
    rows = result.all()

    out = []
    for row in rows:
        out.append({
            "symbol": row.symbol,
            "trade_count": row.trade_count,
            "total_pnl": round(float(row.total_pnl or 0), 4),
            "avg_pnl_pct": round(float(row.avg_pnl_pct or 0), 4),
        })
    return out


@router.get("/metrics/by-month")
async def get_by_month(db: AsyncSession = Depends(get_db)):
    stmt = select(Trade).where(Trade.status == "CLOSED", Trade.is_backtest == False)
    result = await db.execute(stmt)
    trades = result.scalars().all()

    monthly: dict = {}
    for t in trades:
        if not t.entry_time or t.net_pnl is None:
            continue
        key = t.entry_time.strftime("%Y-%m")
        if key not in monthly:
            monthly[key] = {"pnl": 0, "count": 0, "wins": 0}
        monthly[key]["pnl"] += float(t.net_pnl)
        monthly[key]["count"] += 1
        if float(t.net_pnl) > 0:
            monthly[key]["wins"] += 1

    return [
        {
            "year_month": k,
            "pnl": round(v["pnl"], 4),
            "trade_count": v["count"],
            "win_rate": round(v["wins"] / v["count"] * 100, 2) if v["count"] else 0,
        }
        for k, v in sorted(monthly.items())
    ]
