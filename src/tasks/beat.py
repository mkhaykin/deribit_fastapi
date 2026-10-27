from config import config

from .main import app_celery

app_celery.conf.beat_schedule = {
    "request-to-deribit-every-minute": {
        "name": "request to deribit.com",
        "task": "price_collector.task_request",
        "schedule": config.REQUEST_SCHEDULE,
    },
}
