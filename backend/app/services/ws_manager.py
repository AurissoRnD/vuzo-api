import json
from fastapi import WebSocket


class ConnectionManager:
    """Tracks active WebSocket connections by user_id."""

    def __init__(self):
        self._connections: dict[str, WebSocket] = {}

    def connect(self, user_id: str, ws: WebSocket):
        self._connections[user_id] = ws

    def disconnect(self, user_id: str):
        self._connections.pop(user_id, None)

    def is_connected(self, user_id: str) -> bool:
        return user_id in self._connections

    async def send(self, user_id: str, data: dict):
        ws = self._connections.get(user_id)
        if ws is None:
            return
        try:
            await ws.send_text(json.dumps(data))
        except Exception:
            self.disconnect(user_id)


manager = ConnectionManager()
