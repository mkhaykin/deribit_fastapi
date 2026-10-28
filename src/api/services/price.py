import logging
from datetime import date, datetime, timedelta, timezone

import asyncpg
from redis.asyncio import Redis

from null_logger import NullLogger

from ..repository import PriceRepository
from ..schemas import IndexPriceResponse
from ..services.cache import LatestPriceCache


def _start_date(target_date: date) -> datetime:
    return datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        0,
        0,
        0,
        tzinfo=timezone.utc,
    )


class PriceService:
    _logger: logging.Logger
    _price_cache: LatestPriceCache
    _price_repo: PriceRepository

    def __init__(
        self,
        *,
        pool: asyncpg.Pool,
        redis: Redis,
        logger: logging.Logger | None = None,
    ) -> None:
        self._price_repo = PriceRepository(
            pool,
            logger=logger,
        )
        self._price_cache = LatestPriceCache(
            redis,
            logger=logger,
        )
        self._logger = logger or NullLogger(__name__)

    async def get_all_by_ticker(
        self,
        ticker: str,
        last_created_at: int | None = None,
        last_id: int | None = None,
        limit: int | None = None,
    ) -> list[IndexPriceResponse]:
        # TODO проверку на last_created_at и  last_id сюда
        return await self._price_repo.get_all_by_ticker(
            ticker,
            last_created_at,
            last_id,
            limit,
        )

    async def get_latest_by_ticker(self, ticker: str) -> IndexPriceResponse | None:
        cached = await self._price_cache.get_latest(ticker)
        if cached is not None:
            return cached

        price = await self._price_repo.get_latest_by_ticker(ticker)
        if price is not None:
            await self._price_cache.set_latest(ticker, price)
        return price

    async def get_by_ticker_and_date(
        self,
        ticker: str,
        target_date: date,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[IndexPriceResponse]:
        start_timestamp = int(_start_date(target_date).timestamp())
        end_timestamp = int(_start_date(target_date + timedelta(days=1)).timestamp())
        return await self._price_repo.get_by_ticker_and_date(
            ticker,
            start_timestamp,
            end_timestamp,
            limit,
            offset,
        )
