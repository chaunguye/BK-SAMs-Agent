import uuid

from fastapi import WebSocket
from typing import Dict

class WebsocketManager:
    def __init__(self):
        self.connection: Dict[uuid.UUID, WebSocket] = {}

    async def connect(self, student_id: uuid.UUID, websocket: WebSocket):
        if student_id in self.connection:
            try:
                await self.connection[student_id].close(code=1000)
            except:
                pass # Already closed
        await websocket.accept()
        self.connection[student_id] = websocket

    def disconnect(self, student_id: uuid.UUID):
        self.connection.pop(student_id, None)

    async def broadcast(self, message):
        for client in self.connection.values():
            await client.send(message)

    async def send_personal_message(self, student_id: uuid.UUID, message, type):
        websocket = self.connection.get(student_id)
        if websocket:
            payload = {"type": type, "message": message}
            await websocket.send_json(payload)

    