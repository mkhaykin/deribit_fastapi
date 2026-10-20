from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI
from redis.asyncio import from_url

from config import config

from .base_router import router as base_router
from .router import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.pool = await asyncpg.create_pool(
        dsn=config.DATABASE_DSN,
        min_size=1,
        max_size=10,
    )
    app.state.redis = from_url(
        config.REDIS_DSN,
        socket_timeout=config.REDIS_SOCKET_TIMEOUT,
        health_check_interval=config.REDIS_HEALTH_CHECK_INTERVAL,
    )

    try:
        yield
    finally:
        await app.state.redis.close()
        await app.state.pool.close()


def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    app.include_router(router, prefix="/api/v1")
    app.include_router(base_router)

    return app
