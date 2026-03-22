"""
Bybit V5 API client wrapper.
Handles HTTP (pybit) and WebSocket connections.
"""
import asyncio
from typing import Any, Callable, Dict, List, Optional

from pybit.unified_trading import HTTP, WebSocket

from bot.config.settings import settings
from bot.utils.logging import get_logger
from bot.utils.time_utils import ms_to_datetime

logger = get_logger(__name__)


class BybitHTTPClient:
    """Synchronous Bybit HTTP client (pybit uses sync under the hood)."""

    def __init__(self) -> None:
        self._session = HTTP(
            testnet=settings.bybit_testnet,
            api_key=settings.bybit_api_key,
            api_secret=settings.bybit_api_secret,
        )

    def get_klines(
        self,
        symbol: str,
        interval: str,
        start: Optional[int] = None,
        end: Optional[int] = None,
        limit: int = 200,
    ) -> List[Dict]:
        """
        Fetch OHLCV klines from Bybit.
        Returns list of dicts with keys: open_time, open, high, low, close, volume, turnover
        """
        params: Dict[str, Any] = {
            "category": "linear",
            "symbol": symbol,
            "interval": interval,
            "limit": limit,
        }
        if start:
            params["start"] = start
        if end:
            params["end"] = end

        resp = self._session.get_kline(**params)
        if resp.get("retCode") != 0:
            raise RuntimeError(f"Bybit kline error: {resp.get('retMsg')}")

        rows = []
        for item in reversed(resp["result"]["list"]):
            rows.append({
                "open_time": ms_to_datetime(int(item[0])),
                "open": float(item[1]),
                "high": float(item[2]),
                "low": float(item[3]),
                "close": float(item[4]),
                "volume": float(item[5]),
                "turnover": float(item[6]) if len(item) > 6 else None,
            })
        return rows

    def get_wallet_balance(self, account_type: str = "UNIFIED") -> Dict:
        resp = self._session.get_wallet_balance(accountType=account_type)
        if resp.get("retCode") != 0:
            raise RuntimeError(f"Bybit wallet error: {resp.get('retMsg')}")
        return resp["result"]

    def get_positions(self, symbol: Optional[str] = None) -> List[Dict]:
        params: Dict[str, Any] = {"category": "linear", "settleCoin": "USDT"}
        if symbol:
            params["symbol"] = symbol
        resp = self._session.get_positions(**params)
        if resp.get("retCode") != 0:
            raise RuntimeError(f"Bybit positions error: {resp.get('retMsg')}")
        return resp["result"]["list"]

    def place_order(
        self,
        symbol: str,
        side: str,
        qty: str,
        order_type: str = "Market",
        price: Optional[str] = None,
        stop_loss: Optional[str] = None,
        take_profit: Optional[str] = None,
        reduce_only: bool = False,
        order_link_id: Optional[str] = None,
    ) -> Dict:
        params: Dict[str, Any] = {
            "category": "linear",
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "qty": qty,
            "reduceOnly": reduce_only,
        }
        if price:
            params["price"] = price
        if stop_loss:
            params["stopLoss"] = stop_loss
        if take_profit:
            params["takeProfit"] = take_profit
        if order_link_id:
            params["orderLinkId"] = order_link_id

        resp = self._session.place_order(**params)
        if resp.get("retCode") != 0:
            raise RuntimeError(f"Bybit order error: {resp.get('retMsg')}")
        return resp["result"]

    def cancel_order(self, symbol: str, order_id: str) -> Dict:
        resp = self._session.cancel_order(
            category="linear", symbol=symbol, orderId=order_id
        )
        if resp.get("retCode") != 0:
            raise RuntimeError(f"Bybit cancel error: {resp.get('retMsg')}")
        return resp["result"]

    def set_trading_stop(
        self,
        symbol: str,
        stop_loss: Optional[str] = None,
        take_profit: Optional[str] = None,
        position_idx: int = 0,
    ) -> Dict:
        params: Dict[str, Any] = {
            "category": "linear",
            "symbol": symbol,
            "positionIdx": position_idx,
        }
        if stop_loss:
            params["stopLoss"] = stop_loss
        if take_profit:
            params["takeProfit"] = take_profit
        resp = self._session.set_trading_stop(**params)
        if resp.get("retCode") != 0:
            raise RuntimeError(f"Bybit set_trading_stop error: {resp.get('retMsg')}")
        return resp["result"]

    def get_closed_pnl(self, symbol: str, limit: int = 5) -> List[Dict]:
        """Fetch recently closed positions from Bybit (useful to detect SL/TP hits)."""
        try:
            resp = self._session.get_closed_pnl(
                category="linear",
                symbol=symbol,
                limit=limit,
            )
            if resp.get("retCode") != 0:
                raise RuntimeError(f"Bybit closed_pnl error: {resp.get('retMsg')}")
            return resp["result"]["list"]
        except Exception as e:
            logger.error("get_closed_pnl_error", error=str(e))
            return []

    def get_instrument_info(self, symbol: str) -> Dict:
        resp = self._session.get_instruments_info(category="linear", symbol=symbol)
        if resp.get("retCode") != 0:
            raise RuntimeError(f"Bybit instrument info error: {resp.get('retMsg')}")
        items = resp["result"]["list"]
        if not items:
            raise ValueError(f"No instrument info for {symbol}")
        return items[0]


