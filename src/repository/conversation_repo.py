from src.database.database_connect import get_db_pool
from pydantic_ai import ModelRequest, ModelResponse, ToolCallPart, TextPart, UserPromptPart
import json
from fastapi.encoders import jsonable_encoder
from datetime import datetime

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
            SELECT id, raw_message FROM message
            WHERE conversation_id = $1 AND summarized = FALSE
            ORDER BY timestamp ASC
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, conversation_id)
        
    async def get_conversation_summary(self, conversation_id):
        query = """
            SELECT summary FROM conversation
            WHERE id = $1
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, conversation_id) 
        
    async def update_conversation_summary(self, conversation_id, summary):
        query = """
            UPDATE conversation
            SET summary = $1
            WHERE id = $2
        """
        async with self.pool.acquire() as conn:
            return await conn.execute(query, summary, conversation_id)
        
    async def mark_messages_as_summarized(self, conversation_id, message_ids = None):
        if message_ids is None:
            query = """
                UPDATE message
                SET summarized = TRUE
                WHERE conversation_id = $1 AND summarized = FALSE
            """
            async with self.pool.acquire() as conn:
                return await conn.execute(query, conversation_id)
        else:
            query = """
                UPDATE message
                SET summarized = TRUE
                WHERE id = ANY($1::int[])
            """
            async with self.pool.acquire() as conn:
                return await conn.execute(query, message_ids)
        
    async def get_conversation_content(self, conversation_id):
        query = """
            SELECT text_content, sender_type FROM message 
            WHERE conversation_id = $1 AND text_content IS NOT NULL
            ORDER BY timestamp ASC
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, conversation_id)

    async def create_conversation(self, title, user_id):
        query = """
            INSERT INTO conversation (title, user_id)
            VALUES ($1, $2)
            RETURNING id;
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, title, user_id)
        
    async def get_conversation_list(self, student_id):
        query = """
            SELECT id, title 
            FROM conversation
            WHERE user_id = $1
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, student_id)
        
    async def update_title(self, conversation_id, new_title):
        query = """
            UPDATE conversation
            SET title = $1
            WHERE id = $2
        """
        async with self.pool.acquire() as conn:
            return await conn.execute(query, new_title, conversation_id)

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
            elif isinstance(part, UserPromptPart):
                texts.append(part.content)
        return "\n".join(texts)
    
    async def search_relevant_activity(self, time_start: datetime = None, name: str = None, time_end: datetime = None, location: str = None, status: str = None, sort_by: str = "number_of_conversion_day", desc: bool = True, top_k: int = 5):
        query = """
            SELECT *
            FROM activity
            WHERE start_time >= COALESCE($1::timestamp, current_date)
            AND ($2::text IS NULL OR name ILIKE '%' || $2 || '%')
            AND ($3::timestamp IS NULL OR end_time <= $3)
            AND ($4::text IS NULL OR location ILIKE '%' || $4 || '%')
            AND ($5::activity_status IS NULL OR status = $5::activity_status)
            ORDER BY {} {}
            LIMIT $6
        """
        order_direction = "DESC" if desc else "ASC"
        
        allowed_columns = {"name", "time_start", "location", "number_of_conversion_day"}

        if sort_by not in allowed_columns:
            sort_by = "number_of_conversion_day"  # default sorting column

        query = query.format(sort_by, order_direction)
        
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, time_start, name, time_end, location, status, top_k)
        return [dict(row) for row in rows]

    

_conversation_repo = None
async def get_conversation_repo():
    global _conversation_repo
    if _conversation_repo is None:
        pool = await get_db_pool()
        _conversation_repo = ConversationRepository(pool)
    return _conversation_repo