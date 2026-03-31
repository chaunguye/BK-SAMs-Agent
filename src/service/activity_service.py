from src.repository.activity_repo import get_activity_repo
import uuid

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
        return await activity_repo.get_activity_by_name(activity_name)
        
        
_activity_service = None
def get_activity_service():
    global _activity_service
    if _activity_service is None:
        _activity_service = ActivityService()
    return _activity_service