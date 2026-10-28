from typing import Type

from celery import Celery
from celery.signals import (
    worker_process_init,
    worker_process_shutdown,
)
from celery.utils.log import get_logger

from config import config
from helpers import get_redis
from tasks.price_collector.fetch_data import RetryableAPIError

logger = get_logger(__name__)


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

    task_annotations = {
        "price_collector.fetch_prices": {
            "max_retries": 3,
            "default_retry_delay": 10,
            "autoretry_for": (RetryableAPIError,),
        },
        "price_collector.store_prices": {
            "max_retries": 5,
            "default_retry_delay": 3,
        },
    }


def create_celery_app(config_obj: Type = CeleryConfig) -> Celery:
    app = Celery(__name__)
    app.config_from_object(config_obj)
    app.autodiscover_tasks(["tasks.price_collector"])

    return app


app_celery = create_celery_app()


@worker_process_init.connect(weak=False)
def init_worker_client(**kwargs) -> None:  # noqa: ARG001, ANN003
    logger.debug("worker process init")

    try:
        logger.debug("Get redis client")
        redis_client = get_redis(config)
        app_celery.redis_client = redis_client
    except Exception:
        logger.exception("Some redis client prepare error")


@worker_process_shutdown.connect(weak=False)
def shutdown_worker_client(**kwargs) -> None:  # noqa: ARG001, ANN003
    """Срабатывает при остановке воркер-процесса."""
    redis_client = getattr(app_celery, "redis_client", None)
    if redis_client:
        logger.debug("Stopping redis client")
        app_celery.redis_client = None
        redis_client.close()
