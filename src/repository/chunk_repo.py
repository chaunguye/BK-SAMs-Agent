from src.database.database_connect import get_db_pool
class ChunkRepository:
    def __init__(self, pool):
        self.pool = pool

    async def insert_document(self, id, file_path, file_type, author, activity_id=None):
        query = """
            INSERT INTO document (id, file_path, file_type, author, activity_id)
            VALUES ($1, $2, $3, $4, $5) RETURNING id
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, id, file_path, file_type, author, activity_id)
        
    async def batch_insert_chunks(self, chunks_data):
        # chunks_data is a list of tuples: (id, text, embedding, doc_id)
        query = """
            INSERT INTO chunk (id, text_content, embedding, document_id)
            VALUES ($1, $2, $3::vector, $4)
        """
        async with self.pool.acquire() as conn:
            await conn.executemany(query, chunks_data)

async def initialize_chunk_repo():
    pool = await get_db_pool()
    chunkRepo = ChunkRepository(pool)
    return chunkRepo