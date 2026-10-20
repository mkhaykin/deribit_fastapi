from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
from fastapi import FastAPI, Response, status
from redis.asyncio import from_url

from config import config

from .router import router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.pool = await asyncpg.create_pool(
        dsn=config.DATABASE_DSN,
        min_size=1,
        max_size=10,
    )
    app.state.redis = from_url(config.REDIS_DSN)

    try:
        yield
    finally:
        await app.state.redis.close()
        await app.state.pool.close()


app = FastAPI(lifespan=lifespan)

app.include_router(router, prefix="/api/v1")


@app.get("/favicon.ico", include_in_schema=False)
async def disable_favicon() -> Response:
    return Response(status_code=204)


@app.get("/")
async def hello() -> dict:
    return {"msg": "Hello World"}


@app.get("/healthz", status_code=status.HTTP_200_OK)
async def health() -> dict:
    return {"status": "alive"}


@app.get("/readyz", status_code=status.HTTP_200_OK)
async def ready(response: Response) -> dict:
    is_pg_ok = True
    is_redis_ok = True
    # TODO проверить статус фактически

    if not is_pg_ok or not is_redis_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unready",
            "db": "up" if is_pg_ok else "down",
            "cache": "up" if is_redis_ok else "down",
        }

    return {"status": "ready"}
