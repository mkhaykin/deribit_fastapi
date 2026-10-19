import asyncio
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
    task_time_limit = 60
    task_soft_time_limit = 50
    task_acks_late = True
    worker_prefetch_multiplier = 10


app_celery = Celery(__name__)
app_celery.config_from_object(CeleryConfig)


@app_celery.task
def task_request() -> None:
    results = [
        DTO(
            ticker=result.index_name,
            price=result.result.index_price,
            ts=int(time.time()),
        )
        for result in asyncio.run(get_prices())
    ]

    store_prices(results)


app_celery.conf.beat_schedule = {
    "request-to-deribit-every-minute": {
        "name": "request to deribit.com",
        "task": task_request.name,
        "schedule": config.REQUEST_SCHEDULE,
    },
}
