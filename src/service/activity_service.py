from src.repository.activity_repo import get_activity_repo

class ActivityController:
    async def register_activity(self, student_id: str, activity_name: str) -> str:
        activity_repo = await get_activity_repo()
        activity = await activity_repo.get_activity_by_name(activity_name)
        if not activity:
            return f"Activity '{activity_name}' not found."
        
        confirm = await self.get_confirmation(student_id, activity_name)
        if confirm:
            activity_id = await activity_repo.register_activity(student_id, activity['id'])
            return f"Successfully registered for {activity_name} with registration ID: {activity_id}"
        else:
            return f"Registration for {activity_name} was cancelled."
    
    async def unregister_activity(self, student_id: str, activity_name: str) -> str:
        activity_repo = await get_activity_repo()
        activity = await activity_repo.get_activity_by_name(activity_name)
        if not activity:
            return f"Activity '{activity_name}' not found."
        confirm = await self.get_confirmation(student_id, activity_name, action="unregister")
        if confirm:
            result = await activity_repo.unregister_activity(student_id, activity['id'])
            if result:
                return f"Successfully unregistered from {activity_name}."
            else:
                return f"Failed to unregister from {activity_name}. You may not be registered for this activity."
        else:
            return f"Unregistration for {activity_name} was cancelled."
        
    async def get_confirmation(self, student_id: str, activity_name: str, action: str = "register") -> bool:
        # Placeholder for confirmation logic
        return True  # Assume confirmation is always given for this placeholder implementation
