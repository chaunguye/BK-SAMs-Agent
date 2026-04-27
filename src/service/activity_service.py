from src.repository.activity_repo import get_activity_repo
import uuid
import logfire
from datetime import datetime
from google.genai import types
from src.service.chunk_service import get_chunk_service

class ActivityService:
    async def register_activity(self, student_id: uuid.UUID, activity_id: uuid.UUID) -> str:
        activity_repo = await get_activity_repo()
        
        success = await activity_repo.register_activity(student_id, activity_id)
        return f"Successfully registered for activity {activity_id}." if success else f"Failed to register for activity {activity_id}."
    
    async def unregister_activity(self, student_id: uuid.UUID, activity_id: uuid.UUID) -> str:
        activity_repo = await get_activity_repo()
        
        success = await activity_repo.unregister_activity(student_id, activity_id)
        return f"Successfully unregistered from activity {activity_id}." if success else f"Failed to unregister from activity {activity_id}."
    async def search_activity_by_name(self, activity_name: str):
        activity_repo = await get_activity_repo()
        # return await activity_repo.get_activity_by_name(activity_name)
        chunk_service = get_chunk_service()
        activity_embedding = await chunk_service.gemini_embedder.aio.models.embed_content(
            model="gemini-embedding-2",
            contents=activity_name,
            config=types.EmbedContentConfig(output_dimensionality=768)
        )
        return await activity_repo.get_activity_id_hybrid(activity_name, "[" + ",".join(str(x) for x in activity_embedding.embeddings[0].values) + "]")  
    async def get_activity_details(self, activity_id: uuid.UUID):
        activity_repo = await get_activity_repo()
        return await activity_repo.get_activity_details(activity_id)
    
    async def get_registered_activitys(self, student_id: uuid.UUID):
        activity_repo = await get_activity_repo()
        return await activity_repo.get_registered_activitys(student_id)
    
    async def search_relevant_activity(self, time_start: datetime = None, name: str = None, time_end: datetime = None, location: str = None, status: str = None, sort_by: str = "number_of_conversion_day", desc: bool = True, top_k: int = 5):
        activity_repo = await get_activity_repo()
        with logfire.span("Searching Relevant Activities"):
            results = await activity_repo.search_relevant_activity(time_start, name, time_end, location, status, sort_by, desc, top_k)
        return results
    
_activity_service = None
def get_activity_service():
    global _activity_service
    if _activity_service is None:
        _activity_service = ActivityService()
    return _activity_service