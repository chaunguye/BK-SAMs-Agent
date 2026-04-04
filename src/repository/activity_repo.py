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
            SELECT id, name, location, status, description, start_time, end_time, similarity(name::text, $1) as score
            FROM activity
            WHERE name % $1
            ORDER BY score DESC
            LIMIT 1
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, activity_name)
    
    async def get_activity_details(self, activity_id: uuid.UUID):
        query = """
            SELECT a.id, a.name, a.location, a.status, a.description, a.start_time, a.end_time, a.max_slots, a.number_of_conversion_day, f.name as organizer_faculty_name
            FROM activity a 
            LEFT JOIN faculty f ON a.faculty_id = f.id
            WHERE a.id = $1
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, activity_id)

    async def get_registered_activitys(self, student_id: uuid.UUID):
        query = """
            SELECT a.id, a.name, a.location, a.status, a.description, a.start_time, a.end_time
            FROM activity a
            JOIN registrations r ON a.id = r.activity_id
            WHERE r.student_id = $1
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, student_id)
        
_activity_repo = None
async def get_activity_repo():
    global _activity_repo
    if _activity_repo is None:
        pool = await get_db_pool()
        _activity_repo = ActivityRepository(pool)
    return _activity_repo