import asyncio
import logging
import time

from celery import Celery, chain

from config import config

from .fetch_data import RetryableAPIError, get_prices
from .store_data import DTO, store_prices


class CeleryConfig:
    enable_utc = True
    timezone = "Europe/Moscow"
    broker_url = config.REDIS_DSN
    broker_connection_retry_on_startup = False
    result_backend = "rpc://"
    worker_send_task_event = False
    task_ignore_result = True

    task_soft_time_limit = 20
    task_time_limit = 25

    task_acks_late = False
    worker_prefetch_multiplier = 1


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


app_celery = Celery(__name__)
app_celery.config_from_object(CeleryConfig)


@app_celery.task(
    name="price_collector.fetch_prices",
    autoretry_for=(RetryableAPIError,),
    max_retries=3,
    default_retry_delay=20,
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


@app_celery.task(
    name="price_collector.store_prices",
    bind=True,
    max_retries=5,
    default_retry_delay=10,
)
def store_prices_task(self, raw_results: list[dict]) -> None:  # noqa: ANN001
    result = store_prices([DTO.from_dict(item) for item in raw_results], logger=logger)
    if not result:
        raise self.retry(exc=RuntimeError("All API sources failed or timed out"))


@app_celery.task(name="price_collector.task_request")
def task_request() -> None:
    pipeline = chain(fetch_prices.s(), store_prices_task.s())
    pipeline.apply_async()


app_celery.conf.beat_schedule = {
    "request-to-deribit-every-minute": {
        "name": "request to deribit.com",
        "task": task_request.name,
        "schedule": config.REQUEST_SCHEDULE,
    },
}
