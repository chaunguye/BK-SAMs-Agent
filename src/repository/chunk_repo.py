from src.database.database_connect import get_db_pool
class ChunkRepository:
    def __init__(self, pool):
        self.pool = pool

    async def insert_document(self, id, file_path, file_type, author, file_name, activity_id=None):
        query = """
            INSERT INTO document (id, file_path, file_type, author, file_name, activity_id)
            VALUES ($1, $2, $3, $4, $5, $6) RETURNING id
        """
        async with self.pool.acquire() as conn:
            return await conn.execute(query, id, file_path, file_type, author, file_name, activity_id)
        
    async def batch_insert_chunks(self, chunks_data):
        # chunks_data is a list of tuples: (id, text, embedding, doc_id)
        query = """
            INSERT INTO chunk (id, text_content, embeddings, document_id)
            VALUES ($1, $2, $3::vector, $4)
        """
        async with self.pool.acquire() as conn:
            await conn.executemany(query, chunks_data)
    
    async def search_chunks_by_embedding(self, query_embedding, top_k=5):
        query = """
            SELECT id, text_content, embeddings <=> $1::vector AS distance
            FROM chunk
            ORDER BY embeddings <=> $1::vector
            LIMIT $2
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, query_embedding, top_k)
        return [dict(row) for row in rows]

    async def search_relevant_activity(self, time_start: str = None, name: str = None, time_end: str = None, location: str = None, status: str = None, sort_by: str = "number_of_conversion_day", desc: bool = True, top_k: int = 5):
        query = """
            SELECT *
            FROM activity
            WHERE start_time >= COALESCE($1::timestamp, current_date)
            AND ($2::text IS NULL OR name ILIKE '%' || $2 || '%')
            AND ($3::timestamp IS NULL OR end_time <= $3)
            AND ($4::text IS NULL OR location ILIKE '%' || $4 || '%')
            AND ($5::activity_status IS NULL OR status = $5)
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

_chunk_repo = None
async def get_chunk_repo():
    global _chunk_repo
    if _chunk_repo is None:
        pool = await get_db_pool()
        _chunk_repo = ChunkRepository(pool)
    return _chunk_repo