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

_chunk_repo = None
async def get_chunk_repo():
    global _chunk_repo
    if _chunk_repo is None:
        pool = await get_db_pool()
        _chunk_repo = ChunkRepository(pool)
    return _chunk_repo