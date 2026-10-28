from redis import Redis, from_url

from config import Config
from config import config as default_config


def get_redis(config: Config = default_config) -> Redis:
    redis_client = from_url(
        config.REDIS_DSN,
        socket_timeout=config.REDIS_SOCKET_TIMEOUT,
        health_check_interval=config.REDIS_HEALTH_CHECK_INTERVAL,
    )

    return redis_client
