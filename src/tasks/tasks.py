import asyncio
import logging
import time

from celery import Celery

from config import config

from .fetch_data import get_prices
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


@app_celery.task(name="price_collector.task_request")
def task_request() -> None:
    ts = int(time.time())
    results = [
        DTO(
            ticker=result.index_name,
            price=result.result.index_price,
            ts=ts,
        )
        for result in asyncio.run(get_prices(logger=logger))
    ]

    store_prices(results, logger=logger)


app_celery.conf.beat_schedule = {
    "request-to-deribit-every-minute": {
        "name": "request to deribit.com",
        "task": task_request.name,
        "schedule": config.REQUEST_SCHEDULE,
    },
}
