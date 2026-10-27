import asyncio
import logging
import time

from celery import chain, shared_task

from .fetch_data import get_prices
from .store_data import DTO, store_prices

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@shared_task(
    name="price_collector.fetch_prices",
)
def fetch_prices() -> list[dict]:
    items, exc = asyncio.run(get_prices(logger=logger))
    if exc is not None and not items:
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
    pipeline = chain(fetch_prices.s(), store_prices_task.s())
    pipeline.apply_async()
