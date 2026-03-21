"""
Tracks open positions and account balance by polling Bybit.
"""
import asyncio
from typing import Dict, List, Optional

from bot.exchange.bybit_client import get_http_client
from bot.utils.logging import get_logger

logger = get_logger(__name__)


class PositionManager:
    def __init__(self) -> None:
        self._client = get_http_client()
        self._positions: Dict[str, Dict] = {}  # symbol -> position dict
        self._equity: float = 0.0
        self._available: float = 0.0
        self._unrealized_pnl: float = 0.0

    async def refresh(self) -> None:
        """Refresh positions and wallet balance from exchange."""
        await asyncio.gather(
            asyncio.to_thread(self._refresh_balance),
            asyncio.to_thread(self._refresh_positions),
        )

    def _refresh_balance(self) -> None:
        try:
            result = self._client.get_wallet_balance()
            for account in result.get("list", []):
                if account.get("accountType") == "UNIFIED":
                    self._equity = float(account.get("totalEquity") or 0)
                    self._available = float(account.get("totalAvailableBalance") or 0)
                    self._unrealized_pnl = float(account.get("totalUnrealisedPnl") or 0)
                    logger.info("balance_refreshed", equity=self._equity, available=self._available)
                    break
            else:
                logger.warning(
                    "balance_account_not_found",
                    accounts=[a.get("accountType") for a in result.get("list", [])],
                )
        except Exception as e:
            logger.error("position_manager_balance_error", error=str(e))

    def _refresh_positions(self) -> None:
        try:
            positions = self._client.get_positions()
            self._positions = {}
            for pos in positions:
                size = float(pos.get("size", 0))
                if size > 0:
                    symbol = pos["symbol"]
                    self._positions[symbol] = {
                        "symbol": symbol,
                        "side": pos.get("side"),
                        "size": size,
                        "avg_price": float(pos.get("avgPrice", 0)),
                        "unrealized_pnl": float(pos.get("unrealisedPnl", 0)),
                        "stop_loss": pos.get("stopLoss"),
                        "take_profit": pos.get("takeProfit"),
                        "leverage": int(pos.get("leverage", 1)),
                    }
        except Exception as e:
            logger.error("position_manager_positions_error", error=str(e))

    def get_position(self, symbol: str) -> Optional[Dict]:
        return self._positions.get(symbol)

    def has_position(self, symbol: str) -> bool:
        return symbol in self._positions

    def all_positions(self) -> List[Dict]:
        return list(self._positions.values())

    def open_count(self) -> int:
        return len(self._positions)

    @property
    def equity(self) -> float:
        return self._equity

    @property
    def available(self) -> float:
        return self._available

    @property
    def unrealized_pnl(self) -> float:
        return self._unrealized_pnl
