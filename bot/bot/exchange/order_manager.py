"""
Order execution manager.
Places, tracks and cancels orders via Bybit V5.
"""
import uuid
from typing import Dict, Optional

from bot.exchange.bybit_client import get_http_client
from bot.utils.logging import get_logger

logger = get_logger(__name__)


def _gen_link_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


class OrderManager:
    def __init__(self) -> None:
        self._client = get_http_client()

    def open_long(
        self,
        symbol: str,
        qty: float,
        stop_loss: float,
        take_profit: float,
    ) -> Dict:
        """Open a LONG (buy) market order with SL and TP."""
        link_id = _gen_link_id("L")
        result = self._client.place_order(
            symbol=symbol,
            side="Buy",
            qty=str(qty),
            order_type="Market",
            stop_loss=str(round(stop_loss, 2)),
            take_profit=str(round(take_profit, 2)),
            order_link_id=link_id,
        )
        logger.info(
            "order_long_opened",
            symbol=symbol,
            qty=qty,
            sl=stop_loss,
            tp=take_profit,
            order_id=result.get("orderId"),
        )
        return result

    def open_short(
        self,
        symbol: str,
        qty: float,
        stop_loss: float,
        take_profit: float,
    ) -> Dict:
        """Open a SHORT (sell) market order with SL and TP."""
        link_id = _gen_link_id("S")
        result = self._client.place_order(
            symbol=symbol,
            side="Sell",
            qty=str(qty),
            order_type="Market",
            stop_loss=str(round(stop_loss, 2)),
            take_profit=str(round(take_profit, 2)),
            order_link_id=link_id,
        )
        logger.info(
            "order_short_opened",
            symbol=symbol,
            qty=qty,
            sl=stop_loss,
            tp=take_profit,
            order_id=result.get("orderId"),
        )
        return result

    def close_position(
        self,
        symbol: str,
        qty: float,
        side: str,
    ) -> Dict:
        """
        Close an open position by placing a reduce-only market order.
        side: "Buy" to close SHORT, "Sell" to close LONG
        """
        link_id = _gen_link_id("C")
        result = self._client.place_order(
            symbol=symbol,
            side=side,
            qty=str(qty),
            order_type="Market",
            reduce_only=True,
            order_link_id=link_id,
        )
        logger.info(
            "order_position_closed",
            symbol=symbol,
            qty=qty,
            side=side,
            order_id=result.get("orderId"),
        )
        return result

    def cancel(self, symbol: str, order_id: str) -> Dict:
        result = self._client.cancel_order(symbol=symbol, order_id=order_id)
        logger.info("order_cancelled", symbol=symbol, order_id=order_id)
        return result

    def get_instrument_info(self, symbol: str) -> Dict:
        return self._client.get_instrument_info(symbol)
