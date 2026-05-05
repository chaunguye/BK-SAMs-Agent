from typing import List

from src.database.database_connect import get_db_pool
import uuid
from datetime import datetime
import logfire

class ActivityRepository:
    def __init__(self, pool):
        self.pool = pool

    async def register_activity(self, student_id: uuid.UUID, activity_id: str):
        query = """
            INSERT INTO registrations (student_id, activity_id)
            SELECT $1, $2
            WHERE EXISTS (
                SELECT max_slots FROM activity WHERE id = $2
                AND max_slots > (
                    SELECT COUNT(student_id) FROM registrations WHERE activity_id = $2
                )
            )
            AND NOT EXISTS (
                SELECT 1 FROM blacklist
                WHERE student_id = $1 AND banned_faculty_id = (SELECT faculty_id FROM activity WHERE id = $2)
                AND banned_until >= NOW() AND deleted_at IS NULL
            )
            RETURNING id
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchrow(query, student_id, activity_id)
            return result is not None  
            
        
    async def check_availability(self, conn,activity_id: str):
        query = """
            SELECT max_slots - COUNT(r.student_id) AS available_slots
            FROM activity a
            LEFT JOIN registrations r ON a.id = r.activity_id
            WHERE a.id = $1
            GROUP BY a.max_slots
        """
        result = await conn.fetchrow(query, activity_id)
        return result['available_slots'] if result else 0
        
    async def check_blacklist(self, conn, student_id: uuid.UUID, activity_id: str):
        query = """
            SELECT EXISTS (
                SELECT 1
                FROM blacklist
                WHERE student_id = $1 
                AND banned_faculty_id = (SELECT faculty_id FROM activity WHERE id = $2)
                AND banned_until >= NOW() AND deleted_at IS NULL
            ) AS is_blacklisted
        """
        result = await conn.fetchrow(query, student_id, activity_id)
        return result['is_blacklisted'] if result else False

    async def unregister_activity(self, student_id: uuid.UUID, activity_id: str):
        query = """
            DELETE FROM registrations
            WHERE student_id = $1 AND activity_id = $2
            AND EXISTS (
                SELECT 1 FROM activity WHERE id = $2 AND start_time > NOW() + INTERVAL '1 day'
            )
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

    async def get_activity_id_hybrid(self, activity_name: str, activity_embedding: str):
        logfire.info(f"Searching for activity with name: {activity_name} and embedding: {activity_embedding}")
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
            ORDER BY activity_name_embeddings <=> $1 LIMIT 10
            """
        async with self.pool.acquire() as conn:
            embedding_results = await conn.fetch(query, activity_embedding)

        return await self.rrf_compute(trigram_results, embedding_results)

        
    async def rrf_compute(self, trigram_results, embedding_results, k=60):
        logfire.info(f"Computing RRF scores for {len(trigram_results)} trigram results and {len(embedding_results)} embedding results with k={k}")
        #{ activity_id: {"score": total_rrf_score, "data": full_record_object} }
        results_map = {}

        # Helper function to process results
        def process_results(records):
            for rank, record in enumerate(records, start=1):
                activity_id = record['id']
                score = 1 / (k + rank)
                
                if activity_id not in results_map:
                    # Store both the score AND the original record data
                    results_map[activity_id] = {
                        "score": score,
                        "data": dict(record) # Convert asyncpg Record to Dict
                    }
                else:
                    results_map[activity_id]["score"] += score

        process_results(trigram_results)
        process_results(embedding_results)

        # Sort by the nested 'score' value
        sorted_items = sorted(
            results_map.values(), 
            key=lambda x: x["score"], 
            reverse=True
        )
        logfire.info(f"RRF computation completed. Sorted results: {sorted_items if sorted_items else 'No results found'}")
        return sorted_items[:5] if sorted_items else None

    async def get_activity_details(self, activity_id: uuid.UUID):
        query = """
            SELECT a.id, a.name, a.location, a.status, a.description, a.start_time, a.end_time, a.max_slots, a.number_of_conversion_day, f.name as organizer_faculty_name
            FROM activity a 
            LEFT JOIN faculty f ON a.faculty_id = f.id
            WHERE a.id = $1
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, activity_id)

    async def get_registered_activities(self, student_id: uuid.UUID):
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