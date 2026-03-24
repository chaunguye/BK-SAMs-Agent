import os
from dotenv import load_dotenv
from redis.asyncio import Redis
load_dotenv()

class CacheManager:
    def __init__(self):
        self.redis_client = Redis(
        host=os.getenv('REDIS_HOST'),
        port=int(os.getenv('REDIS_PORT')),
        decode_responses=True,
        username=os.getenv('REDIS_USERNAME'),
        password=os.getenv('REDIS_PASSWORD'),
        )

    async def set_cache(self, key, value, expire_time=None):
        if expire_time:
            await self.redis_client.setex(key, expire_time, value)
        else:
            await self.redis_client.set(key, value)

    async def get_cache(self, key):
        return await self.redis_client.get(key)

    async def delete_cache(self, key):
        await self.redis_client.delete(key)

_cache_manager = None
def get_cache_manager():
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager

