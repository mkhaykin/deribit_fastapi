import logging

import asyncpg
from redis.asyncio import Redis

from null_logger import NullLogger


class HealthService:
    _logger: logging.Logger
    _pool: asyncpg.Pool
    _redis: Redis

    def __init__(
        self,
        *,
        pool: asyncpg.Pool,
        redis: Redis,
        logger: logging.Logger | None = None,
    ) -> None:
        self._pool = pool
        self._redis = redis
        self._logger = logger or NullLogger(__name__)

    async def db_ready(self) -> bool:
        try:
            query = "SELECT 1;"
            async with self._pool.acquire() as conn:
                await conn.fetch(query)
        except Exception as e:
            self._logger.error(f"db ready check error: {e}")
            return False

        return True

    async def cache_ready(self) -> bool:
        try:
            await self._redis.ping()
        except (ConnectionError, TimeoutError) as e:
            self._logger.error(f"redis ready check error: {e}")
            return False
        except Exception as e:
            self._logger.error(f"exception: {e}")
            return False

        return True

    async def ready(self) -> bool:
        return await self.db_ready() and await self.cache_ready()
