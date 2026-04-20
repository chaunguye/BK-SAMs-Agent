import json

import redis
import os
from dotenv import load_dotenv
from src.repository.conversation_repo import get_conversation_repo
from src.cache.cache_manager import get_cache_manager
import logfire
from fastapi.encoders import jsonable_encoder
from pydantic_ai.messages import ModelMessage
from pydantic import TypeAdapter
from src.util.filter_history import summarize_conversation

load_dotenv()

class ConversationService:
    def __init__(self):
        self.messages_adapter = TypeAdapter(list[ModelMessage])
        self.latest = 5
        self.max_history = 10
    async def get_conversation(self, conversation_id):
        with logfire.span("Get cache mananger instance"):
            cache = get_cache_manager()
        with logfire.span("Get conversation repo instance"):
            conversation_repo = await get_conversation_repo()

        with logfire.span("Fetching Conversation From Cache Reddis"):
            conversation = await cache.get_cache(str(conversation_id))
            logfire.info(f"Fetching message history from cache for conversation_id: {conversation_id}. Result: {f'Found in cache: {conversation}' if conversation else 'Not found in cache'}")
        
        if conversation:
            try:
                conversation = json.loads(conversation)
                return self.messages_adapter.validate_python(conversation)
            except json.JSONDecodeError as e:
                logfire.error(f"Error decoding conversation data from cache for conversation_id: {conversation_id}. Error: {e}")
                return []
        else:
            logfire.info(f"Cache miss for conversation_id: {conversation_id}. Fetching from database.")
            conversation = await conversation_repo.get_conversation(conversation_id)
            records = conversation['raw_message']
            logfire.info(f"Fetched {len(records)} messages from database for conversation_id: {conversation_id}. Records: {records}")

            summary = await conversation_repo.get_conversation_summary(conversation_id)
            logfire.info(f"Fetched conversation summary from database for conversation_id: {conversation_id}. Summary: {summary}")
            message_history_object = []
            message_history_object.append(json.load(summary))
            for rec in records:
                message_history_object.append(json.loads(rec["raw_message"]))

            with logfire.span("Set cache to Redis"):
                await cache.set_cache(str(conversation_id), json.dumps(jsonable_encoder(message_history_object)))
                logfire.info(f"Write Cache to Redis: {json.dumps(jsonable_encoder(message_history_object))}")
            return self.messages_adapter.validate_python(message_history_object)
                
    async def save_conversation(self, conversation_id, conversation_data, current_history = None, student_id = None):
        cache = get_cache_manager()

        conversation_repo = await get_conversation_repo()

        if student_id:
            await conversation_repo.save_conversation(conversation_id, conversation_data)

        un_summarized_messages = await conversation_repo.get_conversation(conversation_id)
    
        if len(un_summarized_messages) > self.max_history:
            with logfire.span("Summarizing conversation history for conversation_id: {}".format(conversation_id)):
                summary, recent = await summarize_conversation([json.loads(message['raw_message']) for message in un_summarized_messages], self.latest)
                logfire.info(f"Summary result for conversation_id: {conversation_id}: {summary}")

                await conversation_repo.update_conversation_summary(conversation_id, summary)
                logfire.info(f"Updated conversation summary in database for conversation_id: {conversation_id}")
                update_ids = [message['id'] for message in un_summarized_messages[:-self.latest]]
                # Mark the old messages as summarized in the database
                await conversation_repo.mark_messages_as_summarized(conversation_id, update_ids)
                logfire.info(f"Marking {len(update_ids)} messages as summarized for conversation_id: {conversation_id}. Message IDs: {update_ids}")
            
            serialized_history = jsonable_encoder([message.model_dump(mode='json') if hasattr(message, 'model_dump') else message for message in summary + recent])
            await cache.set_cache(str(conversation_id), json.dumps(serialized_history))


        if current_history is None:
            current_history = await self.get_conversation_summary(conversation_id)
            current_history += await self.get_conversation(conversation_id)['raw_message']

        current_history.extend(conversation_data)
            

        serialized_history = jsonable_encoder([message.model_dump(mode='json') if hasattr(message, 'model_dump') else message for message in current_history])
        # Ensure serialized_history is a JSON string
        await cache.set_cache(str(conversation_id), json.dumps(serialized_history))
        
    async def create_conversation(self, title, user_id):
        conversation_repo = await get_conversation_repo()
        return await conversation_repo.create_conversation(title, user_id)
    
    async def get_conversation_list(self, user_id):
        conversation_repo = await get_conversation_repo()
        return await conversation_repo.get_conversation_list(user_id)
    
    async def load_history(self, conversation_id):
        conversation_repo = await get_conversation_repo()
        return await conversation_repo.get_conversation_content(conversation_id)

_conversation_service = None
def get_conversation_service():
    global _conversation_service
    if _conversation_service is None:
        _conversation_service = ConversationService()
    return _conversation_service