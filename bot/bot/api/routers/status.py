import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter
import bot.state as state
from bot.config.settings import settings
from bot.db.engine import get_session
from bot.db.repositories import trade_repo
from bot.exchange.bybit_client import get_http_client

router = APIRouter()


@router.get("/status")
async def get_status():
    await state.position_manager.refresh()
    return state.get_status()


@router.post("/status/pause")
async def pause():
    state.guard.halt("MANUAL_PAUSE")
    return {"status": "paused"}


@router.post("/status/resume")
async def resume():
    state.guard.resume()
    return {"status": "running"}


@router.post("/status/reconcile")
async def manual_reconcile():
    """Force-close all DB trades that are OPEN but have no active Bybit position."""
    from bot.main import reconcile_open_trades

    symbol = settings.trade_symbol
    await state.position_manager.refresh()

    async with get_session() as session:
        open_trades = await trade_repo.get_all_open_trades(session, symbol)

    if not open_trades:
        return {"reconciled": 0, "message": "No orphan trades found"}

    bybit_position = state.position_manager.get_position(symbol)
    if bybit_position:
        return {"reconciled": 0, "message": "Active Bybit position exists — trades are legitimate"}

    # Get current price as fallback
    try:
        klines = await asyncio.to_thread(
            get_http_client().get_klines, symbol, str(settings.trade_interval), limit=1
        )
        last_price = float(klines[-1]["close"]) if klines else 0.0
    except Exception:
        last_price = 0.0

    now = datetime.now(timezone.utc)
    await reconcile_open_trades(symbol, now, last_price)

    return {"reconciled": len(open_trades), "message": f"Closed {len(open_trades)} orphan trades"}
