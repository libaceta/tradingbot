"""
Trading Bot Main Entry Point.

Responsibilities:
1. Initialize DB connection + run Alembic migrations
2. Start KlineFeed (WebSocket + buffer)
3. On each closed candle: evaluate strategy → risk check → execute orders → log to DB
4. Take portfolio snapshots on schedule
5. Start FastAPI server (REST + WebSocket)
"""
import asyncio
import uuid
from datetime import datetime, timezone

import uvicorn
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import bot.state as state
from bot.config.settings import settings
from bot.data.feed import KlineFeed
from bot.db.engine import get_session
from bot.db.repositories import portfolio_repo, signal_repo, trade_repo
from bot.exchange.bybit_client import get_http_client
from bot.risk.position_sizer import calculate_position_size
from bot.utils.logging import configure_logging, get_logger

logger = get_logger(__name__)


async def reconcile_open_trades(symbol: str, candle_time: datetime, candle_close: float) -> None:
    """
    Detect trades that were auto-closed by Bybit (SL/TP hit) but not yet recorded in DB.
    If DB has OPEN trades but Bybit has no active position → close ALL of them in DB.
    Uses Bybit closed PnL history for exit price; falls back to candle close price.
    """
    # Check if Bybit still has an active position — if yes, nothing to reconcile
    bybit_position = state.position_manager.get_position(symbol)
    if bybit_position:
        return

    # Bybit has no position — check if DB has any open trades
    async with get_session() as session:
        open_trades = await trade_repo.get_all_open_trades(session, symbol)

    if not open_trades:
        return  # DB and Bybit are in sync

    logger.info("reconcile_detected_orphan_trades", symbol=symbol, count=len(open_trades))

    # Try to get the real exit price from Bybit closed PnL history
    exit_price = 0.0
    exit_reason = "SL_TP_HIT"
    try:
        closed_pnl_list = await asyncio.to_thread(
            get_http_client().get_closed_pnl, symbol, 5
        )
        if closed_pnl_list:
            latest = closed_pnl_list[0]
            exit_price = float(latest.get("avgExitPrice") or latest.get("exitPrice") or 0)
    except Exception as e:
        logger.error("reconcile_closed_pnl_error", error=str(e))

    # Fallback: use current candle close price
    if exit_price <= 0:
        exit_price = candle_close
        exit_reason = "RECONCILED"
        logger.warning("reconcile_using_candle_close", symbol=symbol, price=exit_price)

    # Close ALL orphan open trades
    from bot.api.event_bus import bus
    async with get_session() as session:
        open_trades = await trade_repo.get_all_open_trades(session, symbol)
        for trade in open_trades:
            # Determine exit reason based on SL/TP levels
            reason = exit_reason
            if exit_reason != "RECONCILED" and trade.stop_loss:
                if trade.direction == "LONG":
                    if exit_price <= trade.stop_loss * 1.002:
                        reason = "STOP_LOSS"
                    elif trade.take_profit and exit_price >= trade.take_profit * 0.998:
                        reason = "TAKE_PROFIT"
                else:
                    if exit_price >= trade.stop_loss * 0.998:
                        reason = "STOP_LOSS"
                    elif trade.take_profit and exit_price <= trade.take_profit * 1.002:
                        reason = "TAKE_PROFIT"

            exit_fee = (exit_price * trade.quantity * settings.backtest_commission
                        if trade.quantity else None)
            await trade_repo.close_trade(
                session,
                trade,
                exit_price=exit_price,
                exit_time=candle_time,
                exit_reason=reason,
                exit_fee=exit_fee,
            )
            logger.info(
                "reconcile_trade_closed",
                symbol=symbol,
                trade_id=trade.id,
                exit_price=exit_price,
                reason=reason,
            )
            await bus.publish("trade_close", {"symbol": symbol, "reason": reason})


