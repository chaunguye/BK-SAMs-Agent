from src.repository.activity_repo import get_activity_repo
import uuid
import logfire
from datetime import datetime
from google.genai import types
from src.service.chunk_service import get_chunk_service

class ActivityService:
    async def register_activity(self, student_id: uuid.UUID, activity_id: uuid.UUID) -> str:
        activity_repo = await get_activity_repo()

        registered_activities = await activity_repo.get_activities_by_user_id(student_id)

        if activity_id in registered_activities:
            return f"Student is already registered for activity {activity_id}."
        
        success = await activity_repo.register_activity(student_id, activity_id)
        return f"Successfully registered for activity {activity_id}." if success else f"Failed to register for activity {activity_id}."
    
    async def unregister_activity(self, student_id: uuid.UUID, activity_id: uuid.UUID) -> str:
        activity_repo = await get_activity_repo()

        registered_activities = await activity_repo.get_activities_by_user_id(student_id)

        if activity_id not in registered_activities:
            return f"Can not cancel because Student is not registered for activity {activity_id}."
        
        success = await activity_repo.unregister_activity(student_id, activity_id)
        return f"Successfully unregistered from activity {activity_id}." if success else f"Failed to unregister from activity {activity_id}. Cancel registration must be done at least 24 hours before the activity starts, and you must be currently registered for the activity."
    
    async def search_activity_by_name(self, activity_name: str):
        activity_repo = await get_activity_repo()
        # return await activity_repo.get_activity_by_name(activity_name)
        chunk_service = get_chunk_service()
        activity_embedding = await chunk_service.gemini_embedder.aio.models.embed_content(
            model="gemini-embedding-2",
            contents=activity_name,
            config=types.EmbedContentConfig(output_dimensionality=768)
        )
        rrf_results = await activity_repo.get_activity_id_hybrid(activity_name, "[" + ",".join(str(x) for x in activity_embedding.embeddings[0].values) + "]")
        return self._filter_rrf_results(rrf_results)
    
    def _filter_rrf_results(self, rrf_results):
        """
        Filter RRF results based on score patterns:
        - If 1 activity has moderately higher score than others → return list of 1 activity
        - If many activities with similar high scores → return list of similar activities
        - If all activities have low scores → return empty list
        """
        if not rrf_results:
            return []
        
        # Extract scores
        scores = [item["score"] for item in rrf_results]
        
        # Define thresholds
        MAX_SCORE = max(scores) if scores else 0
        MIN_SCORE = min(scores) if scores else 0
        
        # Low score threshold (below 0.015 is considered low based on RRF formula)
        LOW_SCORE_THRESHOLD = 0.015
        
        # If all scores are low, return empty list
        if MAX_SCORE < LOW_SCORE_THRESHOLD:
            logfire.info(f"All activities have low scores (max: {MAX_SCORE}). Returning empty list.")
            return []
        
        # Check if top score is significantly higher (at least 50% higher than second highest)
        if len(rrf_results) > 1:
            top_score = scores[0]
            second_score = scores[1]
            score_ratio = top_score / second_score if second_score > 0 else float('inf')
            
            if score_ratio >= 1.5:  # 50% higher threshold
                logfire.info(f"Top activity has significantly higher score ({top_score:.4f}) vs second ({second_score:.4f}). Returning top 1 activity.")
                return [rrf_results[0]]
        
        # Find activities with similar high scores
        # Group activities within 10% of the top score
        top_score = scores[0]
        similarity_threshold = top_score * 0.9  # 90% of top score
        similar_activities = [
            item for item in rrf_results 
            if item["score"] >= similarity_threshold
        ]
        
        if similar_activities:
            logfire.info(f"Found {len(similar_activities)} activities with similar high scores (threshold: {similarity_threshold:.4f}). Returning all similar activities.")
            return similar_activities
        
        # Fallback: return empty list if no similar activities found
        return []  
    async def get_activity_details(self, activity_id: uuid.UUID):
        activity_repo = await get_activity_repo()
        return await activity_repo.get_activity_details(activity_id)
    
    async def get_registered_activities(self, student_id: uuid.UUID):
        activity_repo = await get_activity_repo()
        return await activity_repo.get_registered_activities(student_id)
    
    async def search_relevant_activity(self, time_start: datetime = None, name: str = None, time_end: datetime = None, location: str = None, status: str = None, sort_by: str = "number_of_conversion_day", desc: bool = True, top_k: int = 5):
        activity_repo = await get_activity_repo()

        if time_start and time_start.tzinfo:
            time_start = time_start.replace(tzinfo=None)
        if time_end and time_end.tzinfo:
            time_end = time_end.replace(tzinfo=None)

        with logfire.span("Searching Relevant Activities"):
            results = await activity_repo.search_relevant_activity(time_start, name, time_end, location, status, sort_by, desc, top_k)

        columns = ["id", "name", "location", "status", "description", "start_time", "end_time"]
        return [
            {col: row.get(col) for col in columns}
            for row in results
        ] if results else []
    
_activity_service = None
def get_activity_service():
    global _activity_service
    if _activity_service is None:
        _activity_service = ActivityService()
    return _activity_service