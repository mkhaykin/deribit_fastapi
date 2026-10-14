from celery import Celery

from settings import settings


class CeleryConfig:
    enable_utc = True
    timezone = "Europe/Moscow"
    broker_url = f"redis://{settings.REDIS_SERVER}:6379/0"
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
    print("do something ...")


app_celery.conf.beat_schedule = {
    "request-to-deribit-every-minute": {
        "name": "request to deribit.com",
        "task": task_request.name,
        "schedule": settings.REQUEST_SCHEDULE,
    },
}