async def on_candle(candle: dict, df) -> None:
    """Called on every confirmed closed candle by the KlineFeed."""
    if not state.bot_running or settings.trading_mode == "paused":
        return

    symbol = settings.trade_symbol
    interval = str(settings.trade_interval)
    candle_time = candle.get("open_time", datetime.now(timezone.utc))

    # Refresh positions + balance
    await state.position_manager.refresh()
    equity = state.position_manager.equity
    state.guard.update_positions(state.position_manager.open_count())

    # Reconcile: detect trades auto-closed by Bybit (SL/TP) not yet in DB
    await reconcile_open_trades(symbol, candle_time, float(candle.get("close", 0)))

    # Evaluate strategy
    signal = state.strategy.evaluate(df)

    # Log signal to DB
    async with get_session() as session:
        db_signal = await signal_repo.save_signal(
            session,
            symbol=symbol,
            interval=interval,
            signal_time=candle_time,
            result=signal,
        )

    # Check if we should exit an existing position
    existing = state.position_manager.get_position(symbol)
    if existing:
        side = existing["side"]
        if side == "Buy":
            should_exit, reason = state.strategy.should_exit_long(df, existing)
        elif side == "Sell":
            should_exit, reason = state.strategy.should_exit_short(df, existing)
        else:
            should_exit, reason = False, ""

        if should_exit:
            logger.info("exit_signal", symbol=symbol, reason=reason)
            close_side = "Sell" if side == "Buy" else "Buy"
            try:
                await asyncio.to_thread(
                    state.order_manager.close_position,
                    symbol=symbol,
                    qty=existing["size"],
                    side=close_side,
                )
                logger.info("position_closed_on_exchange", symbol=symbol)
            except Exception as e:
                # Position may have already been closed by SL/TP — log and continue
                logger.warning("close_position_failed", symbol=symbol, error=str(e))

            # Always refresh and close DB trade if position is gone
            await state.position_manager.refresh()
            if not state.position_manager.get_position(symbol):
                async with get_session() as session:
                    open_trade = await trade_repo.get_open_trade(session, symbol)
                    if open_trade:
                        await trade_repo.close_trade(
                            session,
                            open_trade,
                            exit_price=float(candle["close"]),
                            exit_time=candle_time,
                            exit_reason=reason,
                        )
                from bot.api.event_bus import bus
                await bus.publish("trade_close", {"symbol": symbol, "reason": reason})
                logger.info("db_trade_closed", symbol=symbol, reason=reason)
        return

    # No existing position — check for entry signal
    if signal.direction == "NONE":
        return

    can_trade, block_reason = state.guard.can_trade(equity)
    if not can_trade:
        logger.info("trade_blocked", reason=block_reason)
        async with get_session() as session:
            await signal_repo.save_signal(
                session,
                symbol=symbol,
                interval=interval,
                signal_time=candle_time,
                result=signal,
                acted_on=False,
                skip_reason=block_reason,
            )
        return

    # Get instrument info for qty step
    try:
        info = await asyncio.to_thread(state.order_manager.get_instrument_info, symbol)
        qty_step = float(info.get("lotSizeFilter", {}).get("qtyStep", 0.001))
    except Exception:
        qty_step = 0.001

    entry_price = float(candle["close"])
    sizing = calculate_position_size(
        equity_usdt=equity,
        entry_price=entry_price,
        atr=signal.atr or 0,
        qty_step=qty_step,
    )

    if not sizing:
        logger.warning("sizing_failed", symbol=symbol)
        return

    # Execute order
    try:
        if signal.direction == "LONG":
            result = await asyncio.to_thread(
                state.order_manager.open_long,
                symbol=symbol,
                qty=sizing["quantity"],
                stop_loss=sizing["long_sl"],
                take_profit=sizing["long_tp"],
            )
        else:  # SHORT
            result = await asyncio.to_thread(
                state.order_manager.open_short,
                symbol=symbol,
                qty=sizing["quantity"],
                stop_loss=sizing["short_sl"],
                take_profit=sizing["short_tp"],
            )

        order_id = result.get("orderId", str(uuid.uuid4()))

        async with get_session() as session:
            trade = await trade_repo.create_trade(
                session,
                external_id=order_id,
                symbol=symbol,
                direction=signal.direction,
                quantity=sizing["quantity"],
                entry_price=entry_price,
                entry_time=candle_time,
                stop_loss=sizing[f"{'long' if signal.direction == 'LONG' else 'short'}_sl"],
                take_profit=sizing[f"{'long' if signal.direction == 'LONG' else 'short'}_tp"],
                atr_at_entry=signal.atr,
                risk_usdt=sizing["risk_usdt"],
                notional_usdt=sizing["notional_usdt"],
                signal_id=db_signal.id,
                entry_fee_rate=settings.backtest_commission,
            )

        from bot.api.event_bus import bus
        await bus.publish(
            "trade_open",
            {
                "trade_id": trade.id,
                "symbol": symbol,
                "direction": signal.direction,
                "entry_price": entry_price,
            },
        )
        logger.info(
            "trade_opened",
            symbol=symbol,
            direction=signal.direction,
            qty=sizing["quantity"],
            entry=entry_price,
        )

    except Exception as e:
        logger.error("order_execution_error", symbol=symbol, error=str(e))


