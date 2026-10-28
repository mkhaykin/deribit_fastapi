import redis
from celery.utils.log import get_task_logger
from redis.exceptions import RedisError

logger = get_task_logger(__name__)


def invalidate(redis_client: redis.Redis, ticker: str) -> None:
    try:
        redis_client.delete(f"price:latest:{ticker}")
    except RedisError:
        logger.exception(
            "Failed to invalidate latest price cache for ticker %s",
            ticker,
        )
