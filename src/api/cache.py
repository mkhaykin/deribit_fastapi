import logging

from redis.asyncio import Redis

from null_logger import NullLogger

from .schemas import IndexPriceResponse


class PriceCache:
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
        self._logger.debug("Запрос кеша на %s", ticker)
        value = await self._redis.get(
            f"price:latest:{ticker}",
        )

        if value is None:
            self._logger.debug("Ключ %s не найден", ticker)
            return None

        return IndexPriceResponse.model_validate_json(value)

    async def set_latest(
        self,
        ticker: str,
        price: IndexPriceResponse,
        ttl: int = 30,
    ) -> None:
        await self._redis.set(
            f"price:latest:{ticker}",
            price.model_dump_json(),
            ex=ttl,
        )
        self._logger.debug("Кешируем %s = %s", ticker, price)
