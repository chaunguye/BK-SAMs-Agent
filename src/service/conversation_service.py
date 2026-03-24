import json

import redis
import os
from dotenv import load_dotenv
from src.repository.conversation_repo import get_conversation_repo
from src.cache.cache_manager import get_cache_manager
import logfire

load_dotenv()

class ConversationService:
    async def get_conversation(self, conversation_id):
        cache = get_cache_manager()
        conversation_repo = await get_conversation_repo()

        with logfire.span("Fetching Conversation From Cache Reddis"):
            conversation = await cache.get_cache(conversation_id)
            logfire.info(f"Fetching message history from cache for conversation_id: {conversation_id}. Result: {'Found in cache: {conversation}' if conversation else 'Not found in cache'}")
        
        if conversation:
            try:
                conversation = json.loads(conversation)
            except json.JSONDecodeError as e:
                logfire.error(f"Error decoding conversation data from cache for conversation_id: {conversation_id}. Error: {e}")
                return []
        else:
            logfire.info(f"Cache miss for conversation_id: {conversation_id}. Fetching from database.")
            conversation = await conversation_repo.get_conversation(conversation_id)
            await cache.set_cache(conversation_id, conversation)
            return json.loads(conversation) if conversation else []
        
    async def save_conversation(self, conversation_id, conversation_data):
        cache = get_cache_manager()
        conversation_repo = await get_conversation_repo()

        history = await self.get_conversation(conversation_id)
        history.extend(conversation_data)

        serialized_history = json.dumps([message.model_dump() if hasattr(message, 'model_dump') else message for message in history])

        await conversation_repo.save_conversation(conversation_id, serialized_history)
        await cache.set_cache(conversation_id, serialized_history)

_conversation_service = None
def get_conversation_service():
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service