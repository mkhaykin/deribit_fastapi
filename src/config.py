import os


class Config:
    DATABASE_DSN: str = os.environ.get("DATABASE_DSN") or ""

    REDIS_DSN: str = os.environ.get("REDIS_DSN") or ""
    REDIS_SOCKET_TIMEOUT: float = 1.0
    REDIS_HEALTH_CHECK_INTERVAL: float = 30.0

    CACHE_LIFETIME: int = int(os.environ.get("CACHE_LIFETIME") or 5)
    REQUEST_SCHEDULE: int = int(os.environ.get("REQUEST_SCHEDULE") or 60)

    API_URL = "https://test.deribit.com/api/v2"


config = Config()
