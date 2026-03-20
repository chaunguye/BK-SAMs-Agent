import uuid

from fastapi import WebSocket
from typing import Dict

class WebsocketManager:
    def __init__(self, limit: int = 100):
        self.connection: Dict[uuid.UUID, WebSocket] = {}
        self.limit = limit

    async def connect(self, student_id: str, websocket: WebSocket):
        if student_id in self.connection:
            try:
                await self.connection[student_id].close(code=1000)
            except:
                pass # Already closed
        if len(self.connection) >= self.limit:
            await websocket.accept()
            await websocket.send_json({"type": "error", "message": "Connection limit reached. Please try again later."})
            await websocket.close()
        await websocket.accept()
        self.connection[student_id] = websocket

    def disconnect(self, student_id: str):
        self.connection.pop(student_id, None)

    async def broadcast(self, message):
        for client in self.connection.values():
            await client.send(message)

    async def send_personal_message(self, student_id: str, message, type):
        websocket = self.connection.get(student_id)
        if websocket:
            payload = {"type": type, "message": message}
            await websocket.send_json(payload)

_websocket_manager = None
def get_websocket_manager():
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebsocketManager()
    return _websocket_manager