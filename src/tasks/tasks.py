import asyncio
import time
from typing import Literal, TypedDict

from celery import chain, shared_task
from celery.utils.log import get_task_logger

from config import config

from .fetch_data import QueryTicket, get_prices
from .store_data import DTO, store_prices

logger = get_task_logger(__name__)


class IndexDataDict(TypedDict):
    index_name: Literal["btc_usd", "eth_usd"]
    url: str


@shared_task(
    name="price_collector.fetch_prices",
)
def fetch_prices(indexes: list[IndexDataDict]) -> list[dict]:
    tickets = [
        QueryTicket(
            index_name=index["index_name"],
            url=index["url"],
        )
        for index in indexes
    ]

    items, exc = asyncio.run(
        get_prices(
            tickets,
            logger=logger,
        ),
    )

    if exc is not None and not items:
        # выбрасываем исключение только если ничего не получили.
        # Даже если отработала часть запросов, нас это устроит
        raise exc

    ts = int(time.time())
    # тут мы делаем вроде пустую работу, но нам все равно валидировать надо
    results = [
        DTO(
            ticker=item.index_name,
            price=item.result.index_price,
            ts=ts,
        )
        for item in items
    ]

    return [item.to_dict() for item in results]


@shared_task(
    name="price_collector.store_prices",
    bind=True,
)
def store_prices_task(self, raw_results: list[dict]) -> None:  # noqa: ANN001
    result = store_prices([DTO.from_dict(item) for item in raw_results], logger=logger)
    if not result:
        raise self.retry(exc=RuntimeError("All API sources failed or timed out"))


@shared_task(name="price_collector.task_request")
def task_request() -> None:
    pipeline = chain(
        fetch_prices.s(
            [
                {
                    "index_name": "btc_usd",
                    "url": config.INDEX_PRICE_URL.format(index_name="btc_usd"),
                },
                {
                    "index_name": "eth_usd",
                    "url": config.INDEX_PRICE_URL.format(index_name="eth_usd"),
                },
            ],
        ),
        store_prices_task.s(),
    )
    pipeline.apply_async()
