import logging
from datetime import date, datetime, timedelta, timezone

import asyncpg

from null_logger import NullLogger

from .repository import PriceRepository
from .schemas import IndexPriceResponse


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
    _price_repo: PriceRepository
    _logger: logging.Logger

    def __init__(
        self,
        *,
        pool: asyncpg.Pool,
        logger: logging.Logger | None = None,
    ) -> None:
        self._price_repo = PriceRepository(
            pool,
            logger=logger,
        )
        self._logger = logger or NullLogger(__name__)

    async def get_all_by_ticker(self, ticker: str) -> list[IndexPriceResponse]:
        return await self._price_repo.get_all_by_ticker(ticker)

    async def get_latest_by_ticker(self, ticker: str) -> IndexPriceResponse | None:
        return await self._price_repo.get_latest_by_ticker(ticker)

    async def get_by_ticker_and_date(self, ticker: str, target_date: date) -> list[IndexPriceResponse]:
        start_timestamp = int(_start_date(target_date).timestamp())
        end_timestamp = int(_start_date(target_date + timedelta(days=1)).timestamp())
        return await self._price_repo.get_by_ticker_and_date(ticker, start_timestamp, end_timestamp)
