import logging
from typing import Any

import asyncpg
from pydantic import BaseModel

from null_logger import NullLogger

from .schemas import IndexPriceResponse


class RepositoryError(RuntimeError):
    """An error occurred while accessing the database."""


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
        except (
            asyncpg.PostgresError,
            asyncpg.InterfaceError,
            OSError,
            TimeoutError,
        ) as e:
            self._logger.exception("Database fetch error")
            raise RepositoryError("Database operation failed") from e

        result.extend(schema.model_validate(dict(row)) for row in rows)
        return result

    async def get_all_by_ticker(
        self,
        ticker: str,
        last_created_at: int | None = None,
        last_id: int | None = None,
        limit: int | None = None,
    ) -> list[IndexPriceResponse]:
        query, args = self._build_query_for_all(ticker, last_created_at, last_id, limit)

        return await self._fetch(
            query,
            *args,
            schema=IndexPriceResponse,
        )

    @staticmethod
    def _build_query_for_all(
        ticker: str,
        last_created_at: int | None,
        last_id: int | None,
        limit: int | None,
    ) -> tuple[str, list[int | str]]:
        if (last_created_at is None) != (last_id is None):
            raise ValueError("Both 'last_created_at' and 'last_id' must be provided together")

        query_parts: list[str] = [
            """
            SELECT id, ticker, price, timestamp
            FROM index_prices
            WHERE ticker = $1
        """,
        ]
        args: list[int | str] = [ticker]

        if last_created_at is not None and last_id is not None:
            query_parts.append(f" AND (timestamp, id) < (${len(args) + 1}, ${len(args) + 2})")
            args.extend((last_created_at, last_id))

        query_parts.append("ORDER BY timestamp DESC, id DESC")

        if limit is not None:
            query_parts.append(f"LIMIT ${len(args) + 1}")
            args.append(limit)

        return "\n".join(query_parts), args

    async def get_latest_by_ticker(self, ticker: str) -> IndexPriceResponse | None:
        query = """
            SELECT id, ticker, price, timestamp
            FROM index_prices
            WHERE ticker = $1
            ORDER BY timestamp DESC, id DESC
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
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[IndexPriceResponse]:
        query = """
            SELECT id, ticker, price, timestamp
            FROM index_prices
            WHERE ticker = $1 AND timestamp >= $2 AND timestamp < $3
            ORDER BY timestamp DESC LIMIT $4 OFFSET $5;
        """
        return await self._fetch(query, ticker, start_ts, end_ts, limit, offset, schema=IndexPriceResponse)
