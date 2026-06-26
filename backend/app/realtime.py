"""Gerenciador de conexões WebSocket para atualizações em tempo real."""
from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

from fastapi import WebSocket


def _default(obj: Any) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)


class ConnectionManager:
    """Mantém os dashboards conectados e transmite eventos para todos."""

    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.discard(websocket)

    @property
    def total(self) -> int:
        return len(self._connections)

    async def broadcast(self, event: str, data: Any) -> None:
        """Envia um evento para todos os dashboards conectados."""
        message = json.dumps({"event": event, "data": data}, default=_default)
        async with self._lock:
            conexoes = list(self._connections)
        mortas: list[WebSocket] = []
        for ws in conexoes:
            try:
                await ws.send_text(message)
            except Exception:
                mortas.append(ws)
        if mortas:
            async with self._lock:
                for ws in mortas:
                    self._connections.discard(ws)


manager = ConnectionManager()
