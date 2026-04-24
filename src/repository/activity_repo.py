from typing import List

from src.database.database_connect import get_db_pool
import uuid
from datetime import datetime

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

    async def get_activity_id_hybrid(self, activity_name: str):
        query = """
            SELECT id, name, location, status, description, start_time, end_time, similarity(name::text, $1) as score
            FROM activity
            WHERE name % $1
            ORDER BY score DESC
            LIMIT 10
        """
        async with self.pool.acquire() as conn:
            trigram_results = await conn.fetch(query, activity_name)

        query = """
            SELECT id, name, location, status, description, start_time, end_time
            FROM activity
            ORDER BY name_embedding <=> $1 LIMIT 10
            """
        async with self.pool.acquire() as conn:
            embedding_results = await conn.fetch(query, activity_name)

        return await self.rrf_compute(trigram_results, embedding_results)

        
    async def rrf_compute(self, trigram_results, embedding_results, k=60):
        # Create a dictionary to store the best score for each activity
        scores = {}

        # Process trigram results
        for rank, record in enumerate(trigram_results, start=1):
            activity_id = record['id']
            score = 1 / (k + rank)  # RRF score for trigram results
            if activity_id not in scores:
                scores[activity_id] = score
            else:
                scores[activity_id] += score

        # Process embedding results
        for rank, record in enumerate(embedding_results, start=1):
            activity_id = record['id']
            score = 1 / (k + rank)  # RRF score for embedding results
            if activity_id not in scores:
                scores[activity_id] = score
            else:
                scores[activity_id] += score

        # Sort activities by their combined RRF scores
        sorted_activities = sorted(scores.items(), key=lambda item: item[1], reverse=True)

        return sorted_activities[:1]  # Return top 1 activity based on RRF scores

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
    
    async def get_activity_by_id(self, activity_id: uuid.UUID):
        query = """
            SELECT id, name, location, status, description, start_time, end_time
            FROM activity
            WHERE id = $1
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, activity_id)
        
    async def update_activity_embedding(self, activity_id: uuid.UUID, embedding: List):
        query = """
            UPDATE activity
            SET activity_name_embeddings = $1::vector
            WHERE id = $2
        """
        async with self.pool.acquire() as conn:
            await conn.execute(query, "[" + ",".join(str(x) for x in embedding) + "]", str(activity_id))
        
_activity_repo = None
async def get_activity_repo():
    global _activity_repo
    if _activity_repo is None:
        pool = await get_db_pool()
        _activity_repo = ActivityRepository(pool)
    return _activity_repo