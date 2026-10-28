from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager
from pathlib import Path

import asyncpg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.asyncio import from_url
from starlette.staticfiles import StaticFiles

from config import config

from .logging_config import configure_logging
from .repository import RepositoryError
from .routers.health import router as health_router
from .routers.price import router as price_router
from .routers.root import router as root_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with AsyncExitStack() as stack:
        pg_pool = await asyncpg.create_pool(
            dsn=config.DATABASE_DSN,
            min_size=1,
            max_size=10,
        )
        stack.push_async_callback(pg_pool.close)

        redis = from_url(
            config.REDIS_DSN,
            socket_timeout=config.REDIS_SOCKET_TIMEOUT,
            health_check_interval=config.REDIS_HEALTH_CHECK_INTERVAL,
        )
        stack.push_async_callback(redis.aclose)

        app.state.pool = pg_pool
        app.state.redis = redis

        yield


async def repository_error_handler(
    request: Request,  # noqa: ARG001
    exc: Exception,  # noqa: ARG001
) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(lifespan=lifespan)

    app.add_exception_handler(
        RepositoryError,
        repository_error_handler,
    )

    base_dir = Path(__file__).parent.absolute()
    static_dir = str((base_dir / "static"))
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.state.static_dir = static_dir

    app.include_router(health_router)
    app.include_router(price_router, prefix="/api/v1")
    app.include_router(root_router)

    return app
