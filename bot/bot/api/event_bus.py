"""
Internal async event bus.
Trading loop publishes events; WebSocket router subscribes and forwards to clients.
"""
import asyncio
from typing import Any, Dict, List


class EventBus:
    def __init__(self) -> None:
        self._subscribers: List[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    async def publish(self, event_type: str, data: Dict[str, Any]) -> None:
        msg = {"type": event_type, "data": data}
        dead = []
        for q in self._subscribers:
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                dead.append(q)
        for q in dead:
            self.unsubscribe(q)


# Global singleton
bus = EventBus()
