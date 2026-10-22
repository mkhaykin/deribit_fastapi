import logging
from typing import Any

import asyncpg
from fastapi import HTTPException
from pydantic import BaseModel

from null_logger import NullLogger

from .schemas import IndexPriceResponse


class PriceRepository:
    _logger: logging.Logger
    _pool: asyncpg.Pool

    def __init__(
        self,
        pool: asyncpg.Pool,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self._logger = logger or NullLogger(__name__)
        self._pool = pool

    async def _fetch[T: BaseModel](self, query: str, *args: Any, schema: type[T]) -> list[T]:
        result: list[T] = []
        try:
            self._logger.debug(query)
            async with self._pool.acquire() as conn:
                rows = await conn.fetch(query, *args)
            self._logger.debug(f"fetched {len(rows)} rows")
        except Exception as e:
            self._logger.error(f"fetch error: {e}")
            raise HTTPException(status_code=500, detail="Database error") from None

        result.extend(schema.model_validate(dict(row)) for row in rows)
        return result

    async def get_all_by_ticker(self, ticker: str) -> list[IndexPriceResponse]:
        query = """
            SELECT id, ticker, price, timestamp
            FROM index_prices
            WHERE ticker = $1
            ORDER BY timestamp DESC LIMIT 1000;
        """
        return await self._fetch(query, ticker, schema=IndexPriceResponse)

    async def get_latest_by_ticker(self, ticker: str) -> IndexPriceResponse | None:
        query = """
            SELECT id, ticker, price, timestamp
            FROM index_prices
            WHERE ticker = $1
            ORDER BY timestamp DESC
            LIMIT 1;
        """
        rows = await self._fetch(query, ticker, schema=IndexPriceResponse)
        if not rows:
            return None

        if len(rows) > 1:
            self._logger.error("Found %s rows, but expected one", len(rows))

        return rows[0]

    async def get_by_ticker_and_date(
        self,
        ticker: str,
        start_ts: int,
        end_ts: int,
    ) -> list[IndexPriceResponse]:
        query = """
            SELECT id, ticker, price, timestamp
            FROM index_prices
            WHERE ticker = $1 AND timestamp >= $2 AND timestamp < $3
            ORDER BY timestamp DESC LIMIT 1000;
        """
        return await self._fetch(query, ticker, start_ts, end_ts, schema=IndexPriceResponse)
