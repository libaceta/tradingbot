"""
Shared bot runtime state.
Single source of truth accessed by both main.py and API routers.
"""
from datetime import datetime, timezone
from typing import Optional

from bot.exchange.order_manager import OrderManager
from bot.exchange.position_manager import PositionManager
from bot.risk.portfolio_guard import PortfolioGuard
from bot.strategy.momentum_trend import MomentumTrendStrategy

bot_running: bool = False
bot_start_time: Optional[datetime] = None
peak_equity: float = 0.0

strategy = MomentumTrendStrategy()
position_manager = PositionManager()
order_manager = OrderManager()
guard = PortfolioGuard()


def get_status() -> dict:
    return {
        "bot_running": bot_running,
        "mode": _get_mode(),
        "uptime_secs": (
            int((datetime.now(timezone.utc) - bot_start_time).total_seconds())
            if bot_start_time
            else 0
        ),
        "open_positions": position_manager.all_positions(),
        "equity_usdt": position_manager.equity,
        "is_halted": guard.is_halted,
        "halt_reason": guard.halt_reason,
    }


def _get_mode() -> str:
    from bot.config.settings import settings
    return settings.trading_mode
