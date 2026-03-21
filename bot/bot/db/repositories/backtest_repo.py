from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import BacktestRun


async def create_backtest_run(
    session: AsyncSession,
    engine: str,
    symbol: str,
    interval: str,
    start_date: date,
    end_date: date,
    initial_capital: float,
    params: Dict[str, Any],
    run_name: Optional[str] = None,
) -> BacktestRun:
    run = BacktestRun(
        run_name=run_name,
        engine=engine,
        symbol=symbol,
        interval=str(interval),
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        ema_fast=params.get("ema_fast"),
        ema_slow=params.get("ema_slow"),
        st_period=params.get("st_period"),
        st_multiplier=params.get("st_multiplier"),
        rsi_period=params.get("rsi_period"),
        rsi_ob=params.get("rsi_ob"),
        rsi_os=params.get("rsi_os"),
        macd_fast=params.get("macd_fast"),
        macd_slow=params.get("macd_slow"),
        macd_signal=params.get("macd_signal"),
        atr_sl_mult=params.get("atr_sl_mult"),
        atr_tp_mult=params.get("atr_tp_mult"),
        risk_per_trade=params.get("risk_per_trade"),
        parameters_json=params,
        status="pending",
    )
    session.add(run)
    await session.flush()
    return run


async def update_backtest_results(
    session: AsyncSession,
    run: BacktestRun,
    metrics: Dict[str, Any],
    equity_curve: List[Dict],
    monthly_returns: Dict[str, float],
) -> BacktestRun:
    from datetime import datetime, timezone

    for key, value in metrics.items():
        if hasattr(run, key):
            setattr(run, key, value)

    run.equity_curve = equity_curve
    run.monthly_returns = monthly_returns
    run.status = "done"
    run.completed_at = datetime.now(timezone.utc)
    session.add(run)
    await session.flush()
    return run


async def get_backtest_runs(
    session: AsyncSession,
    symbol: Optional[str] = None,
    engine: Optional[str] = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[List[BacktestRun], int]:
    from sqlalchemy import func

    stmt = select(BacktestRun)
    if symbol:
        stmt = stmt.where(BacktestRun.symbol == symbol)
    if engine:
        stmt = stmt.where(BacktestRun.engine == engine)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(BacktestRun.created_at.desc()).offset(offset).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all(), total


async def get_leaderboard(
    session: AsyncSession,
    symbol: Optional[str] = None,
    limit: int = 20,
) -> List[BacktestRun]:
    stmt = (
        select(BacktestRun)
        .where(BacktestRun.status == "done", BacktestRun.sharpe_ratio.isnot(None))
    )
    if symbol:
        stmt = stmt.where(BacktestRun.symbol == symbol)
    stmt = stmt.order_by(BacktestRun.sharpe_ratio.desc()).limit(limit)
    result = await session.execute(stmt)
    return result.scalars().all()
