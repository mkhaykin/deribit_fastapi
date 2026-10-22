import logging

from pydantic import ValidationError
from redis import RedisError
from redis.asyncio import Redis

from null_logger import NullLogger

from ..schemas import IndexPriceResponse


class PriceCacheService:
    _logger: logging.Logger
    _redis: Redis

    def __init__(
        self,
        redis: Redis,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self._redis = redis
        self._logger = logger or NullLogger(__name__)

    async def get_latest(
        self,
        ticker: str,
    ) -> IndexPriceResponse | None:
        self._logger.debug("Looking up cached value for %s", ticker)
        try:
            value = await self._redis.get(
                f"price:latest:{ticker}",
            )
        except RedisError as e:
            self._logger.error("Redis connection failed: %s", e)
            return None

        if value is None:
            self._logger.debug("No cache entry found for key %s", ticker)
            return None

        try:
            return IndexPriceResponse.model_validate_json(value)
        except ValidationError:
            self._logger.debug("Malformed cache entry for key %s: %s", ticker, value)
            await self.clear_latest(ticker)
            return None

    async def set_latest(
        self,
        ticker: str,
        price: IndexPriceResponse,
        ttl: int = 30,
    ) -> None:
        self._logger.debug("Cached price for %s: %s", ticker, price)
        try:
            await self._redis.set(
                f"price:latest:{ticker}",
                price.model_dump_json(),
                ex=ttl,
            )
        except RedisError as e:
            self._logger.error("Redis connection failed: %s", e)
            return None

    async def clear_latest(
        self,
        ticker: str,
    ) -> None:
        await self._redis.delete(f"price:latest:{ticker}")
