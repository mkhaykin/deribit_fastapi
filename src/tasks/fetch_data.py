import asyncio
import logging
from decimal import Decimal
from typing import Any, List, Literal, Type

import aiohttp
from aiohttp import ClientSession
from pydantic import BaseModel, ValidationError, model_validator

from config import config
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


async def _fetch_url[T: BaseModel](
    session: ClientSession,
    index_name: Literal["btc_usd", "eth_usd"],
    model: Type[T],
    *,
    logger: logging.Logger | None = None,
) -> T:
    log = logger or NullLogger(__name__)

    url = f"{config.API_URL}/public/get_index_price?index_name={index_name}"

    try:
        async with session.get(url) as response:
            response.raise_for_status()
            text = await response.text()
    except aiohttp.ClientResponseError as exc:
        log.error("Response error fetching %s from %s: %s", index_name, url, exc)
        raise
    except aiohttp.ClientError as exc:
        log.error("Network error fetching %s from %s: %s", index_name, url, exc)
        raise

    try:
        return model.model_validate_json(text, context={"index_name": index_name})
    except ValidationError:
        log.error("Validation failed for %s. Raw text: %s", index_name, text, exc_info=True)
        raise


async def get_prices(
    *,
    logger: logging.Logger | None = None,
    timeout: aiohttp.ClientTimeout = HTTP_TIMEOUT,
    tickets: frozenset[TICKETS_VALUES] = TICKETS_NAMES,
) -> List[FetchModel]:
    log = logger or NullLogger(__name__)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [_fetch_url(session, index_name, FetchModel) for index_name in tickets]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        ans = [result for result in results if isinstance(result, FetchModel)]

        if len(ans) != len(results):
            succeeded = {item.index_name for item in ans}
            missing = sorted(tickets - succeeded)
            log.warning(f"Incomplete price set; missing: {', '.join(missing)}")

        return ans
