import json
import redis.asyncio as aioredis

from app.config import settings

_redis: aioredis.Redis | None = None

# - get_redis() — lazy singleton async Redis client
# - publish(channel, data) — serializes a dict to JSON and publishes to a channel
# - close_redis() — called on app shutdown to cleanly close the connection

async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def publish(channel: str, data: dict):
    r = await get_redis()
    await r.publish(channel, json.dumps(data))


async def close_redis():
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
