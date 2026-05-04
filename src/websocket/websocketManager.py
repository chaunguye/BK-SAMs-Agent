import uuid

from fastapi import WebSocket
from typing import Dict

class WebsocketManager:
    def __init__(self, limit: int = 100):
        self.connection: Dict[uuid.UUID, WebSocket] = {}
        self.limit = limit

    async def connect(self, conversation_id: uuid.UUID, websocket: WebSocket):
        if conversation_id in self.connection:
            try:
                await self.connection[conversation_id].close(code=1000)
            except:
                pass # Already closed
        if len(self.connection) >= self.limit:
            await websocket.accept()
            await websocket.send_json({"type": "error", "message": "Connection limit reached. Please try again later."})
            await websocket.close()
        await websocket.accept()
        self.connection[conversation_id] = websocket

    def disconnect(self, conversation_id: uuid.UUID):
        self.connection.pop(conversation_id, None)

    async def broadcast(self, message):
        for client in self.connection.values():
            await client.send(message)

    async def send_personal_message(self, conversation_id: uuid.UUID, message, type, sender_type="AI", tool_call_id=None):
        websocket = self.connection.get(conversation_id)
        if websocket:
            payload = {"type": type, "message": message, "sender_type": sender_type}
            if tool_call_id is not None:
                payload["tool_call_id"] = tool_call_id
            await websocket.send_json(payload)

    async def send_session_init(self, conversation_id: uuid.UUID, conversation_name: str):
        websocket = self.connection.get(conversation_id)
        if websocket:
            await websocket.send_json({"type": "session_init", "conversation_id": str(conversation_id), "conversation_name": conversation_name})

_websocket_manager = None
def get_websocket_manager():
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebsocketManager()
    return _websocket_manager