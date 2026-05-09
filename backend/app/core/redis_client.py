import json
from typing import Any, Optional
import redis.asyncio as aioredis

from app.core.config import settings

_redis_pool: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_pool


async def close_redis() -> None:
    global _redis_pool
    if _redis_pool is not None:
        await _redis_pool.aclose()
        _redis_pool = None


class CacheClient:
    def __init__(self, redis: aioredis.Redis):
        self._r = redis

    async def get(self, key: str) -> Optional[Any]:
        raw = await self._r.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return raw

    async def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        payload = json.dumps(value) if not isinstance(value, str) else value
        await self._r.setex(key, ttl_seconds, payload)

    async def delete(self, key: str) -> None:
        await self._r.delete(key)

    async def exists(self, key: str) -> bool:
        return bool(await self._r.exists(key))

    async def publish(self, channel: str, message: Any) -> None:
        payload = json.dumps(message) if not isinstance(message, str) else message
        await self._r.publish(channel, payload)


# Key builders — single source of truth for all Redis key patterns
class RedisKeys:
    @staticmethod
    def session_context(session_id: str) -> str:
        return f"aria:session:{session_id}:context"

    @staticmethod
    def schema_cache(connection_id: str) -> str:
        return f"aria:schema:{connection_id}:cache"

    @staticmethod
    def query_result(query_execution_id: str) -> str:
        return f"aria:query:{query_execution_id}:result"

    @staticmethod
    def stream_channel(session_id: str) -> str:
        return f"aria:stream:{session_id}"

    @staticmethod
    def connection_test(connection_id: str) -> str:
        return f"aria:conn:{connection_id}:test"

    @staticmethod
    def schema_task(connection_id: str) -> str:
        return f"aria:schema:{connection_id}:task"

    @staticmethod
    def user_rate_limit(user_id: str) -> str:
        return f"aria:ratelimit:{user_id}"


async def get_cache_client() -> CacheClient:
    redis = await get_redis()
    return CacheClient(redis)
