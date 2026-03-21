"""
WebSocket endpoint for real-time data push to the frontend.
Subscribes to the internal event bus and forwards events to all connected clients.
"""
import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from bot.api.event_bus import bus
from bot.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    queue = bus.subscribe()
    logger.info("ws_client_connected", client=str(websocket.client))

    async def heartbeat():
        while True:
            try:
                await websocket.send_text(json.dumps({"type": "heartbeat", "data": {}}))
                await asyncio.sleep(15)
            except Exception:
                break

    hb_task = asyncio.create_task(heartbeat())

    try:
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=30)
                await websocket.send_text(json.dumps(msg, default=str))
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break
    except WebSocketDisconnect:
        logger.info("ws_client_disconnected", client=str(websocket.client))
    except Exception as e:
        logger.error("ws_error", error=str(e))
    finally:
        hb_task.cancel()
        bus.unsubscribe(queue)
