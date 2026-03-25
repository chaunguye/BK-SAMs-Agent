from src.database.database_connect import get_db_pool
import uuid

class ActivityRepository:
    def __init__(self, pool):
        self.pool = pool

    async def register_activity(self, student_id: uuid.UUID, activity_id: str):
        query = """
            INSERT INTO registrations (student_id, activity_id)
            VALUES ($1, $2) RETURNING id
        """
        async with self.pool.acquire() as conn:
            return await conn.execute(query, student_id, activity_id)
    
    async def unregister_activity(self, student_id: uuid.UUID, activity_id: str):
        query = """
            DELETE FROM registrations
            WHERE student_id = $1 AND activity_id = $2
        """
        async with self.pool.acquire() as conn:
            result = await conn.execute(query, student_id, activity_id)
            return result == "DELETE 1"  # Check if one row was deleted

    async def get_activity_by_name(self, activity_name: str):
        query = """
            SELECT * FROM activity
            WHERE name = $1
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, activity_name)

_activity_repo = None
async def get_activity_repo():
    global _activity_repo
    if _activity_repo is None:
        pool = await get_db_pool()
        _activity_repo = ActivityRepository(pool)
    return _activity_repo