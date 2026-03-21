"""
Backtest runner orchestrator.
Coordinates data loading, engine execution, and DB persistence.
"""
import asyncio
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional

from bot.backtest.backtestingpy_engine import run_backtestingpy
from bot.backtest.vectorbt_engine import run_vectorbt_optimization
from bot.config.settings import settings
from bot.db.engine import get_session
from bot.db.repositories.backtest_repo import (
    create_backtest_run,
    update_backtest_results,
)
from bot.db.repositories.ohlcv_repo import get_ohlcv_as_dataframe
from bot.db.repositories.trade_repo import create_trade
from bot.utils.logging import get_logger

logger = get_logger(__name__)


async def run_backtest(
    engine: str,
    symbol: str,
    interval: str,
    start_date: date,
    end_date: date,
    params: Dict[str, Any],
    initial_capital: float = 10000.0,
    commission: float = 0.00055,
    optimize: bool = False,
    param_ranges: Optional[Dict] = None,
    run_name: Optional[str] = None,
) -> int:
    """
    Main entry point for running a backtest.
    Returns the backtest_run ID.
    """
    # Create DB record
    async with get_session() as session:
        run = await create_backtest_run(
            session,
            engine=engine,
            symbol=symbol,
            interval=str(interval),
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            params=params,
            run_name=run_name or f"{engine}_{symbol}_{start_date}",
        )
        run_id = run.id
        run.status = "running"
        run.started_at = datetime.now(timezone.utc)

    # Load OHLCV data from DB
    start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)

    async with get_session() as session:
        df = await get_ohlcv_as_dataframe(session, symbol, str(interval), start_dt, end_dt)

    if df.empty:
        async with get_session() as session:
            from sqlalchemy import select
            from bot.db.models import BacktestRun
            result = await session.execute(select(BacktestRun).where(BacktestRun.id == run_id))
            run = result.scalar_one()
            run.status = "failed"
            run.error_message = "No OHLCV data found. Run fetch_historical.py first."
        logger.error("backtest_no_data", symbol=symbol, interval=interval)
        return run_id

    logger.info("backtest_data_loaded", rows=len(df), symbol=symbol)

    try:
        if engine == "vectorbt":
            top_results = await asyncio.to_thread(
                run_vectorbt_optimization,
                df=df,
                param_ranges=param_ranges,
                initial_capital=initial_capital,
                commission=commission,
                top_n=20,
                fixed_params=params,
            )

            # Save each top result as a separate backtest_run
            for i, result_params in enumerate(top_results):
                run_name_i = f"vbt_opt_{symbol}_{start_date}_rank{i+1}"
                async with get_session() as session:
                    opt_run = await create_backtest_run(
                        session,
                        engine="vectorbt",
                        symbol=symbol,
                        interval=str(interval),
                        start_date=start_date,
                        end_date=end_date,
                        initial_capital=initial_capital,
                        params=result_params,
                        run_name=run_name_i,
                    )
                    metrics = {
                        "total_trades": result_params.get("total_trades"),
                        "win_rate": result_params.get("win_rate"),
                        "total_return": result_params.get("total_return"),
                        "max_drawdown": result_params.get("max_drawdown"),
                        "sharpe_ratio": result_params.get("sharpe_ratio"),
                    }
                    await update_backtest_results(
                        session, opt_run, metrics,
                        equity_curve=[],
                        monthly_returns={},
                    )

            # Update the main run record as done
            async with get_session() as session:
                from sqlalchemy import select
                from bot.db.models import BacktestRun
                result = await session.execute(select(BacktestRun).where(BacktestRun.id == run_id))
                run = result.scalar_one()
                run.status = "done"
                run.completed_at = datetime.now(timezone.utc)
                if top_results:
                    run.sharpe_ratio = top_results[0].get("sharpe_ratio")

            logger.info("vectorbt_runs_saved", count=len(top_results))

        elif engine == "backtestingpy":
            result = await asyncio.to_thread(
                run_backtestingpy,
                df=df,
                params=params,
                initial_capital=initial_capital,
                commission=commission,
            )

            metrics = result["metrics"]
            equity_curve = result["equity_curve"]
            monthly_returns = result["monthly_returns"]
            trades = result["trades"]

            async with get_session() as session:
                from sqlalchemy import select
                from bot.db.models import BacktestRun
                res = await session.execute(select(BacktestRun).where(BacktestRun.id == run_id))
                run = res.scalar_one()
                await update_backtest_results(
                    session, run, metrics, equity_curve, monthly_returns
                )

            # Save individual trades
            async with get_session() as session:
                for t in trades:
                    await create_trade(
                        session,
                        external_id=t["external_id"],
                        symbol=symbol,
                        direction=t["direction"],
                        quantity=t["quantity"],
                        entry_price=t["entry_price"],
                        entry_time=t["entry_time"],
                        notional_usdt=t["notional_usdt"],
                        risk_usdt=t["risk_usdt"],
                        is_backtest=True,
                        backtest_id=run_id,
                        entry_fee=t["entry_fee"],
                    )

            logger.info(
                "backtestingpy_run_saved",
                run_id=run_id,
                trades=len(trades),
                sharpe=metrics.get("sharpe_ratio"),
            )

    except Exception as e:
        logger.error("backtest_error", run_id=run_id, error=str(e))
        async with get_session() as session:
            from sqlalchemy import select
            from bot.db.models import BacktestRun
            result = await session.execute(select(BacktestRun).where(BacktestRun.id == run_id))
            run = result.scalar_one()
            run.status = "failed"
            run.error_message = str(e)

    return run_id
