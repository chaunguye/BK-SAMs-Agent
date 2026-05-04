import asyncpg
import os
from dotenv import load_dotenv

load_dotenv()

_pool = None

async def get_db_pool():
    global _pool
    if _pool is None:
        try:
            _pool = await asyncpg.create_pool(
                dsn=os.getenv("DB_URL"),
                min_size=1,
                max_size=10
            )
        except Exception as e:
            print(f"Error creating database pool: {e}")
            raise
    return _pool