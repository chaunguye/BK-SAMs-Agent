from src.database.database_connect import get_db_pool
from pydantic_ai import ModelRequest, ModelResponse, ToolCallPart, TextPart
import json
from fastapi.encoders import jsonable_encoder

class ConversationRepository:
    def __init__(self, pool):
        self.pool = pool

    async def save_conversation(self, conversation_id, conversation_data):
        query = """
            INSERT INTO message (sender_type, text_content, conversation_id, raw_message)
            VALUES ($1, $2, $3, $4)
        """
        data_to_insert = []
        for data in conversation_data:
            sender_type = self._get_role(data)
            text_content = self._extract_content(data)
            # metadata = data.model_dump_json() if hasattr(data, 'model_dump_json') else jsonable_encoder(data)
            metadata = jsonable_encoder(data.model_dump(mode='json') if hasattr(data, 'model_dump') else data)
            data_to_insert.append((sender_type, text_content, conversation_id, json.dumps(metadata)))
            
        async with self.pool.acquire() as conn:
            return await conn.executemany(query, data_to_insert)

    async def get_conversation(self, conversation_id):
        query = """
            SELECT raw_message FROM message
            WHERE conversation_id = $1
            ORDER BY timestamp ASC
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, conversation_id)
    async def create_conversation(self, conversation_id):
        query = """
            INSERT INTO conversation (tittle, user_id)
            VALUES ($1, $2)
        """
        async with self.pool.acquire() as conn:
            return await conn.execute(query, conversation_id)

    def _get_role(self, message):
        if isinstance(message, ModelRequest):
            return "client"
        elif isinstance(message, ModelResponse):
            return "AI"
        else:
            return "unknown"
    
    def _extract_content(self, message) -> str:
        texts = []  
        for part in message.parts:
            if isinstance(part, TextPart):
                texts.append(part.content)
            elif isinstance(part, ToolCallPart):
                # We might want to store that a tool was called in the content
                texts.append(f"[Tool Call: {part.tool_name}]")
        return "\n".join(texts)

    

_conversation_repo = None
async def get_conversation_repo():
    global _conversation_repo
    if _conversation_repo is None:
        pool = await get_db_pool()
        _conversation_repo = ConversationRepository(pool)
    return _conversation_repo