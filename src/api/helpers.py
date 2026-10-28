import logging
from typing import Annotated

import asyncpg
from fastapi import Depends
from redis.asyncio import Redis
from starlette.requests import Request

from .services.health import HealthService
from .services.price import PriceService


def get_pg_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.pool


def get_redis(request: Request) -> Redis:
    return request.app.state.redis


def get_logger() -> logging.Logger:
    return logging.getLogger("price_service")


def get_price_service(
    pool: Annotated[asyncpg.Pool, Depends(get_pg_pool)],
    redis: Annotated[Redis, Depends(get_redis)],
    *,
    logger: Annotated[logging.Logger, Depends(get_logger)],
) -> PriceService:
    return PriceService(pool=pool, redis=redis, logger=logger)


def get_health_service(
    pool: Annotated[asyncpg.Pool, Depends(get_pg_pool)],
    redis: Annotated[Redis, Depends(get_redis)],
    *,
    logger: Annotated[logging.Logger, Depends(get_logger)],
) -> HealthService:
    return HealthService(pool=pool, redis=redis, logger=logger)
