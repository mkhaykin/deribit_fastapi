import logging
from datetime import date, datetime, timezone
from typing import Any

import asyncpg
from fastapi import HTTPException
from pydantic import BaseModel

from config import config
from null_logger import NullLogger

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


def _end_date(target_date: date) -> datetime:
    return datetime(
        target_date.year,
        target_date.month,
        target_date.day,
        23,
        59,
        59,
        999999,
        tzinfo=timezone.utc,
    )


class PriceService:
    _pg_dsn: str
    _logger: logging.Logger

    def __init__(
        self,
        *,
        logger: logging.Logger | None = None,
    ) -> None:
        self._pg_dsn = config.DATABASE_DSN
        self._logger = logger or NullLogger(__name__)

    async def _get_connection(self) -> asyncpg.Connection:
        try:
            return await asyncpg.connect(self._pg_dsn)
        except Exception as e:
            self._logger.exception(f"Error connecting to PostgreSQL: {e}")
            raise HTTPException(status_code=500, detail="Database connection error") from None

    async def _fetch[T: BaseModel](self, query: str, *args: Any, schema: type[T]) -> list[T]:
        conn = await self._get_connection()
        result: list[T] = []
        try:
            self._logger.debug(query)
            rows = await conn.fetch(query, *args)
            self._logger.debug(f"fetched {len(rows)} rows")
            result.extend(schema.model_validate(dict(row)) for row in rows)
        except Exception as e:
            self._logger.exception(f"fetch error: {e}")
            raise HTTPException(status_code=500, detail="Database error") from None
        finally:
            await conn.close()
        return result

    async def get_all_by_ticker(self, ticker: str) -> list[IndexPriceResponse]:
        query = """
            SELECT id, ticker, price, timestamp
            FROM index_prices
            WHERE ticker = $1
            ORDER BY timestamp DESC
        """
        return await self._fetch(query, ticker, schema=IndexPriceResponse)

    async def get_latest_by_ticker(self, ticker: str) -> IndexPriceResponse | None:
        query = """
            SELECT id, ticker, price, timestamp
            FROM index_prices
            WHERE ticker = $1
            ORDER BY timestamp DESC
            LIMIT 1
        """
        rows = await self._fetch(query, ticker, schema=IndexPriceResponse)
        if not rows:
            return None

        if len(rows) > 1:
            self._logger.error("Found %s rows, but expected one", len(rows))

        return rows[0]

    async def get_by_ticker_and_date(self, ticker: str, target_date: date) -> list[IndexPriceResponse]:
        query = """
            SELECT id, ticker, price, timestamp
            FROM index_prices
            WHERE ticker = $1 AND timestamp BETWEEN $2 AND $3
            ORDER BY timestamp DESC
        """
        start_timestamp = int(_start_date(target_date).timestamp())
        end_timestamp = int(_end_date(target_date).timestamp())
        return await self._fetch(query, ticker, start_timestamp, end_timestamp, schema=IndexPriceResponse)
