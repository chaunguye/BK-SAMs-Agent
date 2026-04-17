from src.database.database_connect import get_db_pool
from datetime import datetime

class ChunkRepository:
    def __init__(self, pool):
        self.pool = pool

    async def insert_document(self, id, file_path, file_type, author, file_name, activity_id):
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
    
    async def search_chunks_of_activity(self, query_embedding, activity_id, top_k=5):
        query = """
            SELECT id, text_content, embeddings <=> $1::vector AS distance
            FROM chunk
            WHERE document_id IN (
                SELECT id FROM document WHERE activity_id = $2
            )
            ORDER BY embeddings <=> $1::vector
            LIMIT $3
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(query, query_embedding, str(activity_id), top_k)
        return [dict(row) for row in rows]
    
    async def search_chunks_of_activity_hybrid(self, query_embedding, query_text, activity_id, top_k=5):
        query = """
            SELECT id, text_content, embeddings <=> $1::vector AS distance
            FROM chunk
            WHERE document_id IN (
                SELECT id FROM document WHERE activity_id = $2
            )
            ORDER BY embeddings <=> $1::vector
            LIMIT $3
        """
        async with self.pool.acquire() as conn:
            semantic_rows = await conn.fetch(query, query_embedding, str(activity_id), top_k)

        query = """
        SELECT id, text_content, 
            ts_rank_cd(
                fts_tokens, 
                websearch_to_tsquery('simple', $2), 
                32
            ) AS rank
        FROM chunk 
        WHERE activity_id = $1 
        AND fts_tokens @@ websearch_to_tsquery('simple', $2)
        ORDER BY rank DESC 
        LIMIT $3
        """

        async with self.pool.acquire() as conn:
            textual_rows = await conn.fetch(query, str(activity_id), query_text, top_k)

        return await self.rrf_compute(semantic_rows, textual_rows)
    
    async def rrf_compute(self, semantic_rows, textual_rows, k=60):
        # Create a dictionary to store the best score for each chunk
        scores = {}

        # Process semantic results
        for rank, record in enumerate(semantic_rows, start=1):
            chunk_id = record['id']
            score = 1 / (k + rank)  # RRF score for semantic results
            if chunk_id not in scores:
                scores[chunk_id] = score
            else:
                scores[chunk_id] += score

        # Process textual results
        for rank, record in enumerate(textual_rows, start=1):
            chunk_id = record['id']
            score = 1 / (k + rank)  # RRF score for textual results
            if chunk_id not in scores:
                scores[chunk_id] = score
            else:
                scores[chunk_id] += score

        # Sort chunks by their combined RRF scores
        sorted_chunks = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        return sorted_chunks[:5]  # Return top 5 chunks based on RRF scores

_chunk_repo = None
async def get_chunk_repo():
    global _chunk_repo
    if _chunk_repo is None:
        pool = await get_db_pool()
        _chunk_repo = ChunkRepository(pool)
    return _chunk_repo