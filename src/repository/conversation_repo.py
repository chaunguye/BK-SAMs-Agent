from src.database.database_connect import get_db_pool

class ConversationRepository:
    def __init__(self, pool):
        self.pool = pool

    def save_conversation(self, conversation_id, conversation_data):
        query = """
            INSERT INTO message (sender_type, text_content, conversation_id)
            VALUES ($1, $2, $3)
        """
        return self.pool.execute(query, conversation_data['sender_type'], conversation_data['text_content'], conversation_id)

    def get_conversation(self, conversation_id):
        query = """
            SELECT * FROM message
            WHERE conversation_id = $1
            ORDER BY timestamp ASC
        """
        return self.pool.fetch(query, conversation_id)
    def create_conversation(self, conversation_id):
        query = """
            INSERT INTO conversation (tittle, user_id)
            VALUES ($1, $2)
        """
        return self.pool.execute(query, conversation_id)
    

_conversation_repo = None
async def get_conversation_repo():
    global _conversation_repo
    if _conversation_repo is None:
        pool = await get_db_pool()
        _conversation_repo = ConversationRepository(pool)
    return _conversation_repo