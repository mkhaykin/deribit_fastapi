from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg
from fastapi import FastAPI
from redis.asyncio import from_url
from starlette.staticfiles import StaticFiles

from config import config

from .routers.health import router as health_router
from .routers.price import router as price_router
from .routers.root import router as root_router


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

    base_dir = Path(__file__).parent.absolute()
    static_dir = str((base_dir / "static"))
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.state.static_dir = static_dir

    app.include_router(health_router)
    app.include_router(price_router, prefix="/api/v1")
    app.include_router(root_router)

    return app
