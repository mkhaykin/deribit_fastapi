import asyncio
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable, List, Literal, Type

import aiohttp
from aiohttp import ClientSession
from fastapi import status
from pydantic import BaseModel, ValidationError, model_validator

from null_logger import NullLogger

HTTP_TIMEOUT = aiohttp.ClientTimeout(total=6, connect=2, sock_read=4)

TICKETS_VALUES = Literal["btc_usd", "eth_usd"]
TICKETS_NAMES: frozenset[TICKETS_VALUES] = frozenset(("btc_usd", "eth_usd"))


class FetchResultModel(BaseModel):
    estimated_delivery_price: Decimal
    index_price: Decimal


class FetchModel(BaseModel):
    usIn: int
    usOut: int
    usDiff: int
    result: FetchResultModel
    index_name: str

    @model_validator(mode="before")
    @classmethod
    def inject_context_data(cls, data: Any, info: Any) -> Any:
        if info.context and isinstance(data, dict):
            data.update(info.context)
        return data


class RetryableAPIError(Exception):
    """исключение, допускающее повтор"""


@dataclass(frozen=True, slots=True)
class QueryTicket:
    index_name: Literal["btc_usd", "eth_usd"]
    url: str


async def _fetch_index[T: BaseModel](
    session: ClientSession,
    url: str,
    index_name: str,
    model: Type[T],
    *,
    logger: logging.Logger | None = None,
) -> T:
    log = logger or NullLogger(__name__)

    # в общем можно без try except, но так как я вызываю в asyncio.gather,
    # то больше логировать негде
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            raw_data: bytes = await response.read()
    except aiohttp.ClientResponseError as exc:
        log.error("Response error fetching %s from %s: %s", index_name, url, exc)
        raise
    except aiohttp.ClientError as exc:
        log.error("Network error fetching %s from %s: %s", index_name, url, exc)
        raise

    try:
        return model.model_validate_json(raw_data, context={"index_name": index_name})
    except ValidationError:
        log.error(
            "Validation failed for index '%s' at URL %s. Raw response: %r",
            index_name,
            url,
            raw_data,
            exc_info=True,
        )
        raise


async def get_prices(
    tickets: Iterable[QueryTicket],
    *,
    logger: logging.Logger | None = None,
    timeout: aiohttp.ClientTimeout = HTTP_TIMEOUT,
) -> tuple[List[FetchModel], Exception | None]:
    log = logger or NullLogger(__name__)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [
            _fetch_index(
                session,
                item.url,
                item.index_name,
                FetchModel,
            )
            for item in tickets
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    ans: List[FetchModel] = []
    retried_tickets = []
    exc: Exception | None = None
    for ticket, result in zip(tickets, results, strict=True):
        if isinstance(result, FetchModel):
            ans.append(result)
            continue

        is_5xx = (
            isinstance(result, aiohttp.ClientResponseError)
            and result.status >= status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        is_network_or_timeout = isinstance(result, (aiohttp.ClientError, TimeoutError, asyncio.TimeoutError))

        if is_5xx or is_network_or_timeout:
            retried_tickets.append(ticket.index_name)

    if len(ans) != len(results):
        succeeded = {item.index_name for item in ans}
        missing = sorted({ticket.index_name for ticket in tickets} - succeeded)
        log.warning(f"Incomplete price set; missing: {', '.join(missing)}")

    if retried_tickets:
        exc = RetryableAPIError(f"API failed for tickets: {', '.join(retried_tickets)}")

    return ans, exc