async def take_portfolio_snapshot() -> None:
    """Scheduled task: capture portfolio state."""
    await state.position_manager.refresh()
    equity = state.position_manager.equity
    if equity <= 0:
        return

    if equity > state.peak_equity:
        state.peak_equity = equity
    drawdown_pct = (state.peak_equity - equity) / state.peak_equity * 100 if state.peak_equity > 0 else 0

    async with get_session() as session:
        await portfolio_repo.save_snapshot(
            session,
            snapshot_time=datetime.now(timezone.utc),
            equity_usdt=equity,
            available_usdt=state.position_manager.available,
            unrealized_pnl=state.position_manager.unrealized_pnl,
            open_positions=state.position_manager.open_count(),
            peak_equity=state.peak_equity,
            drawdown_pct=drawdown_pct,
        )

    from bot.api.event_bus import bus
    await bus.publish(
        "portfolio",
        {
            "equity_usdt": equity,
            "drawdown_pct": drawdown_pct,
            "open_positions": state.position_manager.open_count(),
        },
    )


async def scheduled_reconcile() -> None:
    """Scheduled reconciliation: closes orphan DB trades every 5 minutes."""
    symbol = settings.trade_symbol
    try:
        await state.position_manager.refresh()
        # Use 0.0 as price hint — reconcile will fetch from Bybit or use last known price
        async with get_session() as session:
            open_trades = await trade_repo.get_all_open_trades(session, symbol)
        if not open_trades:
            return
        bybit_position = state.position_manager.get_position(symbol)
        if bybit_position:
            return
        # Orphan trades detected — get last known price from Bybit
        try:
            klines = await asyncio.to_thread(
                get_http_client().get_klines, symbol, str(settings.trade_interval), limit=1
            )
            last_price = float(klines[-1]["close"]) if klines else 0.0
        except Exception:
            last_price = 0.0
        if last_price > 0:
            now = datetime.now(timezone.utc)
            await reconcile_open_trades(symbol, now, last_price)
            logger.info("scheduled_reconcile_ran", symbol=symbol, price=last_price)
    except Exception as e:
        logger.error("scheduled_reconcile_error", error=str(e))


async def run_bot() -> None:
    logger.info("bot_starting", mode=settings.trading_mode, symbol=settings.trade_symbol)

    await state.position_manager.refresh()
    equity = state.position_manager.equity
    state.peak_equity = equity
    state.guard.initialize(equity)

    feed = KlineFeed(settings.trade_symbol, str(settings.trade_interval))
    feed.on_candle(on_candle)
    await feed.initialize()

    state.bot_running = True
    state.bot_start_time = datetime.now(timezone.utc)
    logger.info("bot_started", equity=equity)

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        take_portfolio_snapshot,
        "interval",
        seconds=settings.snapshot_interval_secs,
        id="portfolio_snapshot",
    )
    scheduler.add_job(
        scheduled_reconcile,
        "interval",
        seconds=300,  # every 5 minutes
        id="trade_reconcile",
    )
    scheduler.start()

    # Start WebSocket — pybit runs it in a background daemon thread (no loop needed)
    logger.info("ws_connecting", symbol=settings.trade_symbol)
    await feed.start()


def get_bot_status() -> dict:
    return state.get_status()


def pause_bot() -> None:
    state.guard.halt("MANUAL_PAUSE")


def resume_bot() -> None:
    state.guard.resume()


async def main() -> None:
    configure_logging(settings.log_level, settings.log_format)

    from bot.api.app import create_app

    app = create_app()

    asyncio.create_task(run_bot())

    config = uvicorn.Config(
        app=app,
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