class BybitWebSocketClient:
    """
    Async-friendly Bybit WebSocket client.
    Runs pybit WebSocket in a background thread and forwards kline data
    to asyncio queues.
    """

    def __init__(self) -> None:
        self._ws: Optional[WebSocket] = None
        self._kline_callbacks: List[Callable] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def subscribe_kline(self, callback: Callable) -> None:
        self._kline_callbacks.append(callback)

    def start(self, symbol: str, interval: str, loop: asyncio.AbstractEventLoop = None) -> None:
        self._loop = loop
        self._ws = WebSocket(
            testnet=settings.bybit_testnet,
            channel_type="linear",
        )
        topic = f"kline.{interval}.{symbol}"
        self._ws.kline_stream(
            interval=int(interval),
            symbol=symbol,
            callback=self._on_kline,
        )
        logger.info("bybit_ws_started", symbol=symbol, interval=interval)

    def _on_kline(self, msg: Dict) -> None:
        if self._loop is None:
            return
        try:
            data_list = msg.get("data", [])
            for kline in data_list:
                # Only process confirmed (closed) candles
                if kline.get("confirm", False):
                    candle = {
                        "open_time": ms_to_datetime(int(kline["start"])),
                        "open": float(kline["open"]),
                        "high": float(kline["high"]),
                        "low": float(kline["low"]),
                        "close": float(kline["close"]),
                        "volume": float(kline["volume"]),
                        "turnover": float(kline.get("turnover", 0)),
                        "symbol": msg.get("topic", "").split(".")[-1],
                        "interval": str(kline.get("interval", "")),
                    }
                    for cb in self._kline_callbacks:
                        asyncio.run_coroutine_threadsafe(cb(candle), self._loop)
        except Exception as e:
            logger.error("ws_kline_parse_error", error=str(e))

    def stop(self) -> None:
        if self._ws:
            try:
                self._ws.exit()
            except Exception:
                pass
        logger.info("bybit_ws_stopped")


# Module-level singletons
_http_client: Optional[BybitHTTPClient] = None
_ws_client: Optional[BybitWebSocketClient] = None


def get_http_client() -> BybitHTTPClient:
    global _http_client
    if _http_client is None:
        _http_client = BybitHTTPClient()
    return _http_client


def get_ws_client() -> BybitWebSocketClient:
    global _ws_client
    if _ws_client is None:
        _ws_client = BybitWebSocketClient()
    return _ws_client
