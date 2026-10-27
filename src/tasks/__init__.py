__all__ = [
    "app_celery",
    "task_request",
]

from .main import app_celery
from .tasks import task_request
