from celery import Celery

from config import config
from tasks.fetch_data import RetryableAPIError


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


app_celery = Celery(__name__)


app_celery.config_from_object(CeleryConfig)


app_celery.conf.task_annotations = {
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
