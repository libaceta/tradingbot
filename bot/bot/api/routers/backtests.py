import asyncio
from datetime import date
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, Query, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.api.dependencies import get_db
from bot.backtest.runner import run_backtest
from bot.db.models import BacktestRun
from bot.db.repositories.backtest_repo import get_backtest_runs, get_leaderboard
from bot.db.repositories.trade_repo import get_trades

router = APIRouter()


class BacktestRunRequest(BaseModel):
    engine: str = "backtestingpy"
    symbol: str = "BTCUSDT"
    interval: str = "60"
    start_date: date
    end_date: date
    initial_capital: float = 10000.0
    params: Dict[str, Any] = {}
    param_ranges: Optional[Dict[str, List]] = None
    run_name: Optional[str] = None


@router.get("/backtests")
async def list_backtests(
    symbol: Optional[str] = None,
    engine: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size
    runs, total = await get_backtest_runs(db, symbol=symbol, engine=engine, offset=offset, limit=page_size)
    return {"items": [_run_to_dict(r, include_curves=False) for r in runs], "total": total, "page": page}


@router.get("/backtests/leaderboard")
async def leaderboard(
    symbol: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    runs = await get_leaderboard(db, symbol=symbol, limit=limit)
    return [_run_to_dict(r, include_curves=False) for r in runs]


@router.get("/backtests/{run_id}")
async def get_backtest(run_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BacktestRun).where(BacktestRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return _run_to_dict(run, include_curves=True)


@router.get("/backtests/{run_id}/status")
async def get_backtest_status(run_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BacktestRun).where(BacktestRun.id == run_id))
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Backtest run not found")
    return {"run_id": run_id, "status": run.status, "error_message": run.error_message}


@router.get("/backtests/{run_id}/trades")
async def get_backtest_trades(
    run_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    offset = (page - 1) * page_size
    trades, total = await get_trades(
        db,
        is_backtest=True,
        backtest_id=run_id,
        offset=offset,
        limit=page_size,
    )
    from bot.api.routers.trades import _trade_to_dict
    return {"items": [_trade_to_dict(t) for t in trades], "total": total, "page": page}


@router.post("/backtests/run")
async def trigger_backtest(
    req: BacktestRunRequest,
    background_tasks: BackgroundTasks,
):
    async def _run():
        await run_backtest(
            engine=req.engine,
            symbol=req.symbol,
            interval=req.interval,
            start_date=req.start_date,
            end_date=req.end_date,
            params=req.params,
            initial_capital=req.initial_capital,
            param_ranges=req.param_ranges,
            run_name=req.run_name,
        )

    background_tasks.add_task(_run)
    return {"status": "queued", "message": "Backtest started in background. Poll /backtests/{id}/status."}


def _run_to_dict(r: BacktestRun, include_curves: bool = True) -> dict:
    d = {
        "id": r.id,
        "run_name": r.run_name,
        "engine": r.engine,
        "symbol": r.symbol,
        "interval": r.interval,
        "start_date": str(r.start_date) if r.start_date else None,
        "end_date": str(r.end_date) if r.end_date else None,
        "initial_capital": float(r.initial_capital),
        "status": r.status,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        # Parameters
        "ema_fast": r.ema_fast,
        "ema_slow": r.ema_slow,
        "st_period": r.st_period,
        "st_multiplier": float(r.st_multiplier) if r.st_multiplier else None,
        "rsi_period": r.rsi_period,
        "rsi_ob": float(r.rsi_ob) if r.rsi_ob else None,
        "rsi_os": float(r.rsi_os) if r.rsi_os else None,
        # Metrics
        "total_trades": r.total_trades,
        "winning_trades": r.winning_trades,
        "losing_trades": r.losing_trades,
        "win_rate": float(r.win_rate) if r.win_rate else None,
        "total_return": float(r.total_return) if r.total_return else None,
        "annualized_return": float(r.annualized_return) if r.annualized_return else None,
        "max_drawdown": float(r.max_drawdown) if r.max_drawdown else None,
        "sharpe_ratio": float(r.sharpe_ratio) if r.sharpe_ratio else None,
        "sortino_ratio": float(r.sortino_ratio) if r.sortino_ratio else None,
        "calmar_ratio": float(r.calmar_ratio) if r.calmar_ratio else None,
        "profit_factor": float(r.profit_factor) if r.profit_factor else None,
        "avg_r_multiple": float(r.avg_r_multiple) if r.avg_r_multiple else None,
        "final_equity": float(r.final_equity) if r.final_equity else None,
        "total_fees_usdt": float(r.total_fees_usdt) if r.total_fees_usdt else None,
    }
    if include_curves:
        d["equity_curve"] = r.equity_curve
        d["monthly_returns"] = r.monthly_returns
    return d
