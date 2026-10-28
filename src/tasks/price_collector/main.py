import asyncio
import time

from celery import chain, shared_task
from celery.utils.log import get_task_logger

from config import config

from .cache import invalidate
from .fetch_data import QueryTicket, get_prices
from .schemas import IndexRequestTask, PriceSnapshot, PriceTransferPayload
from .store_data import store_prices

logger = get_task_logger(__name__)


@shared_task(
    name="price_collector.fetch_prices",
)
def fetch_prices(indexes: list[IndexRequestTask]) -> list[PriceTransferPayload]:
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
        PriceSnapshot(
            ticker=item.index_name,
            price=item.result.index_price,
            ts=ts,
        )
        for item in items
    ]

    return [item.to_payload() for item in results]


@shared_task(
    name="price_collector.store_prices",
    bind=True,
)
def store_prices_task(self, raw_results: list[PriceTransferPayload]) -> None:  # noqa: ANN001
    result = store_prices([PriceSnapshot.from_payload(item) for item in raw_results], logger=logger)
    if not result:
        raise self.retry(exc=RuntimeError("All API sources failed or timed out"))

    redis_client = getattr(self.app, "redis_client", None)
    if not redis_client:
        logger.warning("There is no redis client for this task")
    else:
        for item in raw_results:
            ticker = item["ticker"]
            logger.debug("Cache invalidation for %s", ticker)
            invalidate(redis_client, ticker)


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
